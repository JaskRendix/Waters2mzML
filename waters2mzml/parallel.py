from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .job import JobResult, process_single_raw


def run_parallel(
    raw_dirs: Iterable[Path],
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
    jobs: int,
    executor_class=ProcessPoolExecutor,  # <-- NEW
) -> list[JobResult]:
    """
    Parallel execution wrapper. Uses ProcessPoolExecutor by default,
    but tests can override executor_class to ThreadPoolExecutor.
    """
    raw_dirs = list(raw_dirs)
    results: list[JobResult] = []

    with executor_class(max_workers=jobs) as pool:
        futures = {
            pool.submit(
                process_single_raw,
                raw_dir,
                msconvert_path,
                output_dir,
                centroid,
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
