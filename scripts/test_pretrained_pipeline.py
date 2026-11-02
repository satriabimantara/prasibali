"""
Uji manual pipeline PrasiBali.ai pada satu teks satua Bali.

Tugas yang diuji:
  (i)   Identifikasi tokoh        -> SatuaNER, bawaan paket balinese-nlp
  (ii)  Alias clustering          -> rule-based, bawaan paket balinese-nlp
  (iii) Klasifikasi peran tokoh   -> pickle eksperimen tesis di folder pretrained-models
                                     (PRETRAINED_MODELS_DIR), sebab paket 2.4.2 belum memuat model supervised

Model bawaan (iii) mengikuti buku tesis: SVM + TF5 (rata-rata word embedding FastText), varian M2
(Tabel 4.57, 4.59, 4.60). Model lain dipilih dengan --variant, --feature, dan --classifier-name.

Cara menjalankan (environment Python 3.11 sudah aktif):
  python scripts/test_pretrained_pipeline.py
  python scripts/test_pretrained_pipeline.py --inspect
  python scripts/test_pretrained_pipeline.py --dump-api
  python scripts/test_pretrained_pipeline.py --variant m1 --feature TF4
  python scripts/test_pretrained_pipeline.py --variant m1 --feature TF4_TF5 --classifier-name "Random Forest"
  python scripts/test_pretrained_pipeline.py --input "<file satua .txt>" --output hasil_uji.json

Lokasi folder model: --models-dir, lalu PRETRAINED_MODELS_DIR (environment atau .env di akar repo),
lalu _reference/old_web/website/balinarrativenlp/pretrained-models.

FastText untuk TF5 dimuat lewat balinese_nlp.embeddings.gensims.BaliFastText dari Hugging Face:
--tf5-repo/--tf5-file, lalu TF5_HF_REPO_ID/TF5_FASTTEXT_FILENAME, lalu nilai bawaan
(satriabimantara/balinese_pretrained_wordembedding, 50_fasttext_model.bin). Unduhan pertama butuh internet.

Keamanan: pickle bisa menjalankan kode saat dimuat. Muat hanya file model milik sendiri.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
import time
import traceback
from importlib import metadata
from pathlib import Path

import prasibali_models as pm

REFERENCE_DIR = "_reference"
DEFAULT_ROOT = Path(__file__).resolve().parent.parent  # akar repo (skrip ada di scripts/)
SAMPLE_REL = Path(REFERENCE_DIR) / "sample_satua" / "raw text" / "I Siput lawan I Kancil.txt"
API_DUMP_NAME = "balinese_nlp_api_dump.txt"
SENTENCE_SEP = "\\n"  # literal dua karakter: backslash + n, keluaran TextPreprocessor
MIN_SENTENCES = 11  # batasan masukan pada tesis (Bab 1.4)
LOW_CONTEXT_WORDS = 20  # di bawah ini, hasil klasifikasi diberi peringatan "konteks sedikit"
EXPECTED_VERSIONS = {"balinese-nlp": "2.4.2", "scikit-learn": "1.2.1", "sklearn-crfsuite": "0.3.6", "pandas": "1.5.3"}

# Modul yang relevan untuk fitur TF5 (word embedding) dan efek samping saved_file.
API_MODULES = [
    "balinese_nlp.embeddings",
    "balinese_nlp.embeddings.BasePretrained",
    "balinese_nlp.embeddings.gensims",
    "balinese_nlp.embeddings.gensims.BaliFastText",
    "balinese_nlp.feature_extractor.narratives.characterclassification",
    "balinese_nlp.feature_extractor.narratives.characterclassification.BaseModelFeatureExtraction",
    "balinese_nlp.feature_extractor.narratives.characterclassification.FeatureExtraction",
    "balinese_nlp.feature_extractor.narratives.characterclassification.WordEmbeddingFeatureExtraction",
    "balinese_nlp.feature_extractor.narratives.characterclassification.LexiconFeatureExtraction",
    "balinese_nlp.feature_extractor.narratives.characterclassification.POSTagFeatureExtraction",
    "balinese_nlp.quoteattribution.rule_based",
    "balinese_nlp.quoteattribution.rule_based.RuleBasedSentenceGrouping",
]

StepError = pm.ModelError


def heading(text: str) -> None:
    print(f"\n{'=' * 72}\n{text}\n{'=' * 72}")


def warn(text: str) -> None:
    print(f"  [PERINGATAN] {text}")


def find_root(explicit: str | None) -> Path:
    """Cari akar proyek: --root, lalu ke atas dari skrip dan cwd, lalu akar repo."""
    if explicit:
        return Path(explicit)
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        for folder in (start, *start.parents):
            if (folder / REFERENCE_DIR).is_dir():
                return folder
    return DEFAULT_ROOT


def read_text(path: Path) -> str:
    if not path.is_file():
        raise StepError(f"File teks tidak ditemukan: {path}")
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise StepError(f"Encoding file tidak dikenali: {path}")


def load_class(module_path: str, name: str):
    """Ambil kelas, baik diekspor dari __init__ maupun berada di modul bernama sama."""
    module = importlib.import_module(module_path)
    attr = getattr(module, name, None)
    if inspect.isclass(attr):
        return attr
    if not inspect.ismodule(attr):
        try:
            attr = importlib.import_module(f"{module_path}.{name}")
        except ModuleNotFoundError:
            attr = module
    for class_name, cls in inspect.getmembers(attr, inspect.isclass):
        if name in class_name or class_name in name:
            return cls
    raise StepError(f"Kelas {name} tidak ditemukan di {module_path}")


def report_environment() -> None:
    heading("0. ENVIRONMENT")
    print(f"  Python {sys.version.split()[0]}")
    if sys.version_info[:2] != (3, 11):
        warn("Python seharusnya 3.11")
    for package, expected in EXPECTED_VERSIONS.items():
        try:
            found = metadata.version(package)
        except metadata.PackageNotFoundError:
            raise StepError(f"{package} belum terpasang") from None
        print(f"  {package:<18} {found}")
        if found != expected:
            warn(f"{package} seharusnya {expected}; pickle lama bisa gagal dimuat atau berperilaku beda")


def report_supervised_in_package() -> bool:
    """Menjawab: apakah paket yang terpasang sudah memuat model klasifikasi supervised?"""
    import balinese_nlp

    folder = Path(balinese_nlp.__file__).parent / "narratives" / "characterclassification" / "supervised"
    files = sorted(p.name for p in folder.glob("*") if p.is_file() and p.name != "__init__.py") if folder.is_dir() else []
    state = ", ".join(files) if files else "kosong atau tidak ada"
    print(f"  Isi characterclassification/supervised di paket: {state}")
    return bool(files)


def preprocess_story(raw: str):
    """Sembilan langkah praproses, urutan sama dengan web lama."""
    from balinese_nlp.textpreprocessor import TextPreprocessor

    tp = TextPreprocessor()
    text = tp.convert_ascii_sentence(raw)
    text = tp.normalize_words(text)
    text = tp.remove_tab_characters(text)
    text = tp.remove_special_punctuation(text)
    text = tp.remove_punctuation(text)
    text = tp.remove_exclamation_words(text)
    text = tp.add_enter_after_period_punctuation(text)
    text = tp.remove_leading_trailing_whitespace(text)
    text = tp.remove_whitespace_multiple(text)

    # identify_characters membuang elemen terakhir hasil split, jadi teks harus berakhir dengan pemisah.
    if not text.rstrip().endswith(SENTENCE_SEP):
        warn("Teks tidak berakhir dengan titik; pemisah ditambahkan agar kalimat terakhir tidak terbuang")
        text = f"{text.rstrip()}{SENTENCE_SEP}"
    sentences = [s.strip() for s in text.split(SENTENCE_SEP) if s.strip()]
    if not sentences:
        raise StepError("Praproses menghasilkan nol kalimat. Pastikan teks memuat tanda titik.")
    return tp, text, sentences


def identify_characters(ner_name: str, text: str, sentences: list[str]):
    from balinese_nlp.narratives.characterner import BaseModel
    from balinese_nlp.narratives.utils import load_pretrained_character_ner_model

    started = time.perf_counter()
    model = load_pretrained_character_ner_model(ner_name)
    if isinstance(model, dict):  # format pickle lama
        model = model.get("optimal_best_all_train_model", model)
    print(f"  Model {ner_name}: {type(model).__name__}, dimuat {time.perf_counter() - started:.1f} dtk")

    started = time.perf_counter()
    characters = sorted(set(BaseModel.identify_characters(preprocessed_story=text, pretrained_model=model)))
    print(f"  Inferensi {time.perf_counter() - started:.1f} dtk, {len(characters)} sebutan tokoh unik:")
    if not characters:
        raise StepError("Tidak ada tokoh yang terdeteksi")
    for name in characters:
        hits = sum(name.lower() in sentence.lower() for sentence in sentences)
        print(f"    - {name}  (muncul di {hits} kalimat)")
    return model, characters


def show_bio_example(model, sentences: list[str], characters: list[str]) -> None:
    """Contoh label BIO satu kalimat. Hanya informasi, kegagalannya tidak menggugurkan uji."""
    sentence = next((s for s in sentences if any(c.lower() in s.lower() for c in characters)), sentences[0])
    try:
        y_pred, tagged = model.predict_sentence(sentence)
        print(f"\n  Contoh BIO\n    Kalimat : {sentence}\n    Label   : {y_pred}\n    Token   : {tagged}")
    except Exception as exc:  # noqa: BLE001
        warn(f"predict_sentence tidak bisa ditampilkan: {exc!r}")


def cluster_aliases(characters: list[str], similarity: str, threshold: float) -> dict:
    cls = load_class("balinese_nlp.narratives.aliasclustering.rule_based", "AliasClusteringRuleBased")
    groups = cls(pairwise_distance=similarity, avg_threshold_similarity=threshold).fit(characters).cluster()
    print(f"  Metode {similarity}, ambang {threshold}: {len(groups)} kelompok tokoh")
    for group, aliases in groups.items():
        print(f"    {group}: {aliases}")
    return groups


def group_sentences(sentences: list[str], groups: dict):
    cls = load_class("balinese_nlp.quoteattribution.rule_based", "RuleBasedSentenceGrouping")
    df = cls(add_characterization_column=False).fit(sentences=sentences, characters_alias_clustering=groups).predict()
    print(f"  Kolom keluaran grouping: {list(df.columns)}")
    if "GroupedSentences" not in df.columns:
        raise StepError("Kolom GroupedSentences tidak ada pada keluaran RuleBasedSentenceGrouping")
    return df.reset_index(drop=True)


def stop_word_remover(tp):
    """Pakai metode paket. Bila namanya beda, pakai daftar stop word bawaan paket dan beri peringatan."""
    for name in ("remove_stop_words", "remove_stopwords", "remove_stop_word"):
        method = getattr(tp, name, None)
        if callable(method):
            return method
    import balinese_nlp

    path = Path(balinese_nlp.__file__).parent / "textpreprocessor" / "data" / "stopwords" / "data.txt"
    if not path.is_file():
        raise StepError("Metode penghapus stop word tidak ditemukan; hasil klasifikasi tidak akan valid")
    stop_words = set(path.read_text(encoding="utf-8").split())
    warn("Metode stop word paket tidak ditemukan; memakai data.txt paket. Cocokkan dengan web lama.")
    return lambda text: " ".join(word for word in text.split() if word not in stop_words)


LEGACY_PREPROCESS = False  # --legacy-preprocess: tiru web lama (lihat docstring preprocess_context)


def preprocess_context(value, tp) -> str:
    """Case folding -> buang stop word -> buang titik -> '-' jadi spasi -> strip.

    Web lama (views/features.py) mengisi kolom konteks dengan case_folding(GroupedSentences), lalu menimpanya
    dengan remove_stop_words(GroupedSentences): case folding praktis tidak berlaku. Dengan --legacy-preprocess
    langkah itu dilewati agar hasilnya bisa dibandingkan dengan web lama. Mana yang sesuai dengan data pelatihan
    belum dipastikan; keduanya dicoba lalu bandingkan labelnya.
    """
    text = " ".join(map(str, value)) if isinstance(value, (list, tuple)) else str(value)
    text = text.replace(SENTENCE_SEP, " ")
    if LEGACY_PREPROCESS:
        return stop_word_remover(tp)(text).replace(".", " ").replace("-", " ").strip()
    case_fold = next((getattr(tp, n) for n in ("case_folding", "casefolding", "case_fold") if callable(getattr(tp, n, None))), str.lower)
    text = stop_word_remover(tp)(case_fold(text))
    return text.replace(".", " ").replace("-", " ").strip()


def load_classifier(models_dir: Path, variant: str, codes: list[str], classifier_name: str,
                    encoder_path: str | None, bundle_override: Path | None = None):
    if bundle_override is not None:
        if not bundle_override.is_file():
            raise StepError(f"File classifier tidak ditemukan: {bundle_override}")
        bundle_path = bundle_override
    else:
        bundle_path = pm.bundle_path(models_dir, variant, codes, classifier_name)
    bundle = pm.unpickle(bundle_path)
    print(f"  Bundle  : {bundle_path.name} (sha256 {pm.fingerprint(bundle_path)})")
    print(f"  Lokasi  : {bundle_path}")
    print(f"  Kunci   : {list(bundle) if isinstance(bundle, dict) else pm.describe(bundle)}")
    entry = pm.extract_model_entry(bundle, classifier_name)
    selected = pm.select_extractors(entry, codes)
    encoder_file, encoder = pm.load_encoder(models_dir, encoder_path)
    print(f"  Encoder : {encoder_file.name}, kelas {[str(c) for c in encoder.classes_]}")
    print(f"  Model   : {type(entry['estimator']).__name__} ({classifier_name}, varian {variant.upper()})")
    expected = getattr(entry["estimator"], "n_features_in_", None)
    for code, extractor in selected:
        print(f"  Fitur   : {code} -> {pm.describe(extractor)}")
    if expected is not None:
        print(f"  Model mengharapkan {expected} fitur (n_features_in_)")
    return entry["estimator"], selected, encoder, entry.get("feature_scaler")


def find_group_labels(df, groups: dict) -> list[str]:
    """Baris dipetakan lewat kolom nama kelompok; bila tidak ada, lewat urutan kelompok."""
    keys = list(groups)
    for column in df.columns:
        if column != "GroupedSentences" and df[column].astype(str).isin(keys).all():
            return df[column].astype(str).tolist()
    if len(df) != len(keys):
        warn("Jumlah baris grouping berbeda dari jumlah kelompok; nama kelompok memakai nomor baris")
        return [f"Baris-{i}" for i in range(len(df))]
    warn("Kolom nama kelompok tidak dikenali; pemetaan memakai urutan. Cek kolom keluaran di atas.")
    return keys


def classify_roles(df, groups: dict, tp, estimator, selected, encoder, embedding_loader=None,
                   lexicon_loader=None, scaler=None) -> list[dict]:
    contexts = [preprocess_context(value, tp) for value in df["GroupedSentences"]]
    features, known_terms = pm.featurize(
        selected, contexts, embedding_loader=embedding_loader, lexicon_loader=lexicon_loader, scaler=scaler
    )
    pm.check_feature_count(estimator, features)
    labels = encoder.inverse_transform(estimator.predict(features))
    scores, probabilities = pm.score_and_probability(estimator, features)
    known_terms = known_terms or [None] * len(contexts)

    results = []
    for i, group in enumerate(find_group_labels(df, groups)):
        results.append({
            "group": group,
            "aliases": list(groups.get(group, [])),
            "role": str(labels[i]),
            "decision_score": scores[i],
            "probability": probabilities[i],
            "context_words": len(contexts[i].split()),
            "known_tfidf_terms": known_terms[i],
        })
    return results


def print_roles(results: list[dict]) -> None:
    def fmt(value, spec: str) -> str:
        return "-" if value is None else format(value, spec)

    print(f"\n  {'Kelompok':<12}{'Peran':<13}{'Skor':>9}{'Prob.':>8}{'Kata':>7}{'TF-IDF':>8}  Alias")
    for row in results:
        print(f"  {row['group']:<12}{row['role']:<13}{fmt(row['decision_score'], '.3f'):>9}"
              f"{fmt(row['probability'], '.3f'):>8}{row['context_words']:>7}{fmt(row['known_tfidf_terms'], 'd'):>8}  {row['aliases']}")
    print("\n  Skor  = decision_function (untuk SVM: jarak ke hyperplane, bukan probabilitas).")
    print("  Prob. = probabilitas kelas terpilih, hanya untuk model yang mendukung predict_proba.")
    print("  TF-IDF = jumlah term konteks yang dikenal vektorizer TF-IDF (hanya untuk fitur TF4).")
    for row in results:
        if row["known_tfidf_terms"] == 0:
            warn(f"{row['group']}: tidak ada term TF-IDF yang dikenal, labelnya tidak bermakna")
        elif row["context_words"] < LOW_CONTEXT_WORDS:
            warn(f"{row['group']}: konteks sedikit ({row['context_words']} kata), hasil kurang andal")


def inspect_models(models_dir: Path, max_mb: int) -> None:
    heading(f"INSPEKSI {models_dir}")
    if not models_dir.is_dir():
        raise StepError(f"Folder model tidak ditemukan: {models_dir}")

    def summary(obj, depth: int = 0) -> None:
        pad = "    " * (depth + 2)
        if isinstance(obj, dict) and depth < 4:
            for key, value in list(obj.items())[:12]:
                extra = ""
                if not isinstance(value, dict):
                    extra = f"  [{pm.extractor_style(value)}]"
                    if hasattr(value, "n_features_in_"):
                        extra += f" [n_features_in_={value.n_features_in_}]"
                        hint = pm.infer_lexicon_codes(value.n_features_in_) if in_lexicon[0] else None
                        if hint:
                            extra += f" [cocok fitur leksikon {hint}]"
                print(f"{pad}{key!r}: {pm.brief(value)}{extra}")
                summary(value, depth + 1)
        elif pm.is_placeholder(obj) and depth < 5:
            # objek dari modul lama (mis. FeatureExtraction): tampilkan state-nya
            print(f"{pad}[placeholder {type(obj).__module__}.{type(obj).__name__}] atribut:")
            summary(vars(obj), depth)

    # pretrained_baseline_m1.pkl di akar character-classification/ diabaikan untuk v1.0 (keputusan pengembang).
    ignored = models_dir / "character-classification" / "pretrained_baseline_m1.pkl"
    in_lexicon = [False]
    for path in sorted(p for p in models_dir.rglob("*") if p.is_file()):
        in_lexicon[0] = "lexicon" in path.parts
        if path.suffix == ".npy":  # bagian internal .bin (gensim), dihitung di ukuran .bin induknya
            continue
        size_mb = path.stat().st_size / 1_048_576
        if path.suffix == ".bin":
            npy = path.with_name(path.name + ".wv.vectors_ngrams.npy")
            if npy.is_file():
                size_mb += npy.stat().st_size / 1_048_576
        print(f"  {path.relative_to(models_dir)}  ({size_mb:.1f} MB"
              f"{', termasuk vectors_ngrams.npy; perkiraan RAM saat dimuat' if path.suffix == '.bin' else ''})")
        if path.suffix != ".pkl":
            continue
        if path == ignored:
            print("        diabaikan untuk v1.0 (keputusan pengembang)")
            continue
        if size_mb > max_mb:
            print(f"        dilewati (> {max_mb} MB; naikkan dengan --inspect-max-mb)")
            continue
        try:
            obj = pm.unpickle(path)
            if isinstance(obj, dict):
                summary(obj)
            else:
                print(f"        {pm.describe(obj)}")
        except Exception as exc:  # noqa: BLE001
            print(f"        gagal dibaca: {exc!r}")



def dump_api(root: Path) -> Path:
    """Tulis signature, docstring, dan source modul balinese-nlp yang relevan untuk TF5 ke _reference/."""
    heading("API balinese-nlp UNTUK WORD EMBEDDING (TF5) DAN SENTENCE GROUPING")
    lines: list[str] = []
    for name in API_MODULES:
        try:
            module = importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            print(f"  {name}: tidak bisa diimpor ({exc!r})")
            lines.append(f"# {name}: tidak bisa diimpor ({exc!r})\n")
            continue
        print(f"  {name}  ({getattr(module, '__file__', '?')})")
        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != name:
                continue
            try:
                init_sig = str(inspect.signature(cls))
            except (TypeError, ValueError):
                init_sig = "(...)"
            print(f"    class {cls_name}{init_sig}")
            for meth_name, meth in inspect.getmembers(cls, inspect.isfunction):
                if meth_name.startswith("_"):
                    continue
                doc = (inspect.getdoc(meth) or "").splitlines()
                print(f"      .{meth_name}{inspect.signature(meth)}  {doc[0] if doc else ''}")
        for fn_name, fn in inspect.getmembers(module, inspect.isfunction):
            if fn.__module__ == name and not fn_name.startswith("_"):
                print(f"    def {fn_name}{inspect.signature(fn)}")
        try:
            lines.append(f"# {'=' * 70}\n# {name}\n# {getattr(module, '__file__', '?')}\n# {'=' * 70}\n")
            lines.append(inspect.getsource(module))
        except (OSError, TypeError) as exc:
            lines.append(f"# source tidak tersedia: {exc!r}\n")
    out = root / REFERENCE_DIR / API_DUMP_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Source lengkap ditulis ke: {out}")
    print("  Kirim berkas itu ke Claude agar ekstraksi TF5 bisa ditulis sesuai interface Hugging Face paket.")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uji NER tokoh, alias clustering, dan klasifikasi peran.")
    parser.add_argument("--root", help="akar proyek yang memuat _reference/")
    parser.add_argument("--input", help="file .txt satua")
    parser.add_argument("--models-dir", help=f"folder pretrained-models; bawaan dari {pm.MODELS_ENV_VAR} (environment atau .env)")
    parser.add_argument("--ner-model", default="satuaner", choices=["satuaner", "crf1_baseline", "crf2_baseline", "svm_baseline", "hmm"])
    parser.add_argument("--similarity", default="sorensen-dice", choices=["ratcliff", "jaccard", "sorensen-dice", "jaro-distance", "jaro-winkler"])
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--variant", default=pm.DEFAULT_VARIANT, choices=["m1", "m2"], help="varian pretrained (bawaan m2)")
    parser.add_argument("--feature", default=pm.DEFAULT_FEATURE, help="kode fitur TF1-TF5, gabungan pakai _ (mis. TF4_TF5); bawaan TF5")
    parser.add_argument("--classifier-name", default=pm.DEFAULT_CLASSIFIER, choices=list(pm.ALGORITHM_FILE_PREFIX))
    parser.add_argument("--classifier-path", help="path langsung ke satu pickle classifier (mengabaikan --variant)")
    parser.add_argument("--label-encoder", help="path pickle label encoder, bila berbeda dari bawaan")
    parser.add_argument("--tf5-repo", help=f"repo Hugging Face FastText; bawaan dari {pm.TF5_REPO_ENV_VAR}")
    parser.add_argument("--tf5-file", help=f"nama file .bin FastText; bawaan dari {pm.TF5_FILENAME_ENV_VAR}")
    parser.add_argument("--legacy-preprocess", action="store_true",
                        help="praproses konteks seperti web lama (tanpa case folding efektif) untuk perbandingan")
    parser.add_argument("--drop-title", action="store_true", help="buang baris pertama bila berupa judul")
    parser.add_argument("--inspect", action="store_true", help="tampilkan isi folder model lalu berhenti")
    parser.add_argument("--inspect-max-mb", type=int, default=300, help="batas ukuran pickle yang dibuka saat --inspect")
    parser.add_argument("--dump-api", action="store_true", help=f"tulis API/source modul word embedding ke {REFERENCE_DIR}/{API_DUMP_NAME}")
    parser.add_argument("--output", help="simpan hasil ke file JSON")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    global LEGACY_PREPROCESS
    LEGACY_PREPROCESS = args.legacy_preprocess
    root = find_root(args.root)
    input_path = Path(args.input) if args.input else root / SAMPLE_REL
    models_dir, models_source = pm.resolve_models_dir(root, args.models_dir)
    status: dict[str, str] = {}
    result: dict = {
        "input": str(input_path),
        "models_dir": str(models_dir),
        "config": {k: v for k, v in vars(args).items() if k not in {"inspect", "output", "dump_api"}},
    }

    def fail(step: str, exc: Exception) -> None:
        status[step] = "GAGAL"
        print(f"  [GAGAL] {exc}")
        if not isinstance(exc, StepError):
            traceback.print_exc()

    try:
        if args.dump_api:
            dump_api(root)
            return 0
        if args.inspect:
            inspect_models(models_dir, args.inspect_max_mb)
            return 0
        codes = pm.parse_feature_codes(args.feature)
        report_environment()
        print(f"  Folder model ({models_source}): {models_dir}")
        result["package_has_supervised_files"] = report_supervised_in_package()

        heading("1. PRAPROSES")
        raw = read_text(input_path)
        print(f"  File: {input_path.name} ({len(raw)} karakter)")
        first_line, _, remainder = raw.strip().partition("\n")
        if remainder and not first_line.rstrip().endswith((".", "!", "?", '"')):
            if args.drop_title:
                raw = remainder
                print(f"  Baris judul dibuang: {first_line.strip()}")
            else:
                warn(f"Baris pertama mirip judul dan akan menyatu dengan kalimat pertama: '{first_line.strip()}'. Pakai --drop-title untuk membuangnya.")
        tp, text, sentences = preprocess_story(raw)
        print(f"  {len(sentences)} kalimat. Tiga kalimat pertama:")
        for sentence in sentences[:3]:
            print(f"    - {sentence}")
        if len(sentences) < MIN_SENTENCES:
            warn(f"Kurang dari {MIN_SENTENCES} kalimat, batas minimum pada tesis")
        status["Praproses"] = "OK"
    except Exception as exc:  # noqa: BLE001
        fail("Persiapan", exc)
        return 1

    groups = None
    try:
        heading("2. TUGAS (i): IDENTIFIKASI TOKOH")
        model, characters = identify_characters(args.ner_model, text, sentences)
        show_bio_example(model, sentences, characters)
        result["characters"] = characters
        status["(i) Identifikasi tokoh"] = "OK"

        heading("3. TUGAS (ii): ALIAS CLUSTERING")
        groups = cluster_aliases(characters, args.similarity, args.threshold)
        result["alias_groups"] = groups
        status["(ii) Alias clustering"] = "OK"
    except Exception as exc:  # noqa: BLE001
        fail("(i)/(ii)", exc)

    if groups:
        try:
            heading("4. TUGAS (iii): KLASIFIKASI PERAN TOKOH")
            print("  Sumber model: pickle eksperimen tesis di luar paket balinese-nlp")
            override = Path(args.classifier_path) if args.classifier_path else None
            estimator, selected, encoder, scaler = load_classifier(
                models_dir, args.variant, codes, args.classifier_name, args.label_encoder, override
            )
            repo_id, filename = pm.embedding_config(root)
            if args.tf5_repo or args.tf5_file:  # penimpaan manual lewat argumen berarti memakai Hugging Face
                repo_id = args.tf5_repo or pm.DEFAULT_TF5_REPO_ID
                filename = args.tf5_file or pm.DEFAULT_TF5_FILENAME
            if any(code == "TF5" for code, _ in selected):
                print(f"  Embedding TF5: {repo_id} / {filename} (Hugging Face, via BaliFastText)")
            result["tf5_embedding"] = {"repo_id": repo_id, "filename": filename}

            def embedding_loader():
                started = time.perf_counter()
                model = pm.load_fasttext(repo_id, filename)
                print(f"  FastText dimuat: vector_size {model.vector_size}, {time.perf_counter() - started:.1f} dtk")
                return model

            df = group_sentences(sentences, groups)
            def lexicon_loader():
                return pm.load_balisentilex(str(pm.balisentilex_path(root)))

            roles = classify_roles(df, groups, tp, estimator, selected, encoder, embedding_loader,
                                   lexicon_loader=lexicon_loader, scaler=scaler)
            print_roles(roles)
            result["roles"] = roles
            status["(iii) Klasifikasi peran"] = "OK"
        except Exception as exc:  # noqa: BLE001
            fail("(iii) Klasifikasi peran", exc)

    heading("RINGKASAN")
    for step, state in status.items():
        print(f"  {step:<28}{state}")
    if not result.get("package_has_supervised_files"):
        print("\n  Paket yang terpasang belum memuat model klasifikasi supervised, jadi tugas (iii) masih bergantung pada pickle luar.")
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Hasil disimpan ke {args.output}")
    return 1 if "GAGAL" in status.values() or len(status) < 4 else 0


if __name__ == "__main__":
    sys.exit(main())
