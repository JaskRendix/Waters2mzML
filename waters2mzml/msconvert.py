from __future__ import annotations

import subprocess
from pathlib import Path

from .config import ConversionConfig


class MsconvertError(RuntimeError):
    """Failure while running msconvert (native or Docker)."""

    def __init__(
        self, message: str, returncode: int | None = None, stderr: str | None = None
    ):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr or ""


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
    proc = subprocess.run(args, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MsconvertError(
            f"msconvert failed (native) with code {proc.returncode}",
            returncode=proc.returncode,
            stderr=proc.stderr,
        )
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
    if not docker_image:
        raise MsconvertError(
            "Docker image is not configured for msconvert (docker_image is None)"
        )

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

    proc = subprocess.run(docker_args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MsconvertError(
            f"msconvert failed (docker) with code {proc.returncode}",
            returncode=proc.returncode,
            stderr=proc.stderr,
        )

    return raw_path.with_suffix(".mzML")
