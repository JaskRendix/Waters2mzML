from waters2mzml.pipeline import run_pipeline, run_pipeline_parallel
from waters2mzml.qc import QCResult


def fake_msconvert(msconvert_path, raw_path, config):
    mzml_path = raw_path.with_suffix(".mzML")
    mzml_path.write_text(
        '<spectrumList count="2">\n'
        '<spectrum id="scan=1" function=1>\n'
        '<cvParam name="ms level" value="1"/>\n'
        "<binaryDataArrayList> scan=1 & stuff\n"
        '<spectrum id="scan=1" function=1>\n'
        '<spectrum id="scan=2" function=2>\n'
        '<cvParam name="ms level" value="1"/>\n'
        "<binaryDataArrayList> scan=2 & stuff\n"
        '<spectrum id="scan=2" function=2>\n'
        "</spectrumList>\n"
    )
    return mzml_path


def test_full_pipeline(tmp_path, monkeypatch):
    base = tmp_path
    raw_dir = base / "raw_files"
    out_dir = base / "mzML_files"
    raw_dir.mkdir()
    out_dir.mkdir()

    # Create fake .raw folder
    sample_raw = raw_dir / "sample.raw"
    sample_raw.mkdir()

    # _extern.inf with REFERENCE on function 3
    (sample_raw / "_extern.inf").write_bytes(
        b"Function Parameters - Function 1\n"
        b"Function Parameters - Function 2\n"
        b"Function Parameters - Function 3  REFERENCE\n"
    )

    # Create fake FUNC files for functions 1–5
    for func in range(1, 6):
        for suffix in ["_header.txt", "_data.txt"]:
            (sample_raw / f"FUNC{func:03d}{suffix}").write_text("dummy")

    # Patch msconvert
    monkeypatch.setattr("waters2mzml.job.run_msconvert", fake_msconvert)

    # Run pipeline
    run_pipeline(
        base_dir=base,
        input_dir=raw_dir,
        output_dir=out_dir,
        centroid=False,
    )

    # 1. Lockmass deletion
    remaining = {p.name for p in sample_raw.iterdir()}
    assert "FUNC001_header.txt" in remaining
    assert "FUNC002_header.txt" in remaining
    assert "FUNC003_header.txt" not in remaining
    assert "FUNC004_header.txt" not in remaining

    # 2. Output mzML exists
    out_files = list(out_dir.glob("*.mzML"))
    assert len(out_files) == 1
    out_mzml = out_files[0]

    # 3. Postprocessing applied
    text = out_mzml.read_text()
    assert "scan=1" in text
    assert "scan=2" in text
    assert 'value="2"' in text


def test_pipeline_passes_docker_image(monkeypatch, tmp_path):
    called = {}

    def fake_process(**kwargs):
        called.update(kwargs)

        class R:
            success = True
            warnings = []
            qc = None
            mzml_path = tmp_path / "x.mzML"
            raw_dir = tmp_path / "raw/sample.raw"
            error = None

        return R()

    monkeypatch.setattr("waters2mzml.pipeline.process_single_raw", fake_process)

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()

    out = tmp_path / "mzml"

    run_pipeline(
        base_dir=tmp_path,
        input_dir=raw,
        output_dir=out,
        centroid=False,
        use_docker=True,
        docker_image="img",
    )

    assert called["use_docker"] is True
    assert called["docker_image"] == "img"


def test_pipeline_no_raw_folders(tmp_path, caplog):

    raw = tmp_path / "raw"
    out = tmp_path / "out"
    raw.mkdir()
    out.mkdir()

    # No *.raw folders inside raw/
    run_pipeline(
        base_dir=tmp_path,
        input_dir=raw,
        output_dir=out,
        centroid=False,
    )

    assert "No .raw folders found" in caplog.text


def test_pipeline_failure_path(monkeypatch, tmp_path, caplog):

    class R:
        success = False
        warnings = []
        qc = None
        mzml_path = None
        raw_dir = tmp_path / "raw/sample.raw"
        error = "boom"

    def fake_process(**kwargs):
        return R()

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.setattr("waters2mzml.pipeline.process_single_raw", fake_process)

    run_pipeline(tmp_path, raw, out, centroid=False)

    assert "boom" in caplog.text


def test_pipeline_warnings_path(monkeypatch, tmp_path, caplog):

    class R:
        success = True
        warnings = ["w1", "w2"]
        qc = None
        mzml_path = tmp_path / "x.mzML"
        raw_dir = tmp_path / "raw/sample.raw"
        error = None

    def fake_process(**kwargs):
        return R()

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.setattr("waters2mzml.pipeline.process_single_raw", fake_process)

    run_pipeline(tmp_path, raw, out, centroid=False)

    assert "w1" in caplog.text
    assert "w2" in caplog.text


def test_pipeline_qc_logging(monkeypatch, tmp_path, caplog):

    class R:
        success = True
        warnings = []
        qc = QCResult(tic=[1.0, 2.0], bpc=[5.0, 6.0], peak_counts=[10, 20])
        mzml_path = tmp_path / "x.mzML"
        raw_dir = tmp_path / "raw/sample.raw"
        error = None

    def fake_process(**kwargs):
        return R()

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.setattr("waters2mzml.pipeline.process_single_raw", fake_process)

    run_pipeline(tmp_path, raw, out, centroid=False)

    assert "TIC=2" in caplog.text
    assert "MaxTIC=2.00" in caplog.text
    assert "MaxBPC=6.00" in caplog.text
    assert "MedianPeaks=15" in caplog.text


def test_pipeline_parallel_no_raw(tmp_path, caplog):

    raw = tmp_path / "raw"
    out = tmp_path / "out"
    raw.mkdir()
    out.mkdir()

    run_pipeline_parallel(
        base_dir=tmp_path,
        input_dir=raw,
        output_dir=out,
        centroid=False,
        jobs=2,
    )

    assert "No .raw folders found" in caplog.text


def test_pipeline_parallel_success_with_qc_and_warnings(monkeypatch, tmp_path, caplog):

    class R:
        success = True
        warnings = ["wA"]
        qc = QCResult(tic=[3.0], bpc=[7.0], peak_counts=[12])
        mzml_path = tmp_path / "x.mzML"
        raw_dir = tmp_path / "raw/sample.raw"
        error = None

    def fake_parallel(**kwargs):
        return [R()]

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.setattr("waters2mzml.pipeline.run_parallel", fake_parallel)

    run_pipeline_parallel(
        base_dir=tmp_path,
        input_dir=raw,
        output_dir=out,
        centroid=False,
        jobs=2,
    )

    assert "[OK]" in caplog.text
    assert "wA" in caplog.text
    assert "MaxBPC=7.00" in caplog.text


def test_pipeline_parallel_failure(monkeypatch, tmp_path, caplog):

    class R:
        success = False
        warnings = []
        qc = None
        mzml_path = None
        raw_dir = tmp_path / "raw/sample.raw"
        error = "fail"

    def fake_parallel(**kwargs):
        return [R()]

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.setattr("waters2mzml.pipeline.run_parallel", fake_parallel)

    run_pipeline_parallel(
        base_dir=tmp_path,
        input_dir=raw,
        output_dir=out,
        centroid=False,
        jobs=2,
    )

    assert "[FAIL]" in caplog.text
    assert "fail" in caplog.text


def test_pipeline_parallel_docker_passthrough(monkeypatch, tmp_path):

    called = {}

    def fake_parallel(**kwargs):
        called.update(kwargs)
        return []

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sample.raw").mkdir()
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.setattr("waters2mzml.pipeline.run_parallel", fake_parallel)

    run_pipeline_parallel(
        base_dir=tmp_path,
        input_dir=raw,
        output_dir=out,
        centroid=False,
        jobs=4,
        use_docker=True,
        docker_image="img",
    )

    assert called["use_docker"] is True
    assert called["docker_image"] == "img"
