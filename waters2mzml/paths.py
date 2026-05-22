from pathlib import Path


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def clean_raw_folder(raw_dir: Path) -> None:
    # Original behavior: delete files in input folder that are NOT .raw
    # fn = glob.glob('*[!".raw"]'); for f in fn: os.remove(f)
    for entry in raw_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() != ".raw":
            entry.unlink()


def list_raw_folders(raw_dir: Path) -> list[Path]:
    # raw = glob.glob('*.raw')
    return [p for p in raw_dir.glob("*.raw") if p.is_dir() or p.suffix == ".raw"]


def find_mzml_files(dir_: Path) -> list[Path]:
    return list(dir_.glob("*.mzML"))


def list_txt_files(dir_: Path) -> list[Path]:
    return list(dir_.glob("*.txt"))
