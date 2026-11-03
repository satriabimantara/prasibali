"""Pack the pretrained models that PrasiBali v1.0 uses into one archive for a one-time upload to the server.

    python scripts/bundle_models.py                    # dist/prasibali-models-v1.0.tar.gz (~140 MB)
    python scripts/bundle_models.py --with-fasttext    # also FastText 300 (+2.4 GB), if Hugging Face is unreachable

The list comes from the model catalog (apps.analysis.services.model_catalog.required_model_files): every available
classifier pickle plus the label encoder. The archive holds the files at their paths relative to
PRETRAINED_MODELS_DIR and a SHA256SUMS file; on the server it is extracted into ~/prasibali/models and checked with
`sha256sum -c SHA256SUMS` (deploy/server/deploy.sh repeats that check before every deploy).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "dist" / "prasibali-models-v1.0.tar.gz"
FASTTEXT_FILES = (
    "balinese-word-embedding/300_fasttext_model.bin",
    "balinese-word-embedding/300_fasttext_model.bin.wv.vectors_ngrams.npy",
)


def model_files(with_fasttext: bool) -> list[str]:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    import django

    django.setup()
    from apps.analysis.services.model_catalog import required_model_files

    files = required_model_files()
    return files + list(FASTTEXT_FILES) if with_fasttext else files


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models-dir", type=Path, default=Path(os.environ.get("PRETRAINED_MODELS_DIR") or
                                                                REPO_ROOT / "models"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--with-fasttext", action="store_true", help="include FastText 300 (about 2.4 GB)")
    args = parser.parse_args(argv)

    files = model_files(args.with_fasttext)
    missing = [rel for rel in files if not (args.models_dir / rel).is_file()]
    if missing:
        print(f"Missing in {args.models_dir}:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sums = []
    with tarfile.open(args.output, "w:gz") as tar:
        for rel in files:
            path = args.models_dir / rel
            sums.append(f"{sha256(path)}  {rel}")
            tar.add(path, arcname=rel)
            print(f"  {rel}  ({path.stat().st_size / 2**20:.1f} MB)")
        data = ("\n".join(sums) + "\n").encode()
        info = tarfile.TarInfo("SHA256SUMS")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    args.output.with_name("SHA256SUMS").write_bytes(data)

    print(f"Wrote {args.output} ({args.output.stat().st_size / 2**20:.1f} MB, {len(files)} files) "
          f"and {args.output.with_name('SHA256SUMS')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
