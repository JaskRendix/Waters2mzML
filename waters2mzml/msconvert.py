from __future__ import annotations

import subprocess
from pathlib import Path

from .config import ConversionConfig


def run_msconvert(
    msconvert_path: Path, raw_path: Path, config: ConversionConfig
) -> Path:
    """
    Run msconvert on a single .raw folder/file and return the resulting mzML path.
    """
    if config.use_docker:
        return _run_msconvert_docker(raw_path, config)
    else:
        return _run_msconvert_native(msconvert_path, raw_path, config)


def _run_msconvert_native(
    msconvert_path: Path, raw_path: Path, config: ConversionConfig
) -> Path:
    args = f'"{msconvert_path}" "{raw_path}" {config.build_msconvert_args()}'
    subprocess.check_call(args, shell=True)
    return raw_path.with_suffix(".mzML")


def _run_msconvert_docker(raw_path: Path, config: ConversionConfig) -> Path:
    """
    Run msconvert inside a Docker container.

    We mount the parent directory of the .raw folder to /data inside the container
    and call msconvert on /data/<raw_name>.raw, writing mzML next to it.
    """
    raw_path = raw_path.resolve()
    host_dir = raw_path.parent
    raw_name = raw_path.name

    docker_image = config.docker_image
    container_dir = "/data"
    container_raw = f"{container_dir}/{raw_name}"

    docker_args = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{host_dir}:{container_dir}",
        docker_image,
        container_raw,
        *config.build_msconvert_args().split(),
        "--outdir",
        container_dir,
    ]

    subprocess.check_call(docker_args)

    return raw_path.with_suffix(".mzML")
