from waters2mzml.mzml_postprocess import _fix_ms_levels, _renumber_scans


def test_renumber_scans_simple():
    """
    Synthetic mzML snippet with 2 spectra.
    Original script states:
    'every spectrum will be referenced 3 times'
    """
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
    """
    Synthetic snippet where function=2 incorrectly has MS level 1.
    Original script says:
    'we check if the value of this first function 2 scan equals 1'
    """
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
    """
    If function=2 already has MS level 2, nothing should change.
    """
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
