import pytest

from waters2mzml.pipeline import run_pipeline


@pytest.mark.parametrize(
    "sample",
    [
        "sample1",
        "sample2",
        "sample3",
        "sample4",
        "sample5",
        "sample6",
        "sample7",
        "sample8",
        "sample9",
        "sample10",
    ],
)
def test_regression(make_fixture, tmp_path, monkeypatch, sample):
    # Create raw folder + expected mzML
    raw_dir, expected_mzml = make_fixture(tmp_path, sample)

    # Fake msconvert: write expected mzML as if msconvert produced it
    def fake_msconvert(msconvert_path, raw_path, config):
        produced = raw_path.with_suffix(".mzML")
        produced.write_text(expected_mzml.read_text())
        return produced

    # IMPORTANT: patch the function where pipeline imports it
    monkeypatch.setattr("waters2mzml.job.run_msconvert", fake_msconvert)

    # Run pipeline
    out_dir = tmp_path / "out"
    run_pipeline(
        base_dir=tmp_path,
        input_dir=raw_dir.parent,
        output_dir=out_dir,
        centroid=False,
        skip_cleanup=True,
        do_postprocess=False,
    )

    # Compare output to expected
    out_files = list(out_dir.glob("*.mzML"))
    assert len(out_files) == 1
    output = out_files[0]

    assert output.read_text() == expected_mzml.read_text()
