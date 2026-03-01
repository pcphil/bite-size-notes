"""Build a Windows exe using PyInstaller and package as a portable zip."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Build Bite-Size Notes exe")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with console=True so errors print to a visible terminal",
    )
    args = parser.parse_args()

    spec_path = "packaging/bite_size_notes.spec"

    # If --debug, create a temp spec in the same directory with console=True
    # (must stay in packaging/ so SPECPATH-relative paths still resolve)
    if args.debug:
        spec_text = Path(spec_path).read_text(encoding="utf-8")
        spec_text = spec_text.replace("console=False", "console=True")
        debug_spec = Path("packaging/bite_size_notes_debug.spec")
        debug_spec.write_text(spec_text, encoding="utf-8")
        spec_path = str(debug_spec)
        print("DEBUG BUILD: using console=True")

    # Step 1: Run PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        spec_path,
        "--noconfirm",
    ]
    print(f"Running: {' '.join(cmd)}")
    ret = subprocess.call(cmd)

    # Clean up debug spec if we created one
    if args.debug:
        Path(spec_path).unlink(missing_ok=True)

    if ret != 0:
        raise SystemExit(ret)

    # Step 2: Create portable zip from the dist folder
    dist_dir = Path("dist/bite_size_notes")
    if not dist_dir.is_dir():
        print(f"ERROR: {dist_dir} not found after build.", file=sys.stderr)
        raise SystemExit(1)

    zip_name = "BiteSizeNotes_v0.1.0"
    zip_path = shutil.make_archive(f"dist/{zip_name}", "zip", "dist", "bite_size_notes")
    print(f"Created: {zip_path}")


if __name__ == "__main__":
    main()
