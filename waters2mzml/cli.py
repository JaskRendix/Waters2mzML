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
        help="Apply CWT peak picking (profile → centroid) like original script's 'y' option",
    ),
    base_dir: Path = typer.Option(
        Path.cwd(), "--base-dir", help="Base directory (default: CWD)"
    ),
):
    """
    Convert Waters .raw data to mzML and annotate scans/MS levels.
    """
    run_pipeline(
        base_dir=base_dir, input_dir=input, output_dir=output, centroid=centroid
    )


if __name__ == "__main__":
    app()
