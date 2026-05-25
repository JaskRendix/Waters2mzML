from waters2mzml.validation import (
    validate_extern_structure,
    validate_func_directories,
    validate_function_sequence,
    validate_lockmass_consistency,
    validate_raw_folder,
)


def _b(s: str) -> bytes:
    return s.encode("utf-8")


# -----------------------------
# validate_extern_structure
# -----------------------------


def test_extern_structure_empty():
    issues = validate_extern_structure([])
    assert len(issues) == 1
    assert "_extern.inf is empty" in str(issues[0])


def test_extern_structure_no_headers():
    lines = [_b("Some random line"), _b("Another line")]
    issues = validate_extern_structure(lines)
    assert any("No function headers" in str(i) for i in issues)


def test_extern_structure_malformed_line():
    lines = [
        _b("Function Parameters - Function 1"),
        b"\xff\xff\xffBADLINE",  # invalid bytes
    ]
    issues = validate_extern_structure(lines)
    assert any("Malformed line" in str(i) for i in issues)


def test_extern_structure_valid():
    lines = [
        _b("Function Parameters - Function 1"),
        _b("SomeKey: SomeValue"),
    ]
    issues = validate_extern_structure(lines)
    assert issues == []


# -----------------------------
# validate_function_sequence
# -----------------------------


def test_function_sequence_missing_number():
    lines = [_b("Function Parameters - Function ")]
    issues = validate_function_sequence(lines)
    assert any("missing number" in str(i) for i in issues)


def test_function_sequence_non_numeric():
    lines = [_b("Function Parameters - Function X")]
    issues = validate_function_sequence(lines)
    assert any("Non-numeric" in str(i) for i in issues)


def test_function_sequence_not_increasing():
    lines = [
        _b("Function Parameters - Function 2"),
        _b("Function Parameters - Function 1"),
    ]
    issues = validate_function_sequence(lines)
    assert any("not increasing" in str(i) for i in issues)


def test_function_sequence_not_contiguous():
    lines = [
        _b("Function Parameters - Function 1"),
        _b("Function Parameters - Function 3"),
    ]
    issues = validate_function_sequence(lines)
    assert any("not contiguous" in str(i) for i in issues)


def test_function_sequence_valid():
    lines = [
        _b("Function Parameters - Function 1"),
        _b("Function Parameters - Function 2"),
        _b("Function Parameters - Function 3"),
    ]
    issues = validate_function_sequence(lines)
    assert issues == []


# -----------------------------
# validate_lockmass_consistency
# -----------------------------


def test_lockmass_negative():
    issues = validate_lockmass_consistency(-1, 5)
    assert any("non-positive" in str(i) for i in issues)


def test_lockmass_exceeds_last():
    issues = validate_lockmass_consistency(10, 5)
    assert any("exceeds last function" in str(i) for i in issues)


def test_lockmass_valid():
    issues = validate_lockmass_consistency(3, 5)
    assert issues == []


# -----------------------------
# validate_func_directories
# -----------------------------


def test_func_dirs_missing(tmp_path):
    issues = validate_func_directories(tmp_path, last_fn=3)
    assert any("No FUNCxxx" in str(i) for i in issues)


def test_func_dirs_non_numeric(tmp_path):
    (tmp_path / "FUNCABC").mkdir()
    issues = validate_func_directories(tmp_path, last_fn=1)
    assert any("Invalid FUNC directory number" in str(i) for i in issues)


def test_func_dirs_not_contiguous(tmp_path):
    (tmp_path / "FUNC001").mkdir()
    (tmp_path / "FUNC003").mkdir()
    issues = validate_func_directories(tmp_path, last_fn=3)
    assert any("not contiguous" in str(i) for i in issues)


def test_func_dirs_mismatch_last_fn(tmp_path):
    (tmp_path / "FUNC001").mkdir()
    (tmp_path / "FUNC002").mkdir()
    issues = validate_func_directories(tmp_path, last_fn=3)
    assert any("does not match extern last function" in str(i) for i in issues)


def test_func_dirs_valid(tmp_path):
    (tmp_path / "FUNC001").mkdir()
    (tmp_path / "FUNC002").mkdir()
    (tmp_path / "FUNC003").mkdir()
    issues = validate_func_directories(tmp_path, last_fn=3)
    assert issues == []


# -----------------------------
# validate_raw_folder (integration)
# -----------------------------


def test_validate_raw_folder_integration(tmp_path):
    # Create FUNC dirs
    (tmp_path / "FUNC001").mkdir()
    (tmp_path / "FUNC002").mkdir()

    lines = [
        _b("Function Parameters - Function 1"),
        _b("Function Parameters - Function 2"),
    ]

    issues = validate_raw_folder(
        raw_dir=tmp_path,
        lines=lines,
        lockmass_fn=2,
        last_fn=2,
    )

    assert issues == []


def test_validate_raw_folder_detects_multiple_issues(tmp_path):
    # Missing FUNC dirs
    lines = [
        _b("Function Parameters - Function 1"),
        _b("Function Parameters - Function 3"),  # non-contiguous
    ]

    issues = validate_raw_folder(
        raw_dir=tmp_path,
        lines=lines,
        lockmass_fn=5,  # exceeds last_fn
        last_fn=3,
    )

    messages = [str(i) for i in issues]

    assert any("not contiguous" in m for m in messages)
    assert any("exceeds last function" in m for m in messages)
    assert any("No FUNCxxx" in m for m in messages)
