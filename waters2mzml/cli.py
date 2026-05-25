from __future__ import annotations

import logging
from pathlib import Path

import typer

from .pipeline import run_pipeline, run_pipeline_parallel

app = typer.Typer(help="Waters .raw → .mzML conversion and annotation tool")


def setup_logging(level: str) -> None:
    """
    Configure global structured logging.
    Safe to call multiple times.
    """
    logger = logging.getLogger("waters2mzml")

    if logger.handlers:
        return  # already configured

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level.upper())


@app.command()
def convert(
    input: Path = typer.Option(
        ..., "--input", "-i", help="Directory containing .raw folders"
    ),
    output: Path = typer.Option(
        ..., "--output", "-o", help="Directory for .mzML output"
    ),
    centroid: bool = typer.Option(
        False,
        "--centroid/--no-centroid",
        help="Apply CWT peak picking (profile → centroid)",
    ),
    base_dir: Path = typer.Option(
        Path.cwd(), "--base-dir", help="Base directory (default: CWD)"
    ),
    parallel: int = typer.Option(
        1,
        "--parallel",
        "-p",
        help="Number of parallel workers (1 = sequential)",
    ),
    docker: bool = typer.Option(
        False,
        "--docker",
        help="Run msconvert inside a Docker container",
    ),
    docker_image: str | None = typer.Option(
        None,
        "--docker-image",
        help="Docker image containing msconvert (required with --docker)",
    ),
    retries: int = typer.Option(
        0,
        "--retries",
        "-r",
        help="Retry failed msconvert jobs this many times",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
):
    """
    Convert Waters .raw data to mzML and annotate scans/MS levels.
    Supports both sequential and parallel execution.
    """
    setup_logging(log_level)

    if docker and not docker_image:
        raise typer.BadParameter("You must specify --docker-image when using --docker")

    if parallel <= 1:
        # Sequential pipeline
        run_pipeline(
            base_dir=base_dir,
            input_dir=input,
            output_dir=output,
            centroid=centroid,
            use_docker=docker,
            docker_image=docker_image,
        )
    else:
        # Parallel pipeline
        run_pipeline_parallel(
            base_dir=base_dir,
            input_dir=input,
            output_dir=output,
            centroid=centroid,
            jobs=parallel,
            use_docker=docker,
            retries=retries,
            docker_image=docker_image,
        )


if __name__ == "__main__":
    app()
