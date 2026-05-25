from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .config import ConversionConfig
from .msconvert import run_msconvert
from .mzml_postprocess import postprocess_mzml
from .qc import QCResult
from .raw_annotation import RawAnnotationResult, annotate_all_raw

logger = logging.getLogger("waters2mzml.job")


@dataclass
class JobResult:
    raw_dir: Path
    mzml_path: Path | None
    success: bool
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    annotation: RawAnnotationResult | None = None
    qc: QCResult | None = None


def _prepare_job_workdir(raw_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    """
    Create a per-job working directory under output_dir/.tmp/<raw_name>
    and expose the RAW folder there as a symlink (or copy fallback).
    """
    tmp_root = output_dir / ".tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)

    job_root = tmp_root / raw_dir.name
    if job_root.exists():
        shutil.rmtree(job_root)
    job_root.mkdir(parents=True, exist_ok=True)

    job_raw = job_root / raw_dir.name
    try:
        job_raw.symlink_to(raw_dir, target_is_directory=raw_dir.is_dir())
        logger.debug(f"Created symlink for {raw_dir} → {job_raw}")
    except OSError:
        if raw_dir.is_dir():
            shutil.copytree(raw_dir, job_raw)
        else:
            shutil.copy2(raw_dir, job_raw)
        logger.debug(f"Copied RAW folder for {raw_dir} → {job_raw}")

    return job_root, job_raw


def process_single_raw(
    raw_dir: Path,
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
    use_docker: bool = False,
    do_postprocess: bool = True,
) -> JobResult:
    """
    The unified job function used by BOTH sequential and parallel pipelines.
    Now uses a per-job working directory to make msconvert parallel-safe.
    """
    logger.info(f"Starting job for {raw_dir}")

    try:
        # 0) Per-job working directory
        job_root, job_raw = _prepare_job_workdir(raw_dir, output_dir)

        # 1) Annotate RAW
        logger.debug(f"Annotating {raw_dir}")
        annotation = annotate_all_raw([job_raw])[0]
        ms2 = annotation.lockmass_function

        # 2) Convert with msconvert
        logger.debug(f"Converting {raw_dir} with msconvert")
        config = ConversionConfig(centroid=centroid, use_docker=use_docker)
        mzml_path = run_msconvert(msconvert_path, job_raw, config)

        # 3) Post-process
        if do_postprocess:
            logger.debug(f"Postprocessing {raw_dir}")
            qc = postprocess_mzml(mzml_path, ms2)
        else:
            qc = None

        # 4) Move final mzML to output directory
        dest = output_dir / mzml_path.name
        if dest.exists():
            dest.unlink()
        mzml_path.rename(dest)
        logger.debug(f"Moved {raw_dir} mzML → {dest}")

        # 5) Cleanup
        shutil.rmtree(job_root, ignore_errors=True)

        logger.info(f"Completed job for {raw_dir}")

        return JobResult(
            raw_dir=raw_dir,
            mzml_path=dest,
            success=True,
            warnings=annotation.warnings,
            annotation=annotation,
            qc=qc,
        )

    except Exception as exc:
        logger.error(f"Job failed for {raw_dir}: {exc}")
        return JobResult(
            raw_dir=raw_dir,
            mzml_path=None,
            success=False,
            error=str(exc),
        )
