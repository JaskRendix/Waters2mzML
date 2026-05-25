from __future__ import annotations

import time
import traceback
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .job import JobResult, process_single_raw
from .msconvert import MsconvertError


@dataclass
class RetryPolicy:
    max_retries: int = 0
    base_delay: float = 1.0  # seconds
    backoff_factor: float = 2.0  # exponential backoff


def _is_retryable(exc: Exception) -> bool:
    """
    Classify which errors are worth retrying.
    For now: only msconvert failures (native or docker).
    """
    return isinstance(exc, MsconvertError)


def _format_exception(exc: Exception) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _run_with_retries(
    raw_dir: Path,
    msconvert_path: Path,
    output_dir: Path,
    centroid: bool,
    use_docker: bool,
    do_postprocess: bool,
    retry_policy: RetryPolicy,
) -> JobResult:
    last_exc: Exception | None = None

    for attempt in range(retry_policy.max_retries + 1):
        try:
            return process_single_raw(
                raw_dir=raw_dir,
                msconvert_path=msconvert_path,
                output_dir=output_dir,
                centroid=centroid,
                use_docker=use_docker,
                do_postprocess=do_postprocess,
            )
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == retry_policy.max_retries:
                # Fatal or out of retries
                return JobResult(
                    raw_dir=raw_dir,
                    mzml_path=None,
                    success=False,
                    error=_format_exception(exc),
                )

            # Retryable: exponential backoff
            delay = retry_policy.base_delay * (retry_policy.backoff_factor**attempt)
            time.sleep(delay)

    # Should not reach here, but keep a safe fallback
    return JobResult(
        raw_dir=raw_dir,
        mzml_path=None,
        success=False,
        error=_format_exception(last_exc) if last_exc else "Unknown error",
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
    do_postprocess: bool = True,
) -> list[JobResult]:
    """
    Parallel execution wrapper with robust retry logic and per-job isolation.

    Public signature is preserved except for an extra keyword (do_postprocess),
    which defaults to True and matches process_single_raw.
    """
    raw_dirs = list(raw_dirs)
    results: list[JobResult] = []
    retry_policy = RetryPolicy(max_retries=retries)

    total = len(raw_dirs)
    if total == 0:
        print("No .raw folders found.")
        return []

    with executor_class(max_workers=jobs) as pool:
        futures = {
            pool.submit(
                _run_with_retries,
                raw_dir,
                msconvert_path,
                output_dir,
                centroid,
                use_docker,
                do_postprocess,
                retry_policy,
            ): raw_dir
            for raw_dir in raw_dirs
        }

        for idx, future in enumerate(as_completed(futures), start=1):
            raw_dir = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                # Catastrophic worker failure (should be rare)
                result = JobResult(
                    raw_dir=raw_dir,
                    mzml_path=None,
                    success=False,
                    error=_format_exception(exc),
                )

            results.append(result)

            status = "OK" if result.success else "FAIL"
            print(f"[{status}] ({idx}/{total}) {raw_dir}")
            if result.error:
                print(f"    Error: {result.error.splitlines()[-1]}")

    # Preserve deterministic ordering by raw_dir name
    results.sort(key=lambda r: str(r.raw_dir))
    return results
