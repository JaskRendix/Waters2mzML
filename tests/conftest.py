from pathlib import Path

import pytest


def write(p: Path, text: str):
    p.write_text(text, encoding="utf-8")


def make_raw_folder(base: Path, name: str) -> Path:
    raw = base / f"{name}.raw"
    raw.mkdir()
    return raw


def make_func_files(raw: Path, funcs: list[int]):
    for f in funcs:
        write(raw / f"FUNC{f:03d}_header.txt", f"HEADER for FUNC{f:03d}")
        write(raw / f"FUNC{f:03d}_data.txt", f"DATA for FUNC{f:03d}")


def mzml_skeleton(scans: list[tuple[int, int, int]]):
    lines = [f'<spectrumList count="{len(scans)}">']
    for scan_id, func, ms in scans:
        msline = "" if ms is None else f'<cvParam name="ms level" value="{ms}"/>'
        lines.append(
            f'  <spectrum id="scan={scan_id}" function={func}>\n'
            f"    {msline}\n"
            f"  </spectrum>"
        )
    lines.append("</spectrumList>")
    return "\n".join(lines)


@pytest.fixture
def make_fixture():

    def _factory(base: Path, name: str):
        # DO NOT overwrite base
        raw = make_raw_folder(base, name)
        expected = base / f"{name}.expected.mzML"

        if name == "sample1":
            write(raw / "_extern.inf", "Function Parameters - Function 1\n")
            make_func_files(raw, [1])
            write(expected, mzml_skeleton([(1, 1, 1)]))

        elif name == "sample2":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n",
            )
            make_func_files(raw, [1, 2])
            write(expected, mzml_skeleton([(1, 1, 1), (2, 2, 2)]))

        elif name == "sample3":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n",
            )
            make_func_files(raw, [1, 2])
            write(expected, mzml_skeleton([(1, 1, 1), (2, 2, 2)]))

        elif name == "sample4":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n"
                "Function Parameters - Function 3  REFERENCE\n",
            )
            make_func_files(raw, [1, 2, 3, 4])
            write(expected, mzml_skeleton([(1, 1, 1), (2, 2, 2)]))

        elif name == "sample5":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n"
                "Function Parameters - Function 3\n"
                "Function Parameters - Function 4\n",
            )
            make_func_files(raw, [1, 2, 3, 4, 5])
            write(expected, mzml_skeleton([(1, 1, 1), (2, 2, 2)]))

        elif name == "sample6":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n"
                "Function Parameters - Function 3\n"
                "Function Parameters - Function 4\n"
                "Function Parameters - Function 5\n"
                "Function Parameters - Function 6\n"
                "Function Parameters - Function 7  REFERENCE\n",
            )
            make_func_files(raw, [1, 2, 3, 4, 5, 6, 7, 8])
            write(
                expected,
                mzml_skeleton(
                    [
                        (1, 1, 1),
                        (2, 2, 2),
                        (3, 3, 2),
                        (4, 4, 2),
                        (5, 5, 2),
                        (6, 6, 2),
                    ]
                ),
            )

        elif name == "sample7":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n",
            )
            make_func_files(raw, [1, 2])
            write(
                expected,
                mzml_skeleton(
                    [
                        (1, 1, 1),
                        (1, 2, 2),
                        (2, 1, 1),
                        (2, 2, 2),
                    ]
                ),
            )

        elif name == "sample8":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n",
            )
            make_func_files(raw, [1, 2])
            write(
                expected,
                '<spectrumList count="2">\n'
                '  <spectrum id="scan=1" function=1>\n'
                '    <cvParam name="profile spectrum" value="true"/>\n'
                "  </spectrum>\n"
                '  <spectrum id="scan=2" function=2>\n'
                '    <cvParam name="centroid spectrum" value="true"/>\n'
                "  </spectrum>\n"
                "</spectrumList>",
            )

        elif name == "sample9":
            write(
                raw / "_extern.inf",
                "Function Parameters - Function 1\n"
                "Function Parameters - Function 2\n",
            )
            make_func_files(raw, [1, 2])
            write(
                expected,
                '<spectrumList count="2">\n'
                '  <spectrum id="scan=1" function=1>\n'
                "  </spectrum>\n"
                '  <spectrum id="scan=2" function=2>\n'
                "  </spectrum>\n"
                "</spectrumList>",
            )

        elif name == "sample10":
            write(
                raw / "_extern.inf",
                "THIS FILE IS CORRUPTED\nNO FUNCTION HEADERS\n",
            )
            make_func_files(raw, [1, 2, 3])
            write(
                expected,
                mzml_skeleton(
                    [
                        (1, 1, 1),
                        (2, 2, 1),
                    ]
                ),
            )

        else:
            raise ValueError(f"Unknown fixture: {name}")

        return raw, expected

    return _factory
