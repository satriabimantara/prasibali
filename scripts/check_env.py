"""
Cek kesiapan environment Python untuk PrasiBali.ai.

Jalankan dari akar repo, di dalam environment yang sudah aktif:
    python scripts/check_env.py
    python scripts/check_env.py --models-dir "<path ke folder pretrained-models>"
    python scripts/check_env.py --no-smoke      # tanpa unduh embedding dan tanpa prediksi (mis. tanpa internet)

Folder model dibaca dari --models-dir, lalu PRETRAINED_MODELS_DIR (environment atau .env di akar
repo), sama seperti aplikasi web. FastText untuk TF5 dibaca dari TF5_HF_REPO_ID dan
TF5_FASTTEXT_FILENAME (bawaan: satriabimantara/balinese_pretrained_wordembedding, 50_fasttext_model.bin).

Skrip ini memastikan:
  1. Versi Python dan versi library penting sesuai requirements.txt
  2. Model SatuaNER bawaan balinese-nlp bisa dimuat dan mengenali tokoh
  3. Alias clustering berjalan
  4. FastText bahasa Bali (fitur TF5) bisa diunduh/dimuat dari Hugging Face lewat BaliFastText
  5. Pickle classifier peran bisa dimuat dan dijalankan end-to-end pada teks contoh:
     model default aplikasi (SVM + TF5, varian M2) dan pembandingnya, termasuk kecocokan
     dimensi embedding dengan n_features_in_ model
"""
from __future__ import annotations

import argparse
import sys
import time
from importlib import metadata
from pathlib import Path

import prasibali_models as pm

REPO_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_SATUA = (
    "I Lutung kaliwat demen kenehne ngamah biu nasak. "
    "Sedeng iteha I Lutung ngamah biu lantas katumbak baan I Kaki Perodong. "
    "Sang Lutung maglebug ulung ka tanahe. "
    "Ni Bawang nongos di umah dadongne. Ni Kesuna ngelah pikeneh ane jele."
)
# Konteks pendek untuk uji ekstraksi fitur dan prediksi (sudah huruf kecil, tanpa tanda baca).
SAMPLE_CONTEXTS = [
    "ni bawang anak luh jemet tur sayang teken reramane",
    "ni kesuna ngelah pikeneh jele demen ngelengin timpal",
]

# Pin persis blok "AI / NLP" di requirements.txt.
EXPECTED = {
    "balinese-nlp": "2.4.2",
    "scikit-learn": "1.2.1",
    "sklearn-crfsuite": "0.3.6",
    "python-crfsuite": "0.9.10",
    "pandas": "1.5.3",
    "numpy": "1.24.4",
    "scipy": "1.10.1",
    "gensim": "4.3.3",
    "hmmlearn": "0.3.0",
    "openpyxl": "3.1.5",
}

# (label, varian, kode fitur, algoritma). Baris pertama = default aplikasi (wajib lulus).
CLASSIFIER_CHECKS = [
    ("default aplikasi", pm.DEFAULT_VARIANT, pm.DEFAULT_FEATURE, pm.DEFAULT_CLASSIFIER),
    ("pembanding M1", "m1", "TF5", "Support Vector Machine"),
    ("terverifikasi 2 Nov", "m1", "TF4", "Support Vector Machine"),
]

failures: list[str] = []


def embedding_loader():
    """Pemuat FastText untuk TF5; hasilnya di-cache oleh pm.load_fasttext (sekali per proses)."""
    return pm.load_fasttext(*pm.embedding_config(REPO_ROOT))


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def fail(msg: str) -> None:
    print(f"  [GAGAL] {msg}")
    failures.append(msg)


def info(msg: str) -> None:
    print(f"  [info] {msg}")


def check_python() -> None:
    print("1. Versi Python")
    v = sys.version_info
    if (v.major, v.minor) == (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor}.{v.micro} — harus 3.11")


def check_versions() -> None:
    print("2. Versi library")
    for pkg, want in EXPECTED.items():
        try:
            got = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            fail(f"{pkg} belum terpasang")
            continue
        (ok if got == want else fail)(f"{pkg} {got} (seharusnya {want})")
    for pkg in ["torch", "transformers", "huggingface-hub", "Django", "django-allauth"]:
        try:
            info(f"{pkg} {metadata.version(pkg)}")
        except metadata.PackageNotFoundError:
            fail(f"{pkg} belum terpasang")


def preprocess(text: str) -> str:
    """Urutan praproses yang sama dengan web lama (views/features.py)."""
    from balinese_nlp.textpreprocessor import TextPreprocessor

    tp = TextPreprocessor()
    text = tp.convert_ascii_sentence(text)
    text = tp.normalize_words(text)
    text = tp.remove_tab_characters(text)
    text = tp.remove_special_punctuation(text)
    text = tp.remove_punctuation(text)
    text = tp.remove_exclamation_words(text)
    text = tp.add_enter_after_period_punctuation(text)
    text = tp.remove_leading_trailing_whitespace(text)
    return tp.remove_whitespace_multiple(text)


def check_pipeline() -> None:
    print("3. Model SatuaNER + alias clustering")
    try:
        from balinese_nlp.narratives.aliasclustering.rule_based import (
            AliasClusteringRuleBased,
        )
        from balinese_nlp.narratives.characterner import BaseModel
        from balinese_nlp.narratives.utils import load_pretrained_character_ner_model
    except Exception as exc:  # noqa: BLE001
        fail(f"import balinese_nlp gagal: {exc!r}")
        return

    t0 = time.perf_counter()
    model = load_pretrained_character_ner_model("satuaner")
    if isinstance(model, dict):  # format pickle lama: {'optimal_best_all_train_model': ...}
        model = model.get("optimal_best_all_train_model", model)
    ok(f"satuaner.pkl dimuat ({type(model).__name__}, {time.perf_counter() - t0:.1f} dtk)")

    text = preprocess(SAMPLE_SATUA)
    t0 = time.perf_counter()
    chars = sorted(set(BaseModel.identify_characters(preprocessed_story=text, pretrained_model=model)))
    if chars:
        ok(f"tokoh terdeteksi ({time.perf_counter() - t0:.1f} dtk): {chars}")
    else:
        fail("tidak ada tokoh terdeteksi pada teks contoh")
        return

    clusterer = AliasClusteringRuleBased(pairwise_distance="sorensen-dice", avg_threshold_similarity=0.85)
    groups = clusterer.fit(chars).cluster()
    ok(f"alias clustering: {groups}")


def check_one_classifier(models_dir: Path, encoder, label: str, variant: str, feature: str,
                         classifier: str, smoke: bool, required: bool) -> None:
    title = f"{variant.upper()} {feature} {classifier} ({label})"
    report = fail if required else (lambda msg: print(f"  [peringatan] {msg}"))
    try:
        codes = pm.parse_feature_codes(feature)
        path = pm.bundle_path(models_dir, variant, codes, classifier)
        started = time.perf_counter()
        bundle = pm.unpickle(path)
        entry = pm.extract_model_entry(bundle, classifier)
        selected = pm.select_extractors(entry, codes)
        size_mb = path.stat().st_size / 1_048_576
        ok(f"{title}: {path.name} dimuat ({size_mb:.1f} MB, sha256 {pm.fingerprint(path)}, "
           f"{time.perf_counter() - started:.1f} dtk), estimator {type(entry['estimator']).__name__}")
        for code, extractor in selected:
            info(f"ekstraktor {code}: {pm.describe(extractor)} | {pm.extractor_style(extractor)}")
        if not smoke:
            return
        features, _ = pm.featurize(
            selected, SAMPLE_CONTEXTS, log=lambda msg: print(f"  [info]{msg[1:]}"), embedding_loader=embedding_loader
        )
        expected = getattr(entry["estimator"], "n_features_in_", None)
        if codes == ["TF5"] and expected is not None and features.shape[1] != expected:
            raise pm.ModelError(
                f"dimensi embedding {features.shape[1]} tidak sama dengan n_features_in_ model ({expected}). "
                f"File FastText kemungkinan bukan yang dipakai saat pelatihan; atur {pm.TF5_FILENAME_ENV_VAR} di .env "
                f"(pilihan lokal: {pm.local_embedding_files(REPO_ROOT)})"
            )
        pm.check_feature_count(entry["estimator"], features)
        labels = encoder.inverse_transform(entry["estimator"].predict(features))
        ok(f"{title}: prediksi teks contoh berhasil -> {list(map(str, labels))}")
    except pm.ModelError as exc:
        report(f"{title}: {exc}")
    except Exception as exc:  # noqa: BLE001
        report(f"{title}: {exc!r}")


def check_embedding(smoke: bool) -> None:
    print("4. FastText bahasa Bali untuk fitur TF5 (Hugging Face)")
    repo_id, filename = pm.embedding_config(REPO_ROOT)
    info(f"sumber {repo_id}, file {filename} (atur lewat {pm.TF5_FILENAME_ENV_VAR} / {pm.TF5_REPO_ENV_VAR})")
    local = pm.local_embedding_files(REPO_ROOT)
    if local:
        info(f"file embedding lokal di {pm.LOCAL_EMBEDDING_DIR}/: {local}")
    if not smoke:
        print("  [lewati] --no-smoke: embedding tidak diunduh/dimuat")
        return
    try:
        started = time.perf_counter()
        model = pm.load_fasttext(repo_id, filename)
    except pm.ModelError as exc:
        fail(str(exc))
        return
    vocab = len(getattr(model.wv, "key_to_index", {}) or {})
    ok(f"{type(model).__name__} dimuat ({time.perf_counter() - started:.1f} dtk): vector_size {model.vector_size}, "
       f"kosakata {vocab}")
    word = "lutung"
    status = "ada di kosakata" if word in getattr(model.wv, "key_to_index", {}) else "di luar kosakata (pakai n-gram)"
    info(f"contoh kata '{word}': {status}; tesis memakai 300 dimensi untuk TF5")


def check_classifiers(models_arg: str | None, smoke: bool) -> None:
    print("5. Classifier peran tokoh (pickle eksperimen tesis)")
    models_dir, source = pm.resolve_models_dir(REPO_ROOT, models_arg)
    if not models_dir.is_dir():
        fail(f"folder model tidak ditemukan ({source}): {models_dir}. Isi {pm.MODELS_ENV_VAR} di .env")
        return
    ok(f"folder model ({source}): {models_dir}")
    try:
        encoder_path, encoder = pm.load_encoder(models_dir)
    except pm.ModelError as exc:
        fail(str(exc))
        return
    ok(f"label encoder {encoder_path.name}: kelas {[str(c) for c in encoder.classes_]}")
    for index, (label, variant, feature, classifier) in enumerate(CLASSIFIER_CHECKS):
        check_one_classifier(models_dir, encoder, label, variant, feature, classifier, smoke, required=index == 0)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", help=f"folder pretrained-models; bila kosong dibaca dari {pm.MODELS_ENV_VAR}")
    parser.add_argument("--no-smoke", action="store_true",
                        help="hanya muat pickle, tanpa unduh embedding, ekstraksi fitur, dan prediksi")
    args = parser.parse_args()

    check_python()
    check_versions()
    check_pipeline()
    check_embedding(smoke=not args.no_smoke)
    check_classifiers(args.models_dir, smoke=not args.no_smoke)

    print()
    if failures:
        print(f"SELESAI dengan {len(failures)} masalah:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SEMUA CEK LULUS — environment siap untuk PrasiBali.ai")
    return 0


if __name__ == "__main__":
    sys.exit(main())
