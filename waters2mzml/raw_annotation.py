from __future__ import annotations

import glob
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .validation import validate_raw_folder

logger = logging.getLogger("waters2mzml.annotation")


@dataclass
class RawAnnotationResult:
    raw_dir: Path
    lockmass_function: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    extern_lines: int = 0
    func_files_found: int = 0
    func_files_deleted: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_extern_inf(raw_dir: Path) -> list[bytes]:
    info = raw_dir / "_extern.inf"
    if not info.exists():
        raise FileNotFoundError(f"_extern.inf not found in {raw_dir}")
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
    Find the last 'Function Parameters - Function X' header
    and return ONLY the function number as a string.
    """
    last = None
    for line in lines:
        if b"Function Parameters - Function" in line:
            text = line.decode(errors="ignore")
            last = text

    if last is None:
        return None

    # Extract just the integer
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


def _validate_extern_lines(raw_dir: Path, lines: list[bytes]) -> list[str]:
    warnings: list[str] = []
    if not lines:
        warnings.append(f"{raw_dir}: _extern.inf is empty")
    return warnings


def _validate_function_headers(
    raw_dir: Path, lines: list[bytes]
) -> tuple[int | None, list[str]]:
    """
    Validate that function headers exist and are at least somewhat sane.
    Returns (last_function_number, warnings).
    """
    warnings: list[str] = []
    last_ref = _find_last_function_header(lines)

    if last_ref is None:
        warnings.append(f"{raw_dir}: no 'Function Parameters' headers found")
        return None, warnings

    clean = _extract_first_integer(last_ref)
    if clean is None:
        warnings.append(
            f"{raw_dir}: could not parse last function number from header '{last_ref}'"
        )
        return None, warnings

    try:
        last_fn = int(clean)
    except ValueError:
        warnings.append(f"{raw_dir}: last function number is not an integer: '{clean}'")
        return None, warnings

    if last_fn <= 0:
        warnings.append(f"{raw_dir}: last function number is non-positive: {last_fn}")

    return last_fn, warnings


def _validate_lockmass(
    raw_dir: Path, ref: str | None, last_fn: int | None
) -> tuple[int, list[str]]:
    """
    Decide which function to treat as lockmass and validate it.
    Returns (lockmass_function, warnings).
    """
    warnings: list[str] = []

    if ref is None:
        # Fallback: use last function if available
        if last_fn is None:
            warnings.append(
                f"{raw_dir}: no lockmass reference and no function headers; defaulting to 1"
            )
            return 1, warnings
        warnings.append(
            f"{raw_dir}: no explicit lockmass reference; using last function {last_fn}"
        )
        return last_fn, warnings

    clean = _extract_first_integer(ref)
    if clean is None:
        warnings.append(
            f"{raw_dir}: lockmass reference '{ref}' has no digits; defaulting to 1"
        )
        return 1, warnings

    try:
        fn = int(clean)
    except ValueError:
        warnings.append(
            f"{raw_dir}: lockmass reference '{clean}' is not an integer; defaulting to 1"
        )
        return 1, warnings

    if fn <= 0:
        warnings.append(
            f"{raw_dir}: lockmass function {fn} is non-positive; defaulting to 1"
        )
        return 1, warnings

    if last_fn is not None and fn > last_fn:
        warnings.append(
            f"{raw_dir}: lockmass function {fn} > last function {last_fn}; clamping to {last_fn}"
        )
        fn = last_fn

    return fn, warnings


def _delete_functions_from(raw_dir: Path, start_ref: str) -> tuple[int, int]:
    """
    Delete FUNCxxx files starting from the lockmass function and above.
    Returns (func_files_found, func_files_deleted).
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

    deleted = 0
    for di in sorted(set(delete_indices)):
        try:
            os.remove(files[di])
            deleted += 1
        except FileNotFoundError:
            pass

    return len(files), deleted


def annotate_raw_folder(raw_dir: Path) -> RawAnnotationResult:
    """
    Delete lockmass and higher functions in a .raw folder and
    return a structured annotation result with validation info.
    """
    logger.info(f"Annotating RAW folder {raw_dir}")

    warnings: list[str] = []
    errors: list[str] = []

    try:
        lines = _read_extern_inf(raw_dir)
    except FileNotFoundError as e:
        logger.error(f"{raw_dir}: missing _extern.inf")
        return RawAnnotationResult(
            raw_dir=raw_dir,
            lockmass_function=1,
            warnings=[],
            errors=[str(e)],
            extern_lines=0,
            func_files_found=0,
            func_files_deleted=0,
        )

    warnings.extend(_validate_extern_lines(raw_dir, lines))
    extern_lines = len(lines)

    last_fn, header_warnings = _validate_function_headers(raw_dir, lines)
    warnings.extend(header_warnings)

    ref = _find_lockmass_by_reference(lines)
    lockmass_fn, lockmass_warnings = _validate_lockmass(raw_dir, ref, last_fn)
    warnings.extend(lockmass_warnings)

    validation_issues = validate_raw_folder(
        raw_dir=raw_dir,
        lines=lines,
        lockmass_fn=lockmass_fn,
        last_fn=last_fn,
    )

    for issue in validation_issues:
        warnings.append(str(issue))

    # Use the cleaned reference for deletion
    clean_ref = str(lockmass_fn)
    func_found, func_deleted = _delete_functions_from(raw_dir, clean_ref)

    logger.debug(
        f"{raw_dir}: lockmass={lockmass_fn}, extern_lines={extern_lines}, "
        f"func_found={func_found}, func_deleted={func_deleted}"
    )

    return RawAnnotationResult(
        raw_dir=raw_dir,
        lockmass_function=lockmass_fn,
        warnings=warnings,
        errors=errors,
        extern_lines=extern_lines,
        func_files_found=func_found,
        func_files_deleted=func_deleted,
    )


def annotate_all_raw(raw_dirs: list[Path]) -> list[RawAnnotationResult]:
    logger.debug(f"Annotating {len(raw_dirs)} RAW folders")
    return [annotate_raw_folder(rd) for rd in raw_dirs]
