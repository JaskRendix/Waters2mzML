from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .config import default_paths
from .job import process_single_raw
from .parallel import run_parallel
from .paths import clean_raw_folder, ensure_dirs, list_raw_folders

logger = logging.getLogger("waters2mzml.pipeline")


def run_pipeline(
    base_dir: Path,
    input_dir: Path | None,
    output_dir: Path | None,
    centroid: bool,
    skip_cleanup: bool = False,
    use_docker: bool = False,
    docker_image: str | None = None,
    do_postprocess: bool = True,
) -> None:
    paths = default_paths(base_dir)
    if input_dir is not None:
        paths.raw_dir = input_dir
    if output_dir is not None:
        paths.mzml_dir = output_dir

    ensure_dirs(paths.raw_dir, paths.mzml_dir)

    if not skip_cleanup:
        clean_raw_folder(paths.raw_dir)

    raw_dirs = list_raw_folders(paths.raw_dir)
    if not raw_dirs:
        logger.info("No .raw folders found")
        return

    total = len(raw_dirs)
    logger.info(f"Starting sequential pipeline on {total} RAW folders")

    for idx, raw_dir in enumerate(raw_dirs, start=1):
        logger.info(f"[SEQ] ({idx}/{total}) Processing {raw_dir}")

        result = process_single_raw(
            raw_dir=raw_dir,
            msconvert_path=paths.msconvert_path,
            output_dir=paths.mzml_dir,
            centroid=centroid,
            use_docker=use_docker,
            docker_image=docker_image,
            do_postprocess=do_postprocess,
        )

        if result.warnings:
            for w in result.warnings:
                logger.warning(f"{raw_dir}: {w}")

        if not result.success:
            logger.error(f"{raw_dir}: {result.error}")
        else:
            logger.info(f"{raw_dir}: wrote {result.mzml_path}")

        if result.qc:
            logger.info(
                f"{raw_dir}: TIC={len(result.qc.tic)}, "
                f"MaxTIC={max(result.qc.tic):.2f}, "
                f"MaxBPC={max(result.qc.bpc):.2f}, "
                f"MedianPeaks={int(np.median(result.qc.peak_counts))}"
            )

    logger.info("Sequential annotation completed")


def run_pipeline_parallel(
    base_dir: Path,
    input_dir: Path | None,
    output_dir: Path | None,
    centroid: bool,
    jobs: int,
    skip_cleanup: bool = False,
    use_docker: bool = False,
    docker_image: str | None = None,
    do_postprocess: bool = True,
    retries: int = 0,
) -> None:
    """
    Parallel version of run_pipeline using run_parallel.
    """
    paths = default_paths(base_dir)
    if input_dir is not None:
        paths.raw_dir = input_dir
    if output_dir is not None:
        paths.mzml_dir = output_dir

    ensure_dirs(paths.raw_dir, paths.mzml_dir)

    if not skip_cleanup:
        clean_raw_folder(paths.raw_dir)

    raw_dirs = list_raw_folders(paths.raw_dir)
    if not raw_dirs:
        logger.info("No .raw folders found")
        return

    logger.info(f"Running parallel pipeline with {jobs} workers")

    results = run_parallel(
        raw_dirs=raw_dirs,
        msconvert_path=paths.msconvert_path,
        output_dir=paths.mzml_dir,
        centroid=centroid,
        jobs=jobs,
        use_docker=use_docker,
        docker_image=docker_image,
        retries=retries,
        do_postprocess=do_postprocess,
    )

    logger.info("Parallel processing summary:")

    for result in results:
        raw_dir = result.raw_dir

        if result.success:
            logger.info(f"[OK]   {raw_dir} → {result.mzml_path}")

            if result.warnings:
                for w in result.warnings:
                    logger.warning(f"{raw_dir}: {w}")

            if result.qc:
                logger.info(
                    f"{raw_dir}: TIC={len(result.qc.tic)}, "
                    f"MaxTIC={max(result.qc.tic):.2f}, "
                    f"MaxBPC={max(result.qc.bpc):.2f}, "
                    f"MedianPeaks={int(np.median(result.qc.peak_counts))}"
                )

        else:
            logger.error(f"[FAIL] {raw_dir}: {result.error}")

    logger.info("Parallel annotation completed")
