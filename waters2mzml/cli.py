from __future__ import annotations

from pathlib import Path

import typer

from .pipeline import run_pipeline

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
    jobs: int = typer.Option(1, "--jobs", "-j", help="Parallel workers"),
    docker: bool = typer.Option(
        False,
        "--docker",
        help="Run msconvert inside a Docker container (requires a user-provided image)",
    ),
):
    """
    Convert Waters .raw data to mzML and annotate scans/MS levels.
    """
    from .config import default_paths
    from .parallel import run_parallel
    from .paths import list_raw_folders

    paths = default_paths(base_dir)
    paths.raw_dir = input
    paths.mzml_dir = output

    raw_dirs = list_raw_folders(input)

    if jobs == 1:
        run_pipeline(
            base_dir,
            input,
            output,
            centroid,
            use_docker=docker,
        )
    else:
        results = run_parallel(
            raw_dirs=raw_dirs,
            msconvert_path=paths.msconvert_path,
            output_dir=output,
            centroid=centroid,
            jobs=jobs,
            use_docker=docker,
        )

        failures = [r for r in results if not r.success]
        if failures:
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
