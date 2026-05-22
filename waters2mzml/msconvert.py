from __future__ import annotations

import subprocess
from pathlib import Path

from .config import ConversionConfig


def run_msconvert(
    msconvert_path: Path, raw_path: Path, config: ConversionConfig
) -> Path:
    """
    Run msconvert on a single .raw folder/file and return the resulting mzML path(s).
    Mirrors original:
      subprocess.call(msconvert + " " + i + config)
    """
    args = f'"{msconvert_path}" "{raw_path}" {config.build_msconvert_args()}'
    # For now, simple call; later: check returncode, capture stderr, etc.
    subprocess.check_call(args, shell=True)
    # msconvert writes mzML into same directory as input
    mzml_path = raw_path.with_suffix(".mzML")
    return mzml_path
