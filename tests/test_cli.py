import pytest

from waters2mzml.cli import convert


def test_docker_without_image_errors(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    out = tmp_path / "mzml"
    out.mkdir()

    with pytest.raises(Exception) as exc:
        convert(
            input=raw,
            output=out,
            centroid=False,
            base_dir=tmp_path,
            parallel=1,
            docker=True,
            docker_image=None,
            retries=0,
            log_level="INFO",
        )

    assert "docker-image" in str(exc.value).lower()


def test_docker_with_image_passes_validation(tmp_path, monkeypatch):
    called = {}

    def fake_pipeline(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr("waters2mzml.cli.run_pipeline", fake_pipeline)

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()

    out = tmp_path / "mzml"
    out.mkdir()

    convert(
        input=raw,
        output=out,
        centroid=False,
        base_dir=tmp_path,
        parallel=1,
        docker=True,
        docker_image="my/image",
        retries=0,
        log_level="INFO",
    )

    assert called["use_docker"] is True
    assert called["docker_image"] == "my/image"


def test_parallel_pipeline_receives_docker_image(tmp_path, monkeypatch):
    called = {}

    def fake_parallel(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr("waters2mzml.cli.run_pipeline_parallel", fake_parallel)

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()

    out = tmp_path / "mzml"
    out.mkdir()

    convert(
        input=raw,
        output=out,
        centroid=False,
        base_dir=tmp_path,
        parallel=4,
        docker=True,
        docker_image="pwiz/msconvert",
        retries=0,
        log_level="INFO",
    )

    assert called["use_docker"] is True
    assert called["docker_image"] == "pwiz/msconvert"
    assert called["jobs"] == 4


def test_native_mode_does_not_require_image(tmp_path, monkeypatch):
    called = {}

    def fake_pipeline(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr("waters2mzml.cli.run_pipeline", fake_pipeline)

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()

    out = tmp_path / "mzml"
    out.mkdir()

    convert(
        input=raw,
        output=out,
        centroid=False,
        base_dir=tmp_path,
        parallel=1,
        docker=False,
        docker_image=None,
        retries=0,
        log_level="INFO",
    )

    assert called["use_docker"] is False
    assert called["docker_image"] is None


def test_invalid_paths_fail_cleanly(tmp_path, caplog):
    out = tmp_path / "mzml"
    out.mkdir()

    convert(
        input=tmp_path / "does_not_exist",
        output=out,
        centroid=False,
        base_dir=tmp_path,
        parallel=1,
        docker=False,
        docker_image=None,
        retries=0,
        log_level="INFO",
    )

    # The pipeline should NOT raise — it should log a message
    assert "no .raw folders found" in caplog.text.lower()
