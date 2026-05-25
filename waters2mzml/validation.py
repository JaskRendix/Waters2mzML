from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger("waters2mzml.validation")

pattern = re.compile(r"^[A-Za-z0-9 _\-\(\)\[\]\.:=]+$")


class ValidationIssue:
    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message


def validate_extern_structure(lines: list[bytes]) -> list[ValidationIssue]:
    """
    Validate basic structure of _extern.inf.
    Checks for:
    - missing function blocks
    - malformed lines
    - truncated headers
    """
    issues: list[ValidationIssue] = []

    if not lines:
        issues.append(ValidationIssue("_extern.inf is empty"))
        return issues

    header_count = 0
    for line in lines:

        # Detect invalid bytes BEFORE decoding
        if any(b > 0x7F for b in line):
            issues.append(ValidationIssue("Malformed line: <non-ascii-bytes>"))
            continue

        text = line.decode(errors="ignore")
        stripped = text.strip()

        if "Function Parameters - Function" in text:
            header_count += 1

        if not stripped:
            continue

        if not pattern.match(stripped):
            issues.append(ValidationIssue(f"Malformed line: {stripped}"))

    if header_count == 0:
        issues.append(ValidationIssue("No function headers found in _extern.inf"))

    return issues


def validate_function_sequence(lines: list[bytes]) -> list[ValidationIssue]:
    """
    Validate that function numbers are:
    - numeric
    - increasing
    - contiguous (optional but recommended)
    """
    issues: list[ValidationIssue] = []
    numbers: list[int] = []

    for line in lines:
        text = line.decode(errors="ignore")
        if "Function Parameters - Function" in text:
            digits = re.findall(r"\d+", text)

            if not digits:
                # Distinguish missing vs non-numeric
                if text.strip().endswith("Function"):
                    issues.append(
                        ValidationIssue(
                            f"Function header missing number: {text.strip()}"
                        )
                    )
                else:
                    issues.append(
                        ValidationIssue(f"Non-numeric function number: {text.strip()}")
                    )
                continue

            try:
                numbers.append(int(digits[0]))
            except ValueError:
                issues.append(
                    ValidationIssue(f"Non-numeric function number: {digits[0]}")
                )

    if not numbers:
        return issues

    for a, b in zip(numbers, numbers[1:]):
        if b < a:
            issues.append(
                ValidationIssue(f"Function numbers not increasing: {a} -> {b}")
            )

    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        issues.append(
            ValidationIssue(
                f"Function numbers not contiguous: found {numbers}, expected {expected}"
            )
        )

    return issues


def validate_lockmass_consistency(
    lockmass_fn: int, last_fn: int | None
) -> list[ValidationIssue]:
    """
    Validate that the lockmass function is within expected bounds.
    """
    issues: list[ValidationIssue] = []

    if lockmass_fn <= 0:
        issues.append(
            ValidationIssue(f"Lockmass function {lockmass_fn} is non-positive")
        )

    if last_fn is not None and lockmass_fn > last_fn:
        issues.append(
            ValidationIssue(
                f"Lockmass function {lockmass_fn} exceeds last function {last_fn}"
            )
        )

    return issues


def validate_func_directories(
    raw_dir: Path, last_fn: int | None
) -> list[ValidationIssue]:
    """
    Validate that FUNCxxx directories match the function count.
    """
    issues: list[ValidationIssue] = []

    func_dirs = sorted(
        [p for p in raw_dir.iterdir() if p.is_dir() and "FUNC" in p.name]
    )

    if not func_dirs:
        issues.append(ValidationIssue("No FUNCxxx directories found"))
        return issues

    numbers = []
    for d in func_dirs:
        digits = re.findall(r"\d+", d.name)
        if not digits:
            issues.append(ValidationIssue(f"Invalid FUNC directory number: {d.name}"))
            continue
        try:
            numbers.append(int(digits[0]))
        except ValueError:
            issues.append(ValidationIssue(f"Invalid FUNC directory number: {d.name}"))

    if not numbers:
        return issues

    numbers_sorted = sorted(numbers)

    for a, b in zip(numbers_sorted, numbers_sorted[1:]):
        if b < a:
            issues.append(
                ValidationIssue(f"FUNC directories not increasing: {a} -> {b}")
            )

    expected = list(range(numbers_sorted[0], numbers_sorted[0] + len(numbers_sorted)))
    if numbers_sorted != expected:
        issues.append(
            ValidationIssue(
                f"FUNC directories not contiguous: found {numbers_sorted}, expected {expected}"
            )
        )

    if last_fn is not None and numbers_sorted[-1] != last_fn:
        issues.append(
            ValidationIssue(
                f"FUNC directory count ({numbers_sorted[-1]}) does not match extern last function ({last_fn})"
            )
        )

    return issues


def validate_raw_folder(
    raw_dir: Path,
    lines: list[bytes],
    lockmass_fn: int,
    last_fn: int | None,
) -> list[ValidationIssue]:
    """
    Run all validation checks for a RAW folder.
    """
    issues: list[ValidationIssue] = []

    issues.extend(validate_extern_structure(lines))
    issues.extend(validate_function_sequence(lines))
    issues.extend(validate_lockmass_consistency(lockmass_fn, last_fn))
    issues.extend(validate_func_directories(raw_dir, last_fn))

    return issues
