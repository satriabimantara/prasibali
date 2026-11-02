"""Build the site CSS with the Tailwind CSS standalone CLI (no Node.js).

    python scripts/tailwind.py build    # minified src/static/css/app.css (committed)
    python scripts/tailwind.py watch    # rebuild while editing templates

The pinned binary is downloaded once into .tools/ (git-ignored).
"""

from __future__ import annotations

import platform
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

TAILWIND_VERSION = "v4.3.3"
REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / ".tools"
INPUT_CSS = REPO_ROOT / "src" / "static" / "src" / "input.css"
OUTPUT_CSS = REPO_ROOT / "src" / "static" / "css" / "app.css"


def asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if system == "windows":
        return f"tailwindcss-windows-{arch}.exe"
    if system == "darwin":
        return f"tailwindcss-macos-{arch}"
    if system == "linux":
        return f"tailwindcss-linux-{arch}"
    raise SystemExit(f"Unsupported platform: {system} {machine}")


def ensure_binary() -> Path:
    name = asset_name()
    binary = TOOLS_DIR / f"{TAILWIND_VERSION}-{name}"
    if binary.is_file():
        return binary
    TOOLS_DIR.mkdir(exist_ok=True)
    url = f"https://github.com/tailwindlabs/tailwindcss/releases/download/{TAILWIND_VERSION}/{name}"
    print(f"Downloading Tailwind CSS {TAILWIND_VERSION} ({name}) ...")
    tmp = binary.with_suffix(binary.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(binary)
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    return binary


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "build"
    if command not in {"build", "watch"}:
        print(__doc__)
        return 2
    args = [str(ensure_binary()), "-i", str(INPUT_CSS), "-o", str(OUTPUT_CSS)]
    args.append("--minify" if command == "build" else "--watch")
    return subprocess.call(args, cwd=REPO_ROOT)  # noqa: S603 - binary path built above


if __name__ == "__main__":
    sys.exit(main(sys.argv))
