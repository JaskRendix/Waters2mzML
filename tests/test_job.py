from pathlib import Path

from waters2mzml.job import JobResult, process_single_raw


def test_job_success(monkeypatch, tmp_path):
    """
    Ensure process_single_raw runs all steps and returns a successful JobResult.
    """

    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    # Fake annotation: return one ms2 object
    def fake_annotate(raw_dirs):
        assert raw_dirs == [raw_dir]
        return ["MS2-DATA"]

    monkeypatch.setattr("waters2mzml.job.annotate_all_raw", fake_annotate)

    # Fake msconvert: write a dummy mzML file
    def fake_msconvert(msconvert_path, raw_path, config):
        assert raw_path == raw_dir
        out = raw_path.with_suffix(".mzML")
        out.write_text("mzML")
        return out

    monkeypatch.setattr("waters2mzml.job.run_msconvert", fake_msconvert)

    # Fake postprocess: just assert correct args
    def fake_postprocess(mzml_path, ms2):
        assert mzml_path.name == "sample.mzML"
        assert ms2 == "MS2-DATA"

    monkeypatch.setattr("waters2mzml.job.postprocess_mzml", fake_postprocess)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = process_single_raw(
        raw_dir=raw_dir,
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
    )

    assert isinstance(result, JobResult)
    assert result.success
    assert result.error is None
    assert result.mzml_path == output_dir / "sample.mzML"
    assert result.mzml_path.exists()


def test_job_failure(monkeypatch, tmp_path):
    """
    Ensure process_single_raw returns a failure JobResult when any step raises.
    """

    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    # Force annotation to fail
    def fake_annotate(raw_dirs):
        raise RuntimeError("annotate failed")

    monkeypatch.setattr("waters2mzml.job.annotate_all_raw", fake_annotate)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = process_single_raw(
        raw_dir=raw_dir,
        msconvert_path=Path("/fake/msconvert.exe"),
        output_dir=output_dir,
        centroid=False,
    )

    assert isinstance(result, JobResult)
    assert not result.success
    assert result.mzml_path is None
    assert "annotate failed" in result.error
