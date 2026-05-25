from __future__ import annotations

from pathlib import Path

import typer

from .pipeline import run_pipeline, run_pipeline_parallel

app = typer.Typer(help="Waters .raw → .mzML conversion and annotation tool")


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
        help="Run msconvert inside a Docker container (requires a user-provided image)",
    ),
    retries: int = typer.Option(
        0,
        "--retries",
        "-r",
        help="Retry failed msconvert jobs this many times",
    ),
):
    """
    Convert Waters .raw data to mzML and annotate scans/MS levels.
    Supports both sequential and parallel execution.
    """
    if parallel <= 1:
        # Sequential pipeline
        run_pipeline(
            base_dir=base_dir,
            input_dir=input,
            output_dir=output,
            centroid=centroid,
            use_docker=docker,
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
        )


if __name__ == "__main__":
    app()
