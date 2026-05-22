from __future__ import annotations

import glob
import os
import re
from pathlib import Path


def _read_extern_inf(raw_dir: Path) -> list[bytes]:
    info = raw_dir / "_extern.inf"
    with info.open("rb") as f:
        return f.readlines()


def _extract_first_integer(text: str) -> str | None:
    """
    Extract the first integer from a string.
    Returns None if no digits found.
    """
    digits = re.findall(r"\d+", text)
    return digits[0] if digits else None


def _find_lockmass_by_reference(lines: list[bytes]) -> str | None:
    """
    Look for a line containing 'REFERENCE' and extract the function number.
    """
    for line in lines:
        if b"REFERENCE" in line:
            text = line.decode(errors="ignore")
            ref = _extract_first_integer(text)
            if ref:
                return ref
    return None


def _find_last_function_header(lines: list[bytes]) -> str | None:
    """
    Find the last 'Function Parameters - Function X' header.
    """
    last = None
    for line in lines:
        if b"Function Parameters - Function" in line:
            text = line.decode(errors="ignore")
            last = text

    if last is None:
        return None

    return _extract_first_integer(last)


def _func_tag(ref: str) -> tuple[str, int, str]:
    """
    Build FUNCxxx tag and padding.
    """
    # Ensure ref is clean
    ref_clean = _extract_first_integer(ref)
    if ref_clean is None:
        raise ValueError(f"Invalid function reference: {ref}")

    ref_int = int(ref_clean)
    zeros = "0" * max(0, 3 - len(ref_clean))
    func_num_str = zeros + ref_clean

    return f"FUNC{func_num_str}", ref_int, zeros


def _delete_functions_from(raw_dir: Path, start_ref: str) -> None:
    """
    Delete FUNCxxx files starting from the lockmass function and above.
    """
    files = sorted(glob.glob(str(raw_dir / "*")))
    func_tag, r, zeros = _func_tag(start_ref)

    delete_indices: list[int] = []
    i = 0

    for idx, path in enumerate(files):
        if func_tag in path:
            # Found the starting function
            func_current = f"FUNC{zeros}{r + i}"

            for a in range(idx, len(files)):
                if func_current in files[a]:
                    m = a
                    while m < len(files) and func_current in files[m]:
                        delete_indices.append(m)
                        m += 1
                    i += 1
                    func_current = f"FUNC{zeros}{r + i}"

    for di in sorted(set(delete_indices)):
        try:
            os.remove(files[di])
        except FileNotFoundError:
            pass


def annotate_raw_folder(raw_dir: Path) -> int:
    """
    Delete lockmass and higher functions in a .raw folder and
    return the lockmass function number as int.
    """
    lines = _read_extern_inf(raw_dir)

    ref = _find_lockmass_by_reference(lines)
    if ref is None:
        ref = _find_last_function_header(lines)

    if ref is None:
        # No lockmass found — do nothing
        return 1

    # Clean the reference: extract only digits
    clean = _extract_first_integer(ref)
    if clean is None:
        return 1

    # Use the cleaned reference everywhere
    _delete_functions_from(raw_dir, clean)
    return int(clean)


def annotate_all_raw(raw_dirs: list[Path]) -> list[int]:
    return [annotate_raw_folder(rd) for rd in raw_dirs]
