from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .job import JobResult, process_single_raw
from .msconvert import MsconvertError

logger = logging.getLogger("waters2mzml.parallel")


@dataclass
class RetryPolicy:
    max_retries: int = 0
    base_delay: float = 1.0
    backoff_factor: float = 2.0


def _progress_bar(done: int, total: int, width: int = 30) -> str:
    """
    Render a simple text progress bar.
    Example: [██████------] 6/12
    """
    filled = int(width * done / total)
    bar = "█" * filled + "-" * (width - filled)
    return f"[{bar}] {done}/{total}"


def _is_retryable(exc: Exception) -> bool:
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
    start = time.perf_counter()
    last_exc: Exception | None = None

    for attempt in range(retry_policy.max_retries + 1):
        try:
            logger.debug(f"Starting job for {raw_dir} (attempt {attempt+1})")
            result = process_single_raw(
                raw_dir=raw_dir,
                msconvert_path=msconvert_path,
                output_dir=output_dir,
                centroid=centroid,
                use_docker=use_docker,
                do_postprocess=do_postprocess,
            )
            duration = time.perf_counter() - start
            logger.info(f"Job completed for {raw_dir} in {duration:.2f}s")
            return result

        except Exception as exc:
            last_exc = exc

            if not _is_retryable(exc):
                duration = time.perf_counter() - start
                logger.error(f"Fatal error on {raw_dir} after {duration:.2f}s: {exc}")
                return JobResult(
                    raw_dir=raw_dir,
                    mzml_path=None,
                    success=False,
                    error=_format_exception(exc),
                )

            if attempt == retry_policy.max_retries:
                duration = time.perf_counter() - start
                logger.error(
                    f"Retries exhausted for {raw_dir} after {duration:.2f}s: {exc}"
                )
                return JobResult(
                    raw_dir=raw_dir,
                    mzml_path=None,
                    success=False,
                    error=_format_exception(exc),
                )

            delay = retry_policy.base_delay * (retry_policy.backoff_factor**attempt)
            logger.warning(
                f"Retryable msconvert failure on {raw_dir}: {exc}. "
                f"Retrying in {delay:.1f}s (attempt {attempt+1}/{retry_policy.max_retries})"
            )
            time.sleep(delay)

    duration = time.perf_counter() - start
    logger.error(f"Unknown failure on {raw_dir} after {duration:.2f}s")
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
        logger.info("No .raw folders found")
        return []

    logger.info(f"Submitting {total} jobs with {jobs} workers")

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
                logger.error(f"Worker crashed on {raw_dir}: {exc}")
                result = JobResult(
                    raw_dir=raw_dir,
                    mzml_path=None,
                    success=False,
                    error=_format_exception(exc),
                )

            results.append(result)

            # Progress bar
            bar = _progress_bar(idx, total)
            if result.success:
                logger.info(f"{bar} [OK]   {raw_dir}")
            else:
                logger.error(
                    f"{bar} [FAIL] {raw_dir} — {result.error.splitlines()[-1]}"
                )

    ok = sum(r.success for r in results)
    fail = total - ok
    logger.info(f"Completed {total} jobs: {ok} OK, {fail} failed")
    results.sort(key=lambda r: str(r.raw_dir))
    return results
