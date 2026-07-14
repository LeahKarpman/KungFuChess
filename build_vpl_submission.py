"""Build a deterministic VPL submission archive."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "kungfu_chess"
OUTPUT = ROOT / "KungFuChess-VPL-submission.zip"


def should_include(path: Path) -> bool:
    """Return whether a Python source file belongs in the VPL archive."""
    excluded_directories = {"tests", "__pycache__", ".pytest_cache"}
    return (
        path.suffix == ".py"
        and not excluded_directories.intersection(path.parts)
    )


def main() -> None:
    """Create a VPL archive with app.py as its first entry."""
    if OUTPUT.exists():
        OUTPUT.unlink()

    source_files = sorted(
        path for path in PACKAGE.rglob("*.py") if should_include(path)
    )

    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(ROOT / "app.py", "app.py")

        for path in source_files:
            archive.write(path, path.relative_to(ROOT).as_posix())

    print(f"Created {OUTPUT.name}")


if __name__ == "__main__":
    main()