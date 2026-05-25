import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from waters2mzml.job import JobResult
from waters2mzml.msconvert import MsconvertError
from waters2mzml.parallel import run_parallel


@pytest.fixture
def raw_dirs(tmp_path):
    dirs = []
    for i in range(3):
        d = tmp_path / f"sample{i}.raw"
        d.mkdir()
        dirs.append(d)
    return dirs


def test_parallel_success(monkeypatch, tmp_path, raw_dirs):

    def fake_process_single_raw(
        raw_dir, msconvert_path, output_dir, centroid, *args, **kwargs
    ):
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
        executor_class=ThreadPoolExecutor,
    )

    assert len(results) == 3
    assert all(r.success for r in results)
    assert all(r.mzml_path.exists() for r in results)


def test_parallel_non_retryable_failure(monkeypatch, tmp_path, raw_dirs):

    def fake_process_single_raw(*args, **kwargs):
        raise RuntimeError("fatal error")

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
        executor_class=ThreadPoolExecutor,
        retries=5,  # should NOT retry RuntimeError
    )

    assert len(results) == 3
    assert all(not r.success for r in results)
    assert all("fatal error" in r.error for r in results)


def test_parallel_msconvert_retries(monkeypatch, tmp_path, raw_dirs):

    call_count = {"n": 0}

    def fake_process_single_raw(raw_dir, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise MsconvertError("temporary msconvert failure")
        out = tmp_path / "out" / f"{raw_dir.name}.mzML"
        out.write_text("ok")
        return JobResult(raw_dir=raw_dir, mzml_path=out, success=True)

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    results = run_parallel(
        raw_dirs=[raw_dirs[0]],
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=1,
        retries=5,
        executor_class=ThreadPoolExecutor,
    )

    assert results[0].success
    assert call_count["n"] == 3  # retried twice


def test_parallel_msconvert_retry_exhaustion(monkeypatch, tmp_path, raw_dirs):

    def fake_process_single_raw(*args, **kwargs):
        raise MsconvertError("always fails")

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    results = run_parallel(
        raw_dirs=[raw_dirs[0]],
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=1,
        retries=3,
        executor_class=ThreadPoolExecutor,
    )

    assert not results[0].success
    assert "always fails" in results[0].error


def test_parallel_mixed_retry_model(monkeypatch, tmp_path, raw_dirs):
    call_count = {
        "sample0.raw": 0,
        "sample1.raw": 0,
        "sample2.raw": 0,
    }

    def fake_process_single_raw(raw_dir, *args, **kwargs):
        name = raw_dir.name
        call_count[name] += 1

        # sample0: msconvert retryable
        if name == "sample0.raw":
            if call_count[name] < 3:
                raise MsconvertError("temporary")
            out = tmp_path / "out" / f"{name}.mzML"
            out.write_text("ok")
            return JobResult(raw_dir=raw_dir, mzml_path=out, success=True)

        # sample1: fatal annotation/postprocess error
        if name == "sample1.raw":
            raise RuntimeError("fatal")

        # sample2: success
        out = tmp_path / "out" / f"{name}.mzML"
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
        retries=5,
        executor_class=ThreadPoolExecutor,
    )

    # sample0: retried twice, then success
    assert call_count["sample0.raw"] == 3

    # sample1: fatal, no retries
    assert call_count["sample1.raw"] == 1

    # sample2: success
    assert call_count["sample2.raw"] == 1

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0].raw_dir.name == "sample1.raw"


def test_parallel_respects_jobs(monkeypatch, tmp_path, raw_dirs):

    active = 0
    max_active = 0

    def fake_process_single_raw(
        raw_dir, msconvert_path, output_dir, centroid, *args, **kwargs
    ):
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
        executor_class=ThreadPoolExecutor,
    )

    assert max_active == 2


def test_parallel_docker_retry(monkeypatch, tmp_path, raw_dirs):

    call_count = {"n": 0}

    def fake_process_single_raw(raw_dir, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise MsconvertError("docker failure")
        out = tmp_path / "out" / f"{raw_dir.name}.mzML"
        out.write_text("ok")
        return JobResult(raw_dir=raw_dir, mzml_path=out, success=True)

    monkeypatch.setattr(
        "waters2mzml.parallel.process_single_raw", fake_process_single_raw
    )

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    results = run_parallel(
        raw_dirs=[raw_dirs[0]],
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
        jobs=1,
        retries=3,
        executor_class=ThreadPoolExecutor,
        use_docker=True,
    )

    assert results[0].success
    assert call_count["n"] == 2
