from pathlib import Path

from waters2mzml.job import JobResult, process_single_raw
from waters2mzml.qc import QCResult
from waters2mzml.raw_annotation import RawAnnotationResult


def test_job_success(monkeypatch, tmp_path):
    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    # Fake annotation: return one ms2 object
    def fake_annotate(raw_dirs):
        assert raw_dirs == [raw_dir]
        return [
            RawAnnotationResult(
                raw_dir=raw_dir,
                lockmass_function=7,  # any int is fine
                warnings=[],
                errors=[],
                extern_lines=1,
                func_files_found=0,
                func_files_deleted=0,
            )
        ]

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
        assert ms2 == 7

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


def test_job_qc_returned(monkeypatch, tmp_path):
    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    # Fake annotation
    monkeypatch.setattr(
        "waters2mzml.job.annotate_all_raw",
        lambda raw_dirs: [
            RawAnnotationResult(
                raw_dir=raw_dir,
                lockmass_function=3,
                warnings=[],
                errors=[],
                extern_lines=1,
                func_files_found=0,
                func_files_deleted=0,
            )
        ],
    )

    # Fake msconvert
    def fake_msconvert(msconvert_path, raw_path, config):
        out = raw_path.with_suffix(".mzML")
        out.write_text("mzML")
        return out

    monkeypatch.setattr("waters2mzml.job.run_msconvert", fake_msconvert)

    # Fake QC
    qc = QCResult(tic=[1.0], bpc=[2.0], peak_counts=[3])
    monkeypatch.setattr("waters2mzml.job.postprocess_mzml", lambda p, f: qc)

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = process_single_raw(
        raw_dir=raw_dir,
        msconvert_path=Path("/fake"),
        output_dir=out_dir,
        centroid=False,
        do_postprocess=True,
    )

    assert result.qc is qc


def test_job_qc_skipped(monkeypatch, tmp_path):
    raw_dir = tmp_path / "sample.raw"
    raw_dir.mkdir()

    monkeypatch.setattr(
        "waters2mzml.job.annotate_all_raw",
        lambda raw_dirs: [
            RawAnnotationResult(
                raw_dir=raw_dir,
                lockmass_function=3,
                warnings=[],
                errors=[],
                extern_lines=1,
                func_files_found=0,
                func_files_deleted=0,
            )
        ],
    )

    monkeypatch.setattr(
        "waters2mzml.job.run_msconvert", lambda p, r, c: r.with_suffix(".mzML")
    )

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = process_single_raw(
        raw_dir=raw_dir,
        msconvert_path=Path("/fake"),
        output_dir=out_dir,
        centroid=False,
        do_postprocess=False,
    )

    assert result.qc is None


def test_postprocess_synthetic(tmp_path):
    from waters2mzml.mzml_postprocess import postprocess_mzml

    mzml = tmp_path / "fake.mzML"
    mzml.write_text(
        "<binaryDataArrayList> scan=1 & stuff\n"
        '<cvParam name="ms level" value="1"/>\n'
    )

    qc = postprocess_mzml(mzml, lockmass_func=3)

    assert qc is None
    text = mzml.read_text()
    assert "scan=1" in text
