# PrasiBali: aturan kerja untuk Claude Code

Baca file ini dan `_reference/konteks_proyek.md` di awal setiap sesi sebelum menulis kode.
Sebelum mengubah template atau CSS, baca `DESIGN.md` dan ikuti aturannya.

## Produk

PrasiBali adalah web app analisis satua (cerita rakyat) Bali. Fungsinya: (i) identifikasi tokoh, (ii) alias clustering, dan (iii) klasifikasi peran protagonis/antagonis. Model-modelnya berasal dari penelitian tesis S2 pengembang di Institut Teknologi Sepuluh Nopember (2024). Aplikasi ini diikutkan ke AI Web Innovation Challenge, Bali Digital Festival 2026, Tahap 1.

Bahasa antarmuka: Indonesia (default) dan Inggris.

**Fitur inti v1.0 (wajib berfungsi end-to-end):**
- Analisis satua dengan pipeline lengkap: identifikasi tokoh, alias clustering, klasifikasi peran.
- Mode tugas terpisah: identifikasi, alias, peran, atau pipeline lengkap.
- Hasil bertahap: teks dengan nama tokoh disorot beserta label nama entitas tokohnya (PNAME, ANM, GODS, ADJ, OBJ), kartu kelompok alias dengan warna kartu yang berbeda antar kelompok tokoh, label peran dari setiap kelompok tokoh dengan disclaimer.
- **Mode Peneliti** untuk memilih model dan parameter tiap tugas sesuai eksperimen di buku tesis (lihat bagian "Mode Peneliti").
- Riwayat analisis (daftar, detail, hapus satu, hapus semua), kuota harian per pengguna, tombol "Coba contoh satua".
- Akun: registrasi, verifikasi email, login, logout, reset password, profil, pilihan bahasa.

**"Segera Hadir" (hanya tampilan, tanpa logika):** Coreference, Social Graph, Quote Attribution, Summarization, Aksara Bali.

**Di luar v1.0:** Celery/Redis, React, pelatihan ulang model, eksperimen dengan coreference resolution, REST API (Sesi 6, opsional).

## Stack terkunci (jangan diganti tanpa persetujuan)

- Python 3.11 (satu-satunya versi, lokal maupun server; lihat `.python-version`)
- Django 5.2 LTS dengan PostgreSQL 16
- django-allauth (autentikasi), django-environ (konfigurasi)
- Django REST Framework + drf-spectacular (hanya jika Sesi 6 dikerjakan)
- Tailwind CSS (standalone CLI, tanpa Node) + HTMX + Alpine.js
- Gunicorn + Caddy (HTTPS otomatis), whitenoise untuk file statis
- Docker Compose (lokal: `docker-compose.yml`; produksi: `docker-compose.prod.yml`)
- SMTP Hostinger Email (mailbox domain `prasibali.tech`, `smtp.hostinger.com:587` STARTTLS; nilai dari `.env`). Mail API Hostinger tidak dipakai
- pytest, pytest-django, ruff, GitHub Actions

## Struktur repo

```text
src/
  config/            settings (base, dev, prod), urls, wsgi
  apps/
    accounts/        registrasi, verifikasi email, login, profil, bahasa
    analysis/        pipeline AI, riwayat analisis, kuota
      services/      model_catalog.py, model_registry.py, pipeline.py, validasi teks
    pages/           beranda, tentang, fitur "Segera Hadir", privasi
    api/             REST API + dokumentasi OpenAPI
  templates/  static/  locale/ (id, en)
  manage.py
models/              artefak model untuk Docker (di-.gitignore, tidak di-commit)
tests/               pytest: pipeline, katalog model, auth, kuota, riwayat
docker/              Dockerfile, Caddyfile
docs/                arsitektur, screenshot, deploy.md
scripts/             check_env.py, test_pretrained_pipeline.py, prasibali_models.py (utilitas bersama)
```

## Aturan model AI

### Sumber model
- **(i) NER tokoh dan (ii) alias clustering** memakai paket `balinese-nlp==2.4.2` dari PyPI. Jangan menyalin kode model ke dalam web app, dan jangan mengunduh model dari Google Drive.
- **(iii) Classifier peran** tidak ada di dalam `balinese-nlp`. Semua pickle pretrained (hasil eksperimen tesis) berada di folder `pretrained-models/` yang path-nya dibaca dari env `PRETRAINED_MODELS_DIR`. Folder itu berisi:
  ```text
  pretrained-models/
    character-classification/
      lexicon/m1/     TF1, TF2, TF3, TF1_TF2, TF1_TF3, TF2_TF3, TF1_TF2_TF3 (_pretrained_baseline_m1.pkl)
      lexicon/m2/     {dt,gnb,knn,mlp,rf,svm}_pretrained_model.pkl
      wordvector/m1/  TF4, TF5, TF4_TF5 (_pretrained_baseline_m1.pkl)
      wordvector/m2/  {dt,gnb,knn,mlp,rf,svm}_pretrained_model.pkl
      pretrained_baseline_m1.pkl
    label-encoder/    without_coreference_splitted_characterization.pkl
  ```
  - Lokal: `PRETRAINED_MODELS_DIR` menunjuk `J:\Dosen - Universitas Udayana\DriveSync\4. Software Penelitian\#15-prasibali.ai\models\`.
  - Docker/produksi (Sesi 7): isi folder lokal `models/` disalin ke `~/prasibali/models/` di server (di luar git), lalu di-mount read-only ke `/app/models` dengan `PRETRAINED_MODELS_DIR=/app/models`, sama seperti `docker-compose.yml` lokal. Lihat `docs/deploy.md`.
  - Jangan meng-commit file `.pkl`/`.joblib` ke repo.
- Struktur bundle M1 yang sudah terverifikasi (wordvector/m1/TF4): `dict` berkunci nama algoritma (`K-Nearest Neighbor`, `Support Vector Machine`, `Decision Tree`, `Gaussian Naive Bayes`, `Random Forest`, `Multilayer Perceptron`); tiap nilai berisi `["pretrained_model"]["estimator"]` dan `["pretrained_model"]["feature_extractor"]` (dict berkunci kode fitur, mis. `"TF4"`). Struktur bundle lain (lexicon, M2) **belum diverifikasi**: periksa dengan `python scripts/test_pretrained_pipeline.py --inspect` sebelum menulis kode pemuatnya. `pretrained_baseline_m1.pkl` di root diabaikan untuk v1.0.
- M2 berisi satu file per algoritma per jenis fitur. Asumsi kerja (verifikasi dengan `--inspect`): tiap file M2 memakai kombinasi fitur terbaik algoritma itu di jenis fiturnya (Tabel 4.56 untuk leksikon, Tabel 4.57 untuk word vector).
- Label encoder memetakan ke kelas `['Antagonis', 'Protagonis']`.
- **Alur pemuatan dan ekstraksi fitur yang sudah teruji ada di `scripts/prasibali_models.py`** (`bundle_path`, `extract_model_entry`, `select_extractors`, `featurize`, `check_feature_count`, `score_and_probability`). Layanan di `src/apps/analysis/services/` wajib mengikuti logika yang sama, termasuk urutan penggabungan fitur (sesuai urutan kode di nama file, mis. TF4 lalu TF5) dan pengecekan `n_features_in_`.

### Katalog model (`model_catalog.py`)
- Semua pilihan model didefinisikan dalam katalog statis di kode, satu entri per eksperimen. Setiap entri berisi: `id` (contoh `m2-wordvector-tf5-svm`), varian (M1/M2), jenis fitur (leksikon / word vector), kode fitur (contoh `TF5`), algoritma, path relatif terhadap `PRETRAINED_MODELS_DIR`, kunci di dalam bundle, rujukan tabel/lampiran tesis, **dua nilai F1 referensi**, dan status `available`.
- **Dua versi F1 referensi** ditampilkan berdampingan agar hasil terlihat valid dan bisa ditelusuri:
  - `f1_cv`: rata-rata F1 10-fold cross-validation (Tabel 4.56, 4.57, 4.59; Lampiran 14). Nilai ini milik konfigurasi algoritma + fitur, sehingga sama untuk M1 dan M2.
  - `f1_test`: F1 pada data uji, berbeda per varian (Tabel 4.60; Lampiran 15 untuk M1, Lampiran 16 untuk M2).
  - Angka yang sudah terverifikasi ada di tabel `_reference/konteks_proyek.md` bagian 4.3. Angka lain **tidak boleh dikarang**: biarkan `None` dan tampilkan "–".
- Hanya entri yang ekstraksi fiturnya bisa direproduksi di aplikasi yang boleh `available=True`. TF4 (TF-IDF) terbukti punya `transform()`. TF5 dan fitur leksikon (TF1–TF3) mengikuti aturan di bagian "Word embedding (TF5)" dan harus dikonfirmasi pengembang sebelum ditandai tersedia.
- **Default (mode Pengguna Umum): `m2-wordvector-tf4-knn`** (`DEFAULT_CLASSIFIER_ID`). Keputusan pengembang 4 November 2026: pada uji coba beberapa satua di Mode Peneliti, KNN + TF4 memberi hasil peran yang lebih baik. Rujukan tesis: F1 CV 0,6666 (fitur word vector terbaik untuk KNN, Tabel 4.57) dan F1 uji M2 0,6451 (Tabel 4.60). Model ini tidak butuh FastText.
- **Model terbaik menurut tesis: `m2-wordvector-tf5-svm`** (`THESIS_BEST_CLASSIFIER_ID`): F1 CV tertinggi (0,6811; Tabel 4.57/4.59), dan M2 dipilih karena F1 ujinya lebih tinggi daripada M1 (0,6460 vs 0,6366; Tabel 4.60). Di Mode Peneliti ditandai "terbaik menurut tesis"; default ditandai "bawaan". `warm_models` tetap memuat FastText agar model TF5 siap tanpa menunggu.

### Word embedding (TF5) dan Hugging Face
- TF5 = rata-rata vektor word embedding FastText bahasa Bali (Tabel 3.10 menyebut 300 dimensi). Interface di `balinese-nlp` 2.4.2 (sudah dikonfirmasi dari source pengembang):
  ```python
  from balinese_nlp.embeddings.gensims import BaliFastText
  model = BaliFastText(
      huggingface_repo_ID="satriabimantara/balinese_pretrained_wordembedding",
      pretrained_model_bin_filename="300_fasttext_model.bin",
  ).load_pretrained_model()          # model gensim: model.wv[kata], model.vector_size

  from balinese_nlp.feature_extractor.narratives.characterclassification.WordEmbeddingFeatureExtraction import (
      WordEmbeddingFeatureExtraction,
  )
  X = WordEmbeddingFeatureExtraction(pretrained_word_embedding=model).fit(list_konteks).transform()
  # rata-rata model.wv[kata] untuk kata (dipisah spasi) yang ada di model.wv; vektor nol bila tidak ada
  ```
- **Pola ekstraktor balinese-nlp berbeda dari scikit-learn:** `WordEmbeddingFeatureExtraction`, `LexiconFeatureExtraction`, dan `POSTagFeatureExtraction` dipakai dengan `fit(X).transform()`, di mana `transform()` tidak menerima argumen dan menyimpan state di instance. TF-IDF (TF4) memakai `transform(X)`. Adaptor `prasibali_models.run_extractor()` menangani keduanya, ditambah model gensim yang tersimpan langsung dan TF5 yang tidak tersimpan di pickle. Jangan memakai satu instance ekstraktor dari beberapa thread sekaligus (pakai worker Gunicorn sync).
- Repo dan nama file FastText dibaca dari env `TF5_HF_REPO_ID` dan `TF5_FASTTEXT_FILENAME` (kosong = nilai bawaan di atas). File itu **harus sama** dengan yang dipakai saat melatih pickle TF5. Buktinya: `model.vector_size` sama dengan `n_features_in_` estimator TF5. `check_env.py` mengecek ini dan gagal dengan pesan jelas bila berbeda. Semua estimator TF5 punya `n_features_in_` 300 (`--inspect`, 2 November 2026), jadi nama file bawaan adalah `300_fasttext_model.bin`.
- Urutan pemuatan FastText di aplikasi (`services/embeddings.py`): file lokal `PRETRAINED_MODELS_DIR/balinese-word-embedding/<TF5_FASTTEXT_FILENAME>` bila ada, jika tidak dari Hugging Face lewat `BaliFastText`. Dimensinya dicek terhadap bagian TF5 dari `n_features_in_` sebelum dipakai.
- Jika `BasePretrained` mendukung parameter revisi Hugging Face, pin revisinya di env. Jika tidak, andalkan cache yang sudah terisi dengan `HF_HUB_OFFLINE=1` (baca source `BasePretrained` lewat `--dump-api`).
- Unduhan embedding terjadi sekali saja, tidak pernah per request:
  - Folder cache Hugging Face (`HF_HOME`) berada di volume Docker yang persisten.
  - Management command `warm_models` mengunduh dan memuat embedding serta model default saat container start.
  - Setelah cache terisi, produksi berjalan dengan `HF_HUB_OFFLINE=1`.
  - Jika repo Hugging Face privat, token dibaca dari `HF_TOKEN` di `.env`.
- Catat ukuran file embedding dan pemakaian RAM-nya di `docs/deploy.md`. Ukuran ini menentukan jumlah worker Gunicorn di VPS 8 GB.

### Pemuatan dan pencatatan
- Pemilihan model dari pengguna **hanya berupa `id` katalog** yang divalidasi di server (whitelist). Jangan pernah menerima path file dari input pengguna, karena memuat pickle bisa menjalankan kode.
- Muat model secara lazy dengan `lru_cache` di `model_registry.py`: model default dan SatuaNER dimuat saat start, model lain saat pertama dipilih, dengan batas jumlah bundle di cache agar RAM tetap terkendali.
- Setiap `AnalysisRun` menyimpan konfigurasi lengkap dan `model_version`: versi `balinese-nlp`, model NER, metode dan ambang alias, `id` katalog classifier, serta hash SHA-256 pendek file pickle.
- Jika folder model tidak ada atau pickle gagal dimuat, aplikasi tetap menyala; tahap klasifikasi gagal dengan exception khusus dan pesan ramah.
- Jangan melatih ulang model di tahap ini.

### Efek samping paket yang wajib ditangani
- `balinese_nlp.quoteattribution.rule_based.RuleBasedSentenceGrouping` (dipakai sebelum klasifikasi) membuat folder `saved_file` relatif terhadap direktori kerja. Di laptop, folder itu muncul di akar repo dan sudah di-`.gitignore`. Sebelum membungkusnya, baca source-nya (juga ada di `_reference/balinese_nlp_api_dump.txt`). Setelah itu pastikan folder tersebut berada di lokasi yang bisa ditulis (misalnya folder temp/cache khusus yang di-`.gitignore`), atau matikan penyimpanannya jika ada parameternya. Jangan sampai aplikasi gagal di container non-root atau mengotori disk setiap request.

### Tampilan hasil klasifikasi
- Kartu hasil peran wajib memuat disclaimer bahwa label adalah alat bantu analisis dan akurasi model terbatas (F1 rata-rata di tesis di bawah 0,70).
- Tampilkan skor model apa adanya beserta penjelasannya. Untuk SVM yang ditampilkan adalah `decision_function` (jarak ke hyperplane, bukan probabilitas); untuk model yang mendukungnya, `predict_proba` boleh ditampilkan. Jangan menyebut skor sebagai "keyakinan" atau persentase jika memang bukan probabilitas.
- Tampilkan peringatan "konteks sedikit, hasil kurang andal" untuk kelompok tokoh dengan konteks yang sangat sedikit (jumlah kata konteks atau term yang dikenal di bawah ambang yang dapat dikonfigurasi).

### Pin dan batas
- Blok "AI / NLP" di `requirements.txt` dipin persis (scikit-learn 1.2.1 wajib agar pickle bisa dimuat). Mengubah pin berarti menguji ulang hasil terhadap web lama.
- Di Docker, `torch` dipasang dari index CPU (`--extra-index-url https://download.pytorch.org/whl/cpu`) agar image tidak membawa CUDA.
- Jangan menebak API `balinese-nlp`. Baca `_reference/balinese_nlp_notes.md`, source paket di `.venv`, dan `scripts/test_pretrained_pipeline.py` (alur yang sudah terbukti berjalan).
- Batas input: 20.000 karakter.

## Mode Peneliti

Mode biasa memakai konfigurasi default tanpa pilihan. Mode Peneliti adalah panel yang bisa dibuka di halaman Analisis, berisi:

| Tugas | Pilihan | Default |
|---|---|---|
| (i) Identifikasi tokoh | Model NER: `satuaner`, `crf1_baseline`, `crf2_baseline`, `svm_baseline`, `hmm` | `satuaner` |
| (ii) Alias clustering | Metode: `ratcliff`, `jaccard`, `sorensen-dice`, `jaro-distance`, `jaro-winkler`; ambang kemiripan | `jaro-distance`, 0,85 (terbaik menurut tesis untuk SatuaNER M2: F1 0,7172, Tabel 4.36/4.37) |
| (iii) Klasifikasi peran | Varian pretrained (M1/M2) → jenis fitur → kode fitur → algoritma, hanya dari entri katalog yang `available` | `m2-wordvector-tf4-knn` (terbaik menurut tesis: `m2-wordvector-tf5-svm`) |

- Setiap pilihan classifier menampilkan keterangan singkat eksperimen beserta dua nilai F1 referensi dari tesis dan rujukan tabelnya, misalnya "F1 CV 0,6811 (Tabel 4.59) · F1 uji 0,6460 (Tabel 4.60)". Model terbaik menurut tesis ditandai "terbaik menurut tesis", default ditandai "bawaan".
- Mode tampilan: tombol "Pengguna Umum" (bawaan, memakai default) dan "Lanjutan (Mode Peneliti)". Tombol "Reset" di ruang kerja mengosongkan teks dan hasil serta kembali ke mode Pengguna Umum dan model bawaan.
- Konfigurasi yang dipakai disimpan di riwayat, dan halaman detail riwayat menampilkannya.
- Mode Peneliti tersedia untuk semua pengguna yang login; kuota hariannya sama dengan mode biasa.

## Keamanan dan privasi

- Tidak ada secret di kode, di repo, atau di riwayat git. Semua nilai dibaca dari `.env`. `.env.example` hanya berisi nama variabel, tanpa nilai.
- Jangan membaca `.env` dan jangan mencetak nilai secret ke output, log, atau commit.
- Teks pengguna tidak boleh dikirim ke API pihak ketiga. Model berjalan di server sendiri.
- Semua view analisis dan riwayat butuh login dan email terverifikasi.
- Akun demo dibuat lewat `python manage.py create_demo_user`, dengan kredensial dari env. Jangan menulis email atau password demo di repo atau README.
- Pengguna bisa menghapus riwayat dan akunnya sendiri.
- Settings produksi memuat semua header keamanan. Jangan melemahkannya.

## Konvensi kode

- Identifier dan komentar kode: bahasa Inggris.
- Teks untuk pengguna: lewat gettext, dengan terjemahan Indonesia dan Inggris.
- Setiap fitur baru punya test pytest. `ruff check .` harus lulus sebelum commit.
- Test yang butuh pickle ditandai `@pytest.mark.model` dan di-skip bila `PRETRAINED_MODELS_DIR` tidak ada (misalnya di GitHub Actions). Test katalog (validasi id, whitelist, default) tidak butuh pickle dan wajib jalan di CI.
- Commit kecil per tugas, dengan pesan Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
- Paket runtime masuk ke `requirements.txt`; paket khusus development masuk ke `requirements-dev.txt` (yang sudah memuat `-r requirements.txt`). Pasang dengan `pip install -r`, jangan `pip install nama-paket` saja.
- Environment lokal adalah `.venv` (Python 3.11). Jangan memakai `conda install`.

## Perintah

```bash
python -m pip install -r requirements-dev.txt          # dependensi lokal
python scripts/check_env.py                            # cek environment + classifier default end-to-end
python scripts/check_env.py --no-smoke                 # tanpa ekstraksi fitur (mis. tanpa internet)
python scripts/test_pretrained_pipeline.py --inspect   # lihat struktur semua pickle (tipe ekstraktor, n_features_in_)
python scripts/test_pretrained_pipeline.py --dump-api  # tulis API/source modul embedding ke _reference/
python scripts/test_pretrained_pipeline.py --input "<file satua .txt>"   # uji tugas (i)-(iii), default SVM+TF5 M2
python scripts/test_pretrained_pipeline.py --variant m1 --feature TF4    # uji model lain
python scripts/tailwind.py build                       # build src/static/css/app.css (Tailwind standalone, di-commit)
python scripts/generate_ikat.py                        # tulis ulang partial pita ikat
cd src && python manage.py makemessages -l id -l en --no-location && python manage.py compilemessages   # terjemahan (.mo di-commit)
python src/manage.py create_demo_user                  # akun demo dari DEMO_USER_EMAIL/DEMO_USER_PASSWORD
docker compose up --build                              # jalankan lokal
docker compose exec web pytest                         # test
ruff check .                                           # lint
```

## Larangan

- Jangan mengubah repo lama `BaliStoryAnalyzer` atau paket `balistoryanalyzer`. Keduanya artefak riset yang disitasi.
- Jangan meng-commit folder `_reference/`, `models/`, `.venv/`, `saved_file/`, atau `.env`.
- Jangan menjalankan `git push` atau membuat tag tanpa konfirmasi.
- Jangan menambah polesan UX/UI di luar tugas sesi yang sedang berjalan. Rubrik Tahap 1 tidak menilai UX/UI.

## Cara kerja

- Mulai setiap tugas besar dengan plan mode. Tunggu persetujuan sebelum menulis kode.
- Di akhir sesi: jalankan pytest dan ruff, ringkas perubahan, lalu buat commit.
- Jika ada keputusan yang tidak jelas, tanyakan dulu. Jangan berasumsi.
