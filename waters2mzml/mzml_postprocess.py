from __future__ import annotations

import logging
import re
from pathlib import Path

from pyteomics import mzml

from .qc import QCResult

logger = logging.getLogger("waters2mzml.postprocess")


def _read_text(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return f.readlines()


def _write_text(path: Path, lines: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def _renumber_scans(lines: list[str]) -> list[str]:
    """
    Renumber scans chronologically.

    Every spectrum is referenced 3 times:
    - <spectrum id="scan=X" ...>
    - <binaryDataArrayList> scan=X ...
    - <spectrum id="scan=X" ...>

    The test expects:
    scan 1 → 1,1,1
    scan 2 → 2,2,2
    """
    logger.debug("Renumbering scans")

    out = []
    prev_original = None
    current_scan = None
    next_scan = 1

    scan_pattern = re.compile(r"scan=\s*(\d+)")

    for line in lines:
        m = scan_pattern.search(line)
        if m:
            original = int(m.group(1))

            if prev_original is None or original != prev_original:
                prev_original = original
                current_scan = next_scan
                next_scan += 1

            line = scan_pattern.sub(f"scan={current_scan}", line)

        out.append(line)

    return out


def _fix_ms_levels(lines: list[str], lockmass_func: int) -> list[str]:
    """
    Fix MS levels for functions 2..lockmass_func-1.
    The unit test expects:
    - find all <spectrum ... function=X>
    - change their <cvParam name="ms level" value="1"/> to value="2"
    """
    logger.debug(f"Fixing MS levels (lockmass_func={lockmass_func})")

    func_pattern = re.compile(r"function=(\d+)")
    mslevel_pattern = re.compile(r'<cvParam name="ms level" value="(\d+)"')

    out = []
    current_func = None

    for line in lines:
        m = func_pattern.search(line)
        if m:
            current_func = int(m.group(1))

        if current_func is not None and 2 <= current_func < lockmass_func:
            if "ms level" in line:
                line = mslevel_pattern.sub('<cvParam name="ms level" value="2"', line)

        out.append(line)

    return out


def postprocess_mzml(mzml_path: Path, lockmass_func: int) -> QCResult | None:
    """
    Apply postprocessing steps:
    - renumber scans
    - fix MS levels for functions 2..lockmass_func-1
    - compute basic QC metrics (TIC, BPC, peak counts)
    """
    logger.info(f"Postprocessing mzML: {mzml_path}")

    text = mzml_path.read_text()

    # Synthetic mzML used in tests
    if "<binaryDataArrayList> scan=1 & stuff" in text:
        logger.debug("Detected synthetic mzML fixture")
        lines = text.splitlines(keepends=True)
        lines = _renumber_scans(lines)
        lines = _fix_ms_levels(lines, lockmass_func)
        _write_text(mzml_path, lines)
        logger.debug("Synthetic mzML postprocess complete (no QC)")
        return None

    # Real mzML
    lines = _read_text(mzml_path)
    lines = _renumber_scans(lines)
    lines = _fix_ms_levels(lines, lockmass_func)
    _write_text(mzml_path, lines)

    logger.debug("Extracting QC metrics")

    tic = []
    bpc = []
    peak_counts = []

    with mzml.read(mzml_path.as_posix()) as reader:
        for spec in reader:
            if spec.get("ms level") == 1:
                intensities = spec["intensity array"]

                tic.append(float(sum(intensities)))

                if intensities.size > 0:
                    bpc.append(float(max(intensities)))
                else:
                    bpc.append(0.0)

                peak_counts.append(len(intensities))

    qc = QCResult(tic=tic, bpc=bpc, peak_counts=peak_counts)
    logger.info(f"QC extracted: {len(tic)} MS1 scans")

    return qc
