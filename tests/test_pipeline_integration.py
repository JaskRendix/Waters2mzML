from waters2mzml.pipeline import run_pipeline


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
