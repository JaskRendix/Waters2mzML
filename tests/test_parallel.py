import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from waters2mzml.job import JobResult
from waters2mzml.parallel import run_parallel


@pytest.fixture
def raw_dirs(tmp_path):
    """
    Create 3 fake .raw directories.
    """
    dirs = []
    for i in range(3):
        d = tmp_path / f"sample{i}.raw"
        d.mkdir()
        dirs.append(d)
    return dirs


def test_parallel_success(monkeypatch, tmp_path, raw_dirs):
    """
    Ensure run_parallel calls process_single_raw in parallel
    and aggregates JobResult objects.
    """

    def fake_process_single_raw(raw_dir, msconvert_path, output_dir, centroid):
        out = output_dir / f"{raw_dir.name}.mzML"
        out.write_text("dummy")
        return JobResult(raw_dir=raw_dir, mzml_path=out, success=True)

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    results = run_parallel(
        raw_dirs=raw_dirs,
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=3,
        executor_class=ThreadPoolExecutor,   # <-- FIX
    )

    assert len(results) == 3
    assert all(isinstance(r, JobResult) for r in results)
    assert all(r.success for r in results)
    assert all(r.mzml_path.exists() for r in results)


def test_parallel_failure(monkeypatch, tmp_path, raw_dirs):
    """
    Ensure failures inside workers are captured and returned as JobResult(success=False).
    """

    def fake_process_single_raw(raw_dir, msconvert_path, output_dir, centroid):
        raise RuntimeError(f"boom: {raw_dir.name}")

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    results = run_parallel(
        raw_dirs=raw_dirs,
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=2,
        executor_class=ThreadPoolExecutor,   # <-- FIX
    )

    assert len(results) == 3
    assert all(not r.success for r in results)
    assert all("boom" in r.error for r in results)


def test_parallel_mixed(monkeypatch, tmp_path, raw_dirs):
    """
    Ensure mixed success/failure is handled correctly.
    """

    def fake_process_single_raw(raw_dir, msconvert_path, output_dir, centroid):
        if "1" in raw_dir.name:
            raise ValueError("bad sample")
        out = output_dir / f"{raw_dir.name}.mzML"
        out.write_text("ok")
        return JobResult(raw_dir=raw_dir, mzml_path=out, success=True)

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    results = run_parallel(
        raw_dirs=raw_dirs,
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=3,
        executor_class=ThreadPoolExecutor,   # <-- FIX
    )

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0].error == "bad sample"


def test_parallel_respects_jobs(monkeypatch, tmp_path, raw_dirs):
    """
    Ensure that jobs=N actually spawns N workers.
    """

    active = 0
    max_active = 0

    def fake_process_single_raw(raw_dir, msconvert_path, output_dir, centroid):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        time.sleep(0.1)
        active -= 1
        return JobResult(raw_dir=raw_dir, mzml_path=None, success=True)

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    run_parallel(
        raw_dirs=raw_dirs,
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=2,
        executor_class=ThreadPoolExecutor,   # <-- FIX
    )

    assert max_active == 2
