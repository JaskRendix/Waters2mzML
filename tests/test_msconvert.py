import subprocess
from pathlib import Path

import pytest

from waters2mzml.config import ConversionConfig
from waters2mzml.msconvert import (
    MsconvertError,
    _run_msconvert_docker,
    _run_msconvert_native,
    run_msconvert,
)


@pytest.fixture
def raw_path(tmp_path):
    p = tmp_path / "sample.raw"
    p.mkdir()
    return p


@pytest.fixture
def config_native():
    return ConversionConfig(
        centroid=False,
        use_docker=False,
        docker_image=None,
    )


@pytest.fixture
def config_docker():
    return ConversionConfig(
        centroid=True,
        use_docker=True,
        docker_image="my/msconvert:latest",
    )


def test_run_msconvert_native_invokes_subprocess(raw_path, config_native, monkeypatch):
    calls = []

    def fake_run(cmd, shell, capture_output, text):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    msconvert_path = Path("/usr/bin/msconvert")
    out = run_msconvert(msconvert_path, raw_path, config_native)

    assert out == raw_path.with_suffix(".mzML")
    assert len(calls) == 1
    assert str(msconvert_path) in calls[0]
    assert str(raw_path) in calls[0]


def test_run_msconvert_native_error_raises_msconvert_error(
    raw_path, config_native, monkeypatch
):

    def fake_run(cmd, shell, capture_output, text):
        return subprocess.CompletedProcess(cmd, 127, "", "boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(MsconvertError):
        run_msconvert(Path("/usr/bin/msconvert"), raw_path, config_native)


def test_run_msconvert_docker_invokes_correct_docker_command(
    raw_path, config_docker, monkeypatch
):
    calls = []

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = _run_msconvert_docker(raw_path, config_docker)

    assert out == raw_path.with_suffix(".mzML")
    assert len(calls) == 1

    cmd = calls[0]

    # Basic structure
    assert cmd[0] == "docker"
    assert cmd[1] == "run"
    assert "--rm" in cmd

    # Volume mount correctness
    host_dir = str(raw_path.parent)
    assert f"{host_dir}:/data" in cmd

    # Image
    assert "my/msconvert:latest" in cmd

    # Raw file path inside container
    assert "/data/sample.raw" in cmd

    # msconvert args (centroid=True → includes peak picking)
    assert "--outdir" in cmd
    assert "/data" in cmd


def test_run_msconvert_docker_missing_image_raises(raw_path):
    config = ConversionConfig(
        centroid=False,
        use_docker=True,
        docker_image=None,
    )

    with pytest.raises(MsconvertError):
        _run_msconvert_docker(raw_path, config)


def test_run_msconvert_docker_error_raises_msconvert_error(
    raw_path, config_docker, monkeypatch
):

    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, 125, "", "docker boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(MsconvertError):
        _run_msconvert_docker(raw_path, config_docker)


def test_run_msconvert_dispatches_to_native(raw_path, config_native, monkeypatch):
    calls = []

    def fake_native(msconvert_path, raw_path, config):
        calls.append("native")
        return raw_path.with_suffix(".mzML")

    monkeypatch.setattr("waters2mzml.msconvert._run_msconvert_native", fake_native)

    out = run_msconvert(Path("/usr/bin/msconvert"), raw_path, config_native)

    assert out == raw_path.with_suffix(".mzML")
    assert calls == ["native"]


def test_run_msconvert_dispatches_to_docker(raw_path, config_docker, monkeypatch):
    calls = []

    def fake_docker(raw_path, config):
        calls.append("docker")
        return raw_path.with_suffix(".mzML")

    monkeypatch.setattr("waters2mzml.msconvert._run_msconvert_docker", fake_docker)

    out = run_msconvert(Path("/usr/bin/msconvert"), raw_path, config_docker)

    assert out == raw_path.with_suffix(".mzML")
    assert calls == ["docker"]


def test_build_args_default():
    cfg = ConversionConfig(
        centroid=False,
        use_docker=False,
        docker_image=None,
    )

    args = cfg.build_msconvert_args()

    assert "peakPicking" not in args


def test_build_args_centroid_enabled():
    cfg = ConversionConfig(
        centroid=True,
        use_docker=False,
        docker_image=None,
    )

    args = cfg.build_msconvert_args()

    assert "--filter" in args
    assert "peakPicking" in args or "peakpicking" in args.lower()


def test_build_args_is_string():
    cfg = ConversionConfig(
        centroid=False,
        use_docker=False,
        docker_image=None,
    )

    args = cfg.build_msconvert_args()
    assert isinstance(args, str)


def test_build_args_splits_cleanly():
    cfg = ConversionConfig(
        centroid=True,
        use_docker=False,
        docker_image=None,
    )

    args = cfg.build_msconvert_args()
    tokens = args.split()

    assert all(t.strip() for t in tokens)


def test_build_args_no_double_spaces():
    cfg = ConversionConfig(
        centroid=True,
        use_docker=False,
        docker_image=None,
    )

    args = cfg.build_msconvert_args()
    assert "  " not in args


def test_build_args_custom_flags(monkeypatch):
    cfg = ConversionConfig(
        centroid=False,
        use_docker=False,
        docker_image=None,
    )

    def fake_build(self):
        return "--foo --bar=123"

    monkeypatch.setattr(ConversionConfig, "build_msconvert_args", fake_build)

    args = cfg.build_msconvert_args()
    assert "--foo" in args
    assert "--bar=123" in args


def test_docker_image_required(tmp_path):
    raw = tmp_path / "sample.raw"
    raw.mkdir()

    cfg = ConversionConfig(centroid=False, use_docker=True, docker_image=None)

    with pytest.raises(MsconvertError):
        _run_msconvert_docker(raw, cfg)


def test_docker_command_construction(monkeypatch, tmp_path):
    raw = tmp_path / "sample.raw"
    raw.mkdir()

    cfg = ConversionConfig(
        centroid=True,
        use_docker=True,
        docker_image="my/image",
    )

    captured = {}

    def fake_run(cmd, capture_output, text):
        captured["cmd"] = cmd

        class P:
            returncode = 0
            stderr = ""

        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_msconvert_docker(raw, cfg)

    cmd = captured["cmd"]
    assert cmd[0] == "docker"
    assert "my/image" in cmd
    assert "/data/sample.raw" in cmd
    assert "--outdir" in cmd
