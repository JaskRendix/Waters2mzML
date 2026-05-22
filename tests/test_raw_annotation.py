from pathlib import Path

from waters2mzml.raw_annotation import (
    _find_last_function_header,
    _find_lockmass_by_reference,
    annotate_raw_folder,
)


def test_find_lockmass_by_reference():
    """
    Case 1: _extern.inf explicitly contains 'REFERENCE' in a function header.
    """
    lines = [
        b"Function Parameters - Function 1",
        b"Function Parameters - Function 2",
        b"Function Parameters - Function 3  REFERENCE",  # lockmass
    ]

    ref = _find_lockmass_by_reference(lines)
    assert ref == "3"


def test_find_last_function_header():
    """
    Case 2: No REFERENCE tag; fallback to last function header.
    """
    lines = [
        b"Function Parameters - Function 1",
        b"Function Parameters - Function 2",
        b"Function Parameters - Function 5",  # last = lockmass
    ]

    ref = _find_last_function_header(lines)
    assert ref == "5"


def test_annotate_raw_folder_reference(tmp_path: Path):
    """
    Full integration test:
    - Create a fake .raw folder
    - Add _extern.inf containing REFERENCE
    - Add fake FUNC files
    - Ensure lockmass and higher functions are deleted
    """
    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    # Create _extern.inf with REFERENCE on function 3
    extern = raw_dir / "_extern.inf"
    extern.write_bytes(
        b"Function Parameters - Function 1\n"
        b"Function Parameters - Function 2\n"
        b"Function Parameters - Function 3  REFERENCE\n"
    )

    # Create fake FUNC files for functions 1–5
    for func in range(1, 6):
        for suffix in ["_header.txt", "_data.txt", "_scan.bin"]:
            (raw_dir / f"FUNC{func:03d}{suffix}").write_text("dummy")

    # Run annotation
    lockmass = annotate_raw_folder(raw_dir)

    # Lockmass should be function 3
    assert lockmass == 3

    # FUNC003, FUNC004, FUNC005 should be deleted
    remaining = {p.name for p in raw_dir.iterdir()}
    assert "FUNC001_header.txt" in remaining
    assert "FUNC002_header.txt" in remaining
    assert "FUNC003_header.txt" not in remaining
    assert "FUNC004_header.txt" not in remaining
    assert "FUNC005_header.txt" not in remaining


def test_annotate_raw_folder_last_header(tmp_path: Path):
    """
    Same as above, but no REFERENCE tag.
    Should fall back to last function header.
    """
    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    extern = raw_dir / "_extern.inf"
    extern.write_bytes(
        b"Function Parameters - Function 1\n"
        b"Function Parameters - Function 2\n"
        b"Function Parameters - Function 7\n"
    )

    # Create fake FUNC files for functions 1–9
    for func in range(1, 10):
        for suffix in ["_header.txt", "_data.txt"]:
            (raw_dir / f"FUNC{func:03d}{suffix}").write_text("dummy")

    lockmass = annotate_raw_folder(raw_dir)
    assert lockmass == 7

    remaining = {p.name for p in raw_dir.iterdir()}
    assert "FUNC006_header.txt" in remaining
    assert "FUNC007_header.txt" not in remaining
    assert "FUNC008_header.txt" not in remaining
    assert "FUNC009_header.txt" not in remaining
