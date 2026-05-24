from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import ConversionConfig
from .msconvert import run_msconvert
from .mzml_postprocess import postprocess_mzml
from .raw_annotation import annotate_all_raw, RawAnnotationResult


@dataclass
class JobResult:
    raw_dir: Path
    mzml_path: Path | None
    success: bool
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    annotation: RawAnnotationResult | None = None


def process_single_raw(
    raw_dir: Path,
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
    use_docker: bool = False,
) -> JobResult:
    """
    The unified job function used by BOTH sequential and parallel pipelines.
    """
    try:
        # 1) Annotate RAW (reads _extern)
        annotation = annotate_all_raw([raw_dir])[0]
        ms2 = annotation.lockmass_function

        # 2) Convert with msconvert
        config = ConversionConfig(centroid=centroid, use_docker=use_docker)
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
            warnings=annotation.warnings,
            annotation=annotation,
        )

    except Exception as exc:
        return JobResult(
            raw_dir=raw_dir,
            mzml_path=None,
            success=False,
            error=str(exc),
        )
