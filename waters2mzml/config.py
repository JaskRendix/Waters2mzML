from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversionConfig:
    centroid: bool
    ms_level_filter: str = "1-2"
    compression: str = "--zlib --32"
    use_docker: bool = False
    docker_image: str = "proteowizard/msconvert:latest"

    def build_msconvert_args(self) -> str:
        # Mirrors original config strings
        # Original:
        # ' --filter "peakPicking cwt msLevel=1-" --zlib --32 --filter "msLevel 1-2" --filter "titleMaker <RunId>.<ScanNumber>.<ScanNumber>.<ChargeState> File:"<SourcePath>".NativeID:"<Id>""'
        base = f'{self.compression} --filter "msLevel {self.ms_level_filter}"'
        title = (
            ' --filter "titleMaker '
            "<RunId>.<ScanNumber>.<ScanNumber>.<ChargeState> "
            'File:\\"<SourcePath>\\".NativeID:\\"<Id>\\""'
        )
        if self.centroid:
            peak = ' --filter "peakPicking cwt msLevel=1-"'
        else:
            peak = ""
        return f"{peak} {base}{title}"


@dataclass
class Paths:
    base_dir: Path
    raw_dir: Path
    mzml_dir: Path
    msconvert_path: Path


def default_paths(base_dir: Path | None = None) -> Paths:
    base = base_dir or Path.cwd()
    raw_dir = base / "raw_files"
    mzml_dir = base / "mzML_files"
    msconvert_path = (
        base / "pwizLibraries-and-Installation" / "pwiz_Leave-Alone" / "msconvert.exe"
    )
    return Paths(base, raw_dir, mzml_dir, msconvert_path)
