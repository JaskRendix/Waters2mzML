from __future__ import annotations

from pathlib import Path

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
        )

        if result.warnings:
            for w in result.warnings:
                print(f"  WARNING: {w}")

        if not result.success:
            print(f"  ERROR: {result.error}")
        else:
            print(f"  Wrote {result.mzml_path}")

    print("\nAnnotation completed.\n")
