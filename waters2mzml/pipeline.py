from __future__ import annotations

import shutil
from pathlib import Path

from .config import ConversionConfig, default_paths
from .msconvert import run_msconvert
from .mzml_postprocess import postprocess_mzml
from .paths import clean_raw_folder, ensure_dirs, find_mzml_files, list_raw_folders
from .raw_annotation import annotate_all_raw


def run_pipeline(
    base_dir: Path,
    input_dir: Path | None,
    output_dir: Path | None,
    centroid: bool,
    skip_cleanup: bool = False,
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

    ms2_list = annotate_all_raw(raw_dirs)

    config = ConversionConfig(centroid=centroid)
    mzml_paths: list[Path] = []
    for raw_dir in raw_dirs:
        print(f"Converting {raw_dir} ...")
        mzml_path = run_msconvert(paths.msconvert_path, raw_dir, config)
        print(f"Conversion completed: {mzml_path}")
        mzml_paths.append(mzml_path)

    # Post-process and move to output dir
    for mzml_path, ms2 in zip(mzml_paths, ms2_list):
        print(f"Annotating {mzml_path} ...")
        postprocess_mzml(mzml_path, ms2)
        dest = paths.mzml_dir / mzml_path.name
        shutil.move(str(mzml_path), dest)
        print(f"Annotated file written to {dest}")

    print("\nannotation completed!\n")
