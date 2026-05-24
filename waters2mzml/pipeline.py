from __future__ import annotations

from pathlib import Path

import numpy as np

from .config import default_paths
from .job import process_single_raw
from .paths import clean_raw_folder, ensure_dirs, list_raw_folders


def run_pipeline(
    base_dir: Path,
    input_dir: Path | None,
    output_dir: Path | None,
    centroid: bool,
    skip_cleanup: bool = False,
    use_docker: bool = False,
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
        print("No .raw folders found.")
        return

    for idx, raw_dir in enumerate(raw_dirs, start=1):
        print(f"[SEQ] ({idx}/{len(raw_dirs)}) Processing {raw_dir}")
        result = process_single_raw(
            raw_dir=raw_dir,
            msconvert_path=paths.msconvert_path,
            output_dir=paths.mzml_dir,
            centroid=centroid,
            use_docker=use_docker,
            do_postprocess=do_postprocess,
        )

        if result.warnings:
            for w in result.warnings:
                print(f"  WARNING: {w}")

        if not result.success:
            print(f"  ERROR: {result.error}")
        else:
            print(f"  Wrote {result.mzml_path}")

        if result.qc:
            print(f"  TIC points: {len(result.qc.tic)}")
            print(f"  Max TIC: {max(result.qc.tic):.2f}")
            print(f"  Max BPC: {max(result.qc.bpc):.2f}")
            print(f"  Median peak count: {int(np.median(result.qc.peak_counts))}")

    print("\nAnnotation completed.\n")
