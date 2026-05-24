from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .job import JobResult, process_single_raw


def _run_with_retries(
    raw_dir: Path,
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
    retries: int,
    use_docker: bool,
) -> JobResult:
    last_exc = None

    for attempt in range(retries + 1):
        try:
            return process_single_raw(
                raw_dir,
                msconvert_path,
                output_dir,
                centroid,
                use_docker=use_docker,
            )
        except Exception as exc:
            last_exc = exc

    return JobResult(
        raw_dir=raw_dir,
        mzml_path=None,
        success=False,
        error=str(last_exc),
    )


def run_parallel(
    raw_dirs: Iterable[Path],
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
    jobs: int,
    use_docker: bool = False,
    retries: int = 0,
    executor_class=ProcessPoolExecutor,
) -> list[JobResult]:
    """
    Parallel execution wrapper with retry logic.
    Uses ProcessPoolExecutor by default, but tests can override executor_class.
    """
    raw_dirs = list(raw_dirs)
    results: list[JobResult] = []

    with executor_class(max_workers=jobs) as pool:
        futures = {
            pool.submit(
                _run_with_retries,
                raw_dir,
                msconvert_path,
                output_dir,
                centroid,
                retries,
                use_docker,
            ): raw_dir
            for raw_dir in raw_dirs
        }

        for idx, future in enumerate(as_completed(futures), start=1):
            raw_dir = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = JobResult(
                    raw_dir=raw_dir,
                    mzml_path=None,
                    success=False,
                    error=str(exc),
                )

            results.append(result)

            status = "OK" if result.success else "FAIL"
            print(f"[{status}] ({idx}/{len(raw_dirs)}) {raw_dir}")
            if result.error:
                print(f"    Error: {result.error}")

    return results
