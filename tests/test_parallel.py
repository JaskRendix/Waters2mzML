import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from waters2mzml.job import JobResult
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
    assert all(isinstance(r, JobResult) for r in results)
    assert all(r.success for r in results)
    assert all(r.mzml_path.exists() for r in results)


def test_parallel_failure(monkeypatch, tmp_path, raw_dirs):

    def fake_process_single_raw(
        raw_dir, msconvert_path, output_dir, centroid, *args, **kwargs
    ):
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
        executor_class=ThreadPoolExecutor,
    )

    assert len(results) == 3
    assert all(not r.success for r in results)
    assert all("boom" in r.error for r in results)


def test_parallel_mixed(monkeypatch, tmp_path, raw_dirs):

    def fake_process_single_raw(
        raw_dir, msconvert_path, output_dir, centroid, *args, **kwargs
    ):
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
        executor_class=ThreadPoolExecutor,
    )

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0].error == "bad sample"


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


def test_parallel_retries(monkeypatch, tmp_path, raw_dirs):

    call_count = {"n": 0}

    def fake_process_single_raw(
        raw_dir, msconvert_path, output_dir, centroid, *args, **kwargs
    ):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("temporary failure")
        out = output_dir / f"{raw_dir.name}.mzML"
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

    assert len(results) == 1
    assert results[0].success
    assert call_count["n"] == 3


def test_parallel_retry_exhaustion(monkeypatch, tmp_path, raw_dirs):

    def fake_process_single_raw(*args, **kwargs):
        raise RuntimeError("always fails")

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

    assert len(results) == 1
    assert not results[0].success
    assert "always fails" in results[0].error


def test_parallel_retry_isolation(monkeypatch, tmp_path, raw_dirs):
    call_count = {"bad": 0}

    def fake_process_single_raw(raw_dir, *args, **kwargs):
        if raw_dir.name == "sample1.raw":
            call_count["bad"] += 1
            raise RuntimeError("bad file")
        out = tmp_path / "out" / f"{raw_dir.name}.mzML"
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
        retries=2,
        executor_class=ThreadPoolExecutor,
    )

    assert call_count["bad"] == 3

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0].raw_dir.name == "sample1.raw"


def test_parallel_retry_mixed(monkeypatch, tmp_path, raw_dirs):
    call_count = {
        "sample0.raw": 0,
        "sample1.raw": 0,
        "sample2.raw": 0,
    }

    def fake_process_single_raw(raw_dir, *args, **kwargs):
        name = raw_dir.name
        call_count[name] += 1

        if name == "sample0.raw":
            if call_count[name] < 3:
                raise RuntimeError("temporary")
            out = tmp_path / "out" / f"{name}.mzML"
            out.write_text("ok")
            return JobResult(raw_dir=raw_dir, mzml_path=out, success=True)

        if name == "sample1.raw":
            raise RuntimeError("permanent")

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

    assert call_count["sample0.raw"] == 3
    assert call_count["sample1.raw"] == 6
    assert call_count["sample2.raw"] == 1

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0].raw_dir.name == "sample1.raw"
