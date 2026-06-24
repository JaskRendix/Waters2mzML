from waters2mzml.mzml_postprocess import (
    _fix_ms_levels,
    _read_text,
    _renumber_scans,
    _write_text,
    postprocess_mzml,
)


def test_renumber_scans_simple():
    lines = [
        '<spectrumList count="2">',
        '<spectrum id="scan=1" ...>',
        "<binaryDataArrayList> scan=1 & stuff",
        '<spectrum id="scan=1" ...>',
        '<spectrum id="scan=2" ...>',
        "<binaryDataArrayList> scan=2 & stuff",
        '<spectrum id="scan=2" ...>',
    ]

    out = _renumber_scans(lines.copy())

    # Expected chronological IDs:
    # scan 1 → 1,1,1
    # scan 2 → 2,2,2
    assert sum("scan=1" in line for line in out) == 3
    assert sum("scan=2" in line for line in out) == 3
    assert "scan=3" not in "".join(out)


def test_fix_ms_levels_changes_ms2():
    lines = [
        '<spectrum id="scan=1" function=1>',
        '<cvParam name="ms level" value="1"/>',
        '<spectrum id="scan=2" function=2>',
        '<cvParam name="ms level" value="1"/>',  # should become 2
        "<binaryDataArrayList> function=2",
        '<cvParam name="ms level" value="1"/>',  # should become 2
        '<spectrumList count="2">',
    ]

    out = _fix_ms_levels(lines.copy(), lockmass_func=3)

    # All function=2 MS levels must be corrected to 2
    assert 'value="2"' in out[3]
    assert 'value="2"' in out[5]


def test_fix_ms_levels_no_change_if_already_correct():
    lines = [
        '<spectrum id="scan=1" function=1>',
        '<cvParam name="ms level" value="1"/>',
        '<spectrum id="scan=2" function=2>',
        '<cvParam name="ms level" value="2"/>',  # already correct
        "<binaryDataArrayList> function=2",
        '<cvParam name="ms level" value="2"/>',
    ]

    out = _fix_ms_levels(lines.copy(), lockmass_func=3)

    assert out == lines


import re


def test_renumber_scans_repeated_blocks():
    lines = [
        '<spectrum id="scan=5">',
        "<binaryDataArrayList> scan=5",
        '<spectrum id="scan=5">',
        '<spectrum id="scan=6">',
        "<binaryDataArrayList> scan=6",
    ]
    out = _renumber_scans(lines)

    assert len(re.findall(r"scan=1\b", "".join(out))) == 3
    assert len(re.findall(r"scan=2\b", "".join(out))) == 2


def test_renumber_scans_ignores_non_scan_lines():
    lines = ["no scan here", "<foo>", "<bar>"]
    out = _renumber_scans(lines)
    assert out == lines


def test_renumber_scans_out_of_order():
    lines = [
        '<spectrum id="scan=10">',
        '<spectrum id="scan=3">',
        '<spectrum id="scan=10">',
    ]
    out = _renumber_scans(lines)

    assert "scan=1" in out[0]
    assert "scan=2" in out[1]
    assert "scan=3" in out[2]


def test_fix_ms_levels_multiple_function_blocks():
    lines = [
        '<spectrum id="scan=1" function=2>',
        '<cvParam name="ms level" value="1"/>',
        '<spectrum id="scan=2" function=3>',
        '<cvParam name="ms level" value="1"/>',
    ]
    out = _fix_ms_levels(lines, lockmass_func=4)

    # Both function=2 and function=3 should change
    assert 'value="2"' in out[1]
    assert 'value="2"' in out[3]


def test_fix_ms_levels_function1_unchanged():
    lines = [
        '<spectrum id="scan=1" function=1>',
        '<cvParam name="ms level" value="1"/>',
    ]
    out = _fix_ms_levels(lines, lockmass_func=3)
    assert out == lines


def test_fix_ms_levels_no_mslevel_after_function():
    lines = [
        '<spectrum id="scan=1" function=2>',
        "<binaryDataArrayList> function=2",
    ]
    out = _fix_ms_levels(lines, lockmass_func=3)
    assert out == lines


def test_fix_ms_levels_lockmass_boundary():
    lines = [
        '<spectrum id="scan=1" function=1>',
        '<cvParam name="ms level" value="1"/>',
        '<spectrum id="scan=2" function=2>',
        '<cvParam name="ms level" value="1"/>',
    ]
    out = _fix_ms_levels(lines, lockmass_func=2)
    assert out == lines


def test_postprocess_synthetic_fixture(tmp_path):
    p = tmp_path / "test.mzML"
    p.write_text("<binaryDataArrayList> scan=1 & stuff\n")

    qc = postprocess_mzml(p, lockmass_func=3)

    assert qc is None
    assert "<binaryDataArrayList> scan=1" in p.read_text()


def test_postprocess_real_mzml_qc(tmp_path):
    p = tmp_path / "real.mzML"
    p.write_text(
        """
<mzML xmlns="http://psi.hupo.org/ms/mzml">
  <run>
    <spectrum id="scan=1" defaultArrayLength="0">
      <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
      <binaryDataArrayList count="2">
        <binaryDataArray encodedLength="0">
          <cvParam cvRef="MS" accession="MS:1000514" name="m/z array"/>
          <cvParam cvRef="MS" accession="MS:1000521" name="32-bit float"/>
          <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
          <binary></binary>
        </binaryDataArray>
        <binaryDataArray encodedLength="0">
          <cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/>
          <cvParam cvRef="MS" accession="MS:1000521" name="32-bit float"/>
          <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
          <binary></binary>
        </binaryDataArray>
      </binaryDataArrayList>
    </spectrum>
  </run>
</mzML>
"""
    )

    qc = postprocess_mzml(p, lockmass_func=3)

    assert qc is not None
    assert qc.tic == [0.0]
    assert qc.bpc == [0.0]
    assert qc.peak_counts == [0]


def test_read_write_text(tmp_path):
    p = tmp_path / "x.txt"
    _write_text(p, ["a\n", "b\n"])
    assert _read_text(p) == ["a\n", "b\n"]
