from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ConversionConfig
from .msconvert import run_msconvert
from .mzml_postprocess import postprocess_mzml
from .raw_annotation import annotate_all_raw


@dataclass
class JobResult:
    raw_dir: Path
    mzml_path: Path | None
    success: bool
    error: str | None = None


def process_single_raw(
    raw_dir: Path,
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
) -> JobResult:
    """
    The unified job function used by BOTH sequential and parallel pipelines.
    """
    try:
        # 1) Annotate RAW (reads _extern)
        ms2_list = annotate_all_raw([raw_dir])
        ms2 = ms2_list[0]

        # 2) Convert with msconvert
        config = ConversionConfig(centroid=centroid)
        mzml_path = run_msconvert(msconvert_path, raw_dir, config)

        # 3) Post-process mzML
        postprocess_mzml(mzml_path, ms2)

        # 4) Move to output directory
        dest = output_dir / mzml_path.name
        mzml_path.rename(dest)

        return JobResult(
            raw_dir=raw_dir,
            mzml_path=dest,
            success=True,
        )

    except Exception as exc:
        return JobResult(
            raw_dir=raw_dir,
            mzml_path=None,
            success=False,
            error=str(exc),
        )
