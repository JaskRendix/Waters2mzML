from waters2mzml.raw_annotation import (
    RawAnnotationResult,
    _delete_functions_from,
    _extract_first_integer,
    _find_last_function_header,
    _find_lockmass_by_reference,
    _validate_extern_lines,
    _validate_function_headers,
    _validate_lockmass,
    annotate_all_raw,
    annotate_raw_folder,
)


def write_extern(tmp_path, lines: list[str]):
    p = tmp_path / "_extern.inf"
    p.write_bytes("\n".join(lines).encode())
    return p


def test_extract_first_integer():
    assert _extract_first_integer("abc123xyz") == "123"
    assert _extract_first_integer("no digits") is None
    assert _extract_first_integer("99 bottles") == "99"


def test_find_lockmass_by_reference():
    lines = [b"Some text", b"REFERENCE FUNCTION 3", b"Other"]
    assert _find_lockmass_by_reference(lines) == "3"


def test_find_lockmass_by_reference_none():
    lines = [b"no reference here"]
    assert _find_lockmass_by_reference(lines) is None


def test_find_last_function_header():
    lines = [
        b"Function Parameters - Function 1",
        b"Other",
        b"Function Parameters - Function 5",
    ]
    assert _find_last_function_header(lines) == "5"


def test_find_last_function_header_none():
    assert _find_last_function_header([b"no headers"]) is None


def test_validate_extern_lines_empty(tmp_path):
    warnings = _validate_extern_lines(tmp_path, [])
    assert len(warnings) == 1
    assert "empty" in warnings[0]


def test_validate_function_headers_valid(tmp_path):
    lines = [
        b"Function Parameters - Function 1",
        b"Function Parameters - Function 3",
    ]
    last_fn, warnings = _validate_function_headers(tmp_path, lines)
    assert last_fn == 3
    assert warnings == []


def test_validate_function_headers_invalid(tmp_path):
    lines = [b"Function Parameters - Function X"]
    last_fn, warnings = _validate_function_headers(tmp_path, lines)
    assert last_fn is None
    assert len(warnings) == 1


def test_validate_lockmass_valid(tmp_path):
    fn, warnings = _validate_lockmass(tmp_path, "3", 5)
    assert fn == 3
    assert warnings == []


def test_validate_lockmass_clamped(tmp_path):
    fn, warnings = _validate_lockmass(tmp_path, "10", 5)
    assert fn == 5
    assert len(warnings) == 1


def test_validate_lockmass_no_ref(tmp_path):
    fn, warnings = _validate_lockmass(tmp_path, None, 4)
    assert fn == 4
    assert len(warnings) == 1


def test_validate_lockmass_bad_ref(tmp_path):
    fn, warnings = _validate_lockmass(tmp_path, "abc", 4)
    assert fn == 1
    assert len(warnings) == 1


def test_delete_functions_from(tmp_path):
    # Create fake FUNC files
    for i in range(1, 6):
        (tmp_path / f"FUNC00{i}.dat").write_text("x")

    found, deleted = _delete_functions_from(tmp_path, "3")

    assert found == 5
    assert deleted >= 3  # FUNC003, FUNC004, FUNC005


def test_annotate_raw_folder_basic(tmp_path):
    # Create extern with lockmass reference
    write_extern(
        tmp_path,
        [
            "Function Parameters - Function 1",
            "Function Parameters - Function 2",
            "REFERENCE FUNCTION 2",
        ],
    )

    # Create FUNC files
    for i in range(1, 5):
        (tmp_path / f"FUNC00{i}.dat").write_text("x")

    result = annotate_raw_folder(tmp_path)

    assert isinstance(result, RawAnnotationResult)
    assert result.lockmass_function == 2
    assert result.func_files_found == 5
    assert result.func_files_deleted >= 2
    assert result.extern_lines == 3
    assert result.ok


def test_annotate_raw_folder_no_extern(tmp_path):
    result = annotate_raw_folder(tmp_path)

    assert isinstance(result, RawAnnotationResult)
    assert result.lockmass_function == 1
    assert len(result.errors) == 1
    assert not result.ok


def test_annotate_raw_folder_no_lockmass(tmp_path):
    write_extern(
        tmp_path,
        [
            "Function Parameters - Function 1",
            "Function Parameters - Function 3",
        ],
    )

    result = annotate_raw_folder(tmp_path)

    assert result.lockmass_function == 3
    assert len(result.warnings) >= 1


def test_annotate_all_raw(tmp_path):
    d1 = tmp_path / "raw1"
    d2 = tmp_path / "raw2"
    d1.mkdir()
    d2.mkdir()

    write_extern(d1, ["Function Parameters - Function 1"])
    write_extern(d2, ["Function Parameters - Function 2"])

    results = annotate_all_raw([d1, d2])

    assert len(results) == 2
    assert all(isinstance(r, RawAnnotationResult) for r in results)
