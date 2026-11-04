# AI & Technology Disclosure: PrasiBali

Dokumen ini mengikuti Lampiran C Panduan Peserta AI Web Innovation Challenge, Bali Digital Festival 2026. Isinya berlaku untuk rilis **`v1.0-submission`** (Tahap 1, November 2026) di repositori ini dan di <https://prasibali.tech>. Ringkasan ada di tabel pertama; rinciannya di bagian bernomor setelahnya.

## Ringkasan

| Komponen | Isi |
|---|---|
| **Nama Produk** | PrasiBali: aplikasi web analisis tokoh satua (cerita rakyat) Bali berbasis NLP |
| **Framework / Frontend** | Django Templates, Tailwind CSS 4.3.3 (standalone CLI), HTMX 2.0.4, Alpine.js 3.14.8, ikon Lucide (SVG inline) ([§4](#4-framework-runtime-database-dan-hosting)) |
| **Backend / Runtime** | Python 3.11, Django 5.2 LTS, django-allauth 65, Gunicorn 23, WhiteNoise 6 ([§4](#4-framework-runtime-database-dan-hosting)) |
| **Database / Storage** | PostgreSQL 16 (akun, riwayat analisis, kuota); folder `models/` read-only untuk pickle; volume Docker untuk cache Hugging Face dan backup harian ([§4](#4-framework-runtime-database-dan-hosting)) |
| **Hosting / Deployment** | VPS Hostinger KVM 1 (Ubuntu), Docker Compose, Caddy 2.10 dengan HTTPS Let's Encrypt, domain `prasibali.tech`, SMTP Hostinger Email ([§4](#4-framework-runtime-database-dan-hosting)) |
| **AI Model / API / Method** | (i) SatuaNER: CRF + seleksi fitur BPSO; (ii) alias clustering berbasis aturan dengan kemiripan string Jaro distance; (iii) classifier peran supervised ML (bawaan KNN + TF-IDF, M2; 24 konfigurasi di Mode Peneliti) dengan embedding FastText bahasa Bali untuk fitur TF5. Semua model buatan pengembang, berjalan di server sendiri. **Tidak memakai LLM atau API AI pihak ketiga** ([§1](#1-ai-model-api-dan-metode)) |
| **Peran AI dalam Produk** | Inti produk: mengenali tokoh dan label entitasnya, mengelompokkan alias, dan memberi label protagonis/antagonis per kelompok tokoh. Output adalah alat bantu analisis dengan disclaimer ([§2](#2-peran-ai-dalam-produk)) |
| **Dataset / Data Source** | *Balinese Story Texts Dataset* (120 satua beranotasi), dipublikasikan di *Data in Brief* 56 (2024) 110781 dan Mendeley Data (CC BY 4.0). Teks pengguna tidak dipakai untuk melatih model ([§3](#3-dataset-dan-sumber-data)) |
| **Open-source Libraries** | `balinese-nlp`, scikit-learn, sklearn-crfsuite, gensim, PyTorch, Transformers, pandas, NumPy, Django, django-allauth, dan lainnya ([§5](#5-library-open-source)) |
| **Template / Boilerplate** | Tidak memakai template atau starter kit pihak ketiga. Struktur awal dari `django-admin startproject`; template bawaan django-allauth ditimpa dengan template sendiri ([§6](#6-template-dan-boilerplate)) |
| **AI Coding Assistant** | Claude Code (model Claude Opus, Anthropic) dan Claude.ai (chat dan Project) untuk perencanaan, kode, test, dokumentasi, dan sketsa logo ([§7](#7-ai-coding-assistant)) |
| **Pre-existing Components** | Hasil riset tesis (model, dataset, paket `balinese-nlp`, embedding FastText, BaliStoryAnalyzer) dan aplikasi web lama BaliNarrativeNLP. Aplikasi web PrasiBali dibangun baru untuk kompetisi ([§8](#8-komponen-pra-kompetisi)) |
| **Third-party Assets / Credits** | Font Schibsted Grotesk dan Noto Serif Balinese (SIL OFL 1.1), ikon Lucide (ISC), sertifikat Let's Encrypt. Logo dan pola ikat dibuat khusus untuk PrasiBali ([§9](#9-aset-pihak-ketiga-dan-kredit)) |

---

## 1. AI model, API, dan metode

### 1.1 Model di dalam pipeline

Ketiga tahap berjalan berurutan di server PrasiBali untuk setiap analisis ([`src/apps/analysis/services/pipeline.py`](src/apps/analysis/services/pipeline.py)). Konfigurasi bawaan mode Pengguna Umum:

| Tahap | Model bawaan | Metode | Input → Output | Sumber model | Lisensi |
|---|---|---|---|---|---|
| (i) Identifikasi tokoh | **SatuaNER** (`satuaner.pkl`) | Conditional Random Fields dengan fitur leksikal, morfologis, konteks, dan POS tag, diseleksi dengan Hybrid Binary Particle Swarm Optimization (BPSO-CRF) | Kalimat satua (huruf Latin) → tag BIO per token dengan label `PNAME`, `ANM`, `GODS`, `ADJ`, `OBJ` | Paket `balinese-nlp` 2.4.2 (PyPI) | BSD-3-Clause |
| (ii) Alias clustering | `AliasClusteringRuleBased` | Pengelompokan berbasis aturan dengan *pairwise string similarity* Jaro distance, ambang rata-rata 0,85 | Daftar nama tokoh unik → kelompok tokoh (`Tokoh-1`, `Tokoh-2`, ...) | Paket `balinese-nlp` 2.4.2 | BSD-3-Clause |
| (iii) Klasifikasi peran | **`m2-wordvector-tf4-knn`** (`knn_pretrained_model.pkl`) | K-Nearest Neighbor pada fitur TF-IDF (TF4), varian M2 | Gabungan kalimat yang menyebut tiap kelompok → `Protagonis` atau `Antagonis` | Pickle hasil eksperimen tesis (lihat §1.5) | BSD-3-Clause (bagian dari karya pengembang) |

Komponen pendukung, semuanya dari `balinese-nlp` 2.4.2:

| Komponen | Fungsi |
|---|---|
| `TextPreprocessor` | Pemecahan kalimat, normalisasi, dan pembersihan teks bahasa Bali |
| `HiddenMarkovModelPOSTag` | POS tagger HMM bahasa Bali; tag-nya menjadi fitur SatuaNER. Aplikasi memakai satu instance bersama dengan cache per token ([`postag_cache.py`](src/apps/analysis/services/postag_cache.py)) tanpa mengubah hasil |
| `RuleBasedSentenceGrouping` | Mengumpulkan kalimat konteks untuk setiap kelompok tokoh sebelum klasifikasi |
| `WordEmbeddingFeatureExtraction`, `BaliFastText` | Fitur TF5: rata-rata vektor FastText 300 dimensi dari kata-kata konteks |
| Label encoder (`without_coreference_splitted_characterization.pkl`) | Memetakan keluaran classifier ke kelas `['Antagonis', 'Protagonis']` |

### 1.2 Pilihan model identifikasi tokoh (Mode Peneliti)

F1 dari Tabel 4.18 (rata-rata cross-validation) dan Tabel 4.19 (macro F1 data uji, M2) buku tesis.

| `id` | Model | F1 CV | F1 uji |
|---|---|---|---|
| `satuaner` (bawaan) | SatuaNER (CRF + BPSO) | 0,954 | 0,8353 |
| `crf2_baseline` | CRF-2 | 0,9518 | 0,8262 |
| `crf1_baseline` | CRF-1 | 0,9467 | 0,8122 |
| `svm_baseline` | SVM | 0,947 | 0,8072 |
| `hmm` | Hidden Markov Model | 0,932 | 0,7312 |

### 1.3 Pilihan metode alias clustering (Mode Peneliti)

F1 rata-rata dengan SatuaNER M2 pada ambang 0,85 (Tabel 4.36–4.37). Ambang dapat diatur antara 0,50 dan 1,00.

| `id` | Metode | F1 |
|---|---|---|
| `jaro-distance` (bawaan) | Jaro distance | 0,7172 |
| `sorensen-dice` | Sørensen–Dice | 0,7159 |
| `jaro-winkler` | Jaro–Winkler | 0,7097 |
| `ratcliff` | Ratcliff/Obershelp | 0,7076 |
| `jaccard` | Jaccard | 0,7026 |

### 1.4 Classifier peran (Mode Peneliti)

Katalog statis [`model_catalog.py`](src/apps/analysis/services/model_catalog.py) memuat **72 konfigurasi** dari eksperimen tesis (Bab 3.6, Tabel 3.10–3.12, Subbab 4.6). **24 tersedia** di v1.0 (semua konfigurasi word vector); 48 konfigurasi leksikon tampil "segera hadir".

| Dimensi | Pilihan |
|---|---|
| Varian | **M1**: konfigurasi optimal dilatih pada fold latih dengan F1 validasi tertinggi. **M2**: konfigurasi optimal dilatih pada seluruh data latih |
| Fitur word vector (tersedia) | **TF4** TF-IDF; **TF5** rata-rata word embedding FastText bahasa Bali 300 dimensi; **TF4+TF5** (M1) |
| Fitur leksikon (belum tersedia) | TF1 fitur leksikon dasar BaliSentiLex, TF2 fitur leksikon tambahan, TF3 fitur POS tag, dan kombinasinya. Pickle-nya merujuk modul ekstraktor lama, sehingga belum bisa dimuat |
| Algoritma | K-Nearest Neighbor, Decision Tree, Support Vector Machine, Gaussian Naive Bayes, Random Forest, Multilayer Perceptron (scikit-learn 1.2.1) |

Fitur word vector terbaik per algoritma, beserta dua F1 referensi yang juga ditampilkan di aplikasi. F1 CV dari Tabel 4.57 (sama untuk M1 dan M2); F1 uji M1 dari Lampiran 15; F1 uji M2 dari Tabel 4.60. Konfigurasi M1 lain memakai F1 CV dari Lampiran 17 dan F1 uji "–" karena tesis tidak mengujinya.

| Algoritma | Fitur | F1 CV | F1 uji M1 | F1 uji M2 | Keterangan |
|---|---|---|---|---|---|
| SVM | TF5 | **0,6811** | 0,6366 | 0,6460 | **Terbaik menurut tesis** (`m2-wordvector-tf5-svm`) |
| Random Forest | TF5 | 0,6775 | 0,6270 | 0,6273 | |
| KNN | TF4 | 0,6666 | 0,6369 | 0,6451 | **Bawaan aplikasi** (`m2-wordvector-tf4-knn`) |
| MLP | TF5 | 0,6447 | 0,6121 | 0,6596 | |
| Gaussian NB | TF5 | 0,6190 | 0,5819 | 0,5932 | |
| Decision Tree | TF4 | 0,6133 | 0,6188 | 0,6366 | |

Pembanding rule-based BaliSentiLex: F1 CV 0,5395, F1 uji 0,5148. Bawaan aplikasi dipilih pengembang karena pada uji coba beberapa satua KNN + TF4 memberi hasil peran yang lebih baik, dan model ini tidak memerlukan FastText (RAM lebih kecil, start lebih cepat).

### 1.5 File model yang dipakai

Pickle classifier tidak disimpan di git. Bundelnya (`prasibali-models-v1.0.tar.gz`, 30 MB, berisi `SHA256SUMS`) dilampirkan pada rilis `v1.0-submission`. Hash pendek setiap file juga tercatat di `model_version` setiap analisis.

| File (relatif terhadap `PRETRAINED_MODELS_DIR`) | Ukuran | SHA-256 (12 karakter) |
|---|---|---|
| `character-classification/wordvector/m1/TF4_pretrained_baseline_m1.pkl` | 48,7 MB | `dffe459253e7` |
| `character-classification/wordvector/m1/TF5_pretrained_baseline_m1.pkl` | 2,9 MB | `ce4ab89d6b01` |
| `character-classification/wordvector/m1/TF4_TF5_pretrained_baseline_m1.pkl` | 47,3 MB | `6bd39719ce6d` |
| `character-classification/wordvector/m2/knn_pretrained_model.pkl` | 38,3 MB | `0eb3c4e2a272` |
| `character-classification/wordvector/m2/svm_pretrained_model.pkl` | 1,0 MB | `f59d8d88feef` |
| `character-classification/wordvector/m2/rf_pretrained_model.pkl` | 0,7 MB | `28b562e727eb` |
| `character-classification/wordvector/m2/mlp_pretrained_model.pkl` | 0,4 MB | `18b36c3f2530` |
| `character-classification/wordvector/m2/dt_pretrained_model.pkl` | 0,2 MB | `cd8b5d6a62c2` |
| `character-classification/wordvector/m2/gnb_pretrained_model.pkl` | 12 KB | `baa2f6f674e6` |
| `label-encoder/without_coreference_splitted_characterization.pkl` | 2,4 MB | `57cb2878d6a9` |

Model NER (`satuaner.pkl`, `crf1_baseline.pkl`, `crf2_baseline.pkl`, `svm_baseline.pkl`, `hmm.pkl`) sudah termasuk di paket `balinese-nlp` 2.4.2.

**Word embedding FastText (TF5).** `300_fasttext_model.bin` beserta file `.npy`-nya (sekitar 2,4 GB) dari repo Hugging Face [`satriabimantara/balinese_pretrained_wordembedding`](https://huggingface.co/satriabimantara/balinese_pretrained_wordembedding), milik pengembang, lisensi BSD-3-Clause, yang sama dengan embedding saat melatih pickle TF5. File diunduh **sekali** lewat `BaliFastText` ke cache persisten (`HF_HOME`), lalu produksi berjalan dengan `HF_HUB_OFFLINE=1`. Dimensinya (300) dicek terhadap `n_features_in_` estimator sebelum dipakai. Hanya file model yang diunduh; tidak ada teks pengguna yang dikirim.

### 1.6 API AI pihak ketiga

**Tidak ada.** PrasiBali tidak memanggil LLM, API generative AI, atau layanan inferensi eksternal apa pun. Semua inferensi berjalan di proses Django di server sendiri, sehingga teks satua pengguna tidak pernah meninggalkan server PrasiBali.

### 1.7 Pengamanan dan keandalan

| Aspek | Penerapan |
|---|---|
| Whitelist model | Pilihan pengguna hanya berupa `id` katalog yang divalidasi di server. Path file tidak pernah berasal dari input, karena memuat pickle bisa menjalankan kode |
| Pemuatan | *Lazy* dengan `lru_cache` dan batas jumlah bundle (`ANALYSIS_CLASSIFIER_CACHE_SIZE`); model bawaan dan FastText dipanaskan saat start (`warm_models`) |
| Validasi fitur | Jumlah fitur dicek terhadap `n_features_in_` estimator sebelum prediksi |
| Determinisme | Nama tokoh diurutkan sebelum alias clustering agar teks yang sama selalu memberi kelompok yang sama |
| Penanganan error | Exception khusus per tahap (praproses, identifikasi, alias, peran) dengan pesan ramah; status gagal tercatat dan tidak mengurangi kuota; aplikasi tetap menyala bila folder model tidak ada |
| Jejak audit | Setiap `AnalysisRun` menyimpan konfigurasi lengkap dan `model_version`: versi `balinese-nlp` dan scikit-learn, model NER, metode dan ambang alias, `id` classifier, hash SHA-256 pickle dan label encoder, serta identitas embedding bila memakai TF5 |
| Penyalahgunaan | Login dengan email terverifikasi, kuota 10 analisis per hari, batas 20.000 karakter, rate limit login dari django-allauth |

## 2. Peran AI dalam produk

AI adalah fungsi utama PrasiBali, bukan fitur tambahan. Tanpa ketiga model, produk ini tidak menghasilkan apa pun.

| | |
|---|---|
| **Yang dikerjakan AI** | Menemukan setiap sebutan tokoh dan jenis entitasnya; mengelompokkan sebutan yang merujuk ke tokoh yang sama; memberi label protagonis/antagonis pada setiap kelompok berdasarkan kalimat konteksnya |
| **Yang tidak dikerjakan AI** | Tidak membuat teks baru, tidak meringkas, tidak menerjemahkan, dan tidak mengambil keputusan atas nama pengguna |
| **Input** | Teks satua berbahasa Bali dalam huruf Latin, maksimal 20.000 karakter, ditambah pilihan tugas dan (di Mode Peneliti) `id` model |
| **Output** | Teks dengan nama tokoh disorot dan berlabel entitas, kartu kelompok alias, label peran per kelompok, skor model mentah di Mode Peneliti, waktu proses per tahap |
| **Transparansi** | Setiap pilihan model menampilkan F1 referensi tesis dan rujukan tabelnya. Untuk SVM yang ditampilkan adalah `decision_function` (jarak ke hyperplane), tidak pernah disebut probabilitas atau "keyakinan" |
| **Batasan dan disclaimer** | Kartu peran memuat disclaimer bahwa label adalah alat bantu analisis dan F1 rata-rata model di tesis di bawah 0,70. Kelompok dengan konteks kurang dari 20 kata (atau tanpa term TF-IDF yang dikenal) diberi peringatan "konteks sedikit" |
| **Peran manusia** | Pengguna (guru, siswa, peneliti) tetap menjadi penafsir akhir. Hasil dimaksudkan sebagai pembacaan awal |

## 3. Dataset dan sumber data

| Data | Keterangan | Lisensi |
|---|---|---|
| **Balinese Story Texts Dataset: Characters, Aliases, and their Classification** (versi 3) | 120 teks satua Bali yang dianotasi untuk identifikasi tokoh, alias clustering, dan klasifikasi protagonis/antagonis oleh dua penutur asli bahasa Bali. Teks bersumber dari buku *Kumpulan Satua (Dongeng Rakyat Bali)* (Suwija dkk., 2019). Dipakai untuk melatih dan mengevaluasi semua model di tesis. <https://data.mendeley.com/datasets/h2tf5ymcp9/3> · DOI [10.17632/h2tf5ymcp9.3](https://doi.org/10.17632/h2tf5ymcp9.3) | CC BY 4.0 |
| Artikel data: *Balinese Story Texts Dataset for Narrative Text Analyses* | Bimantara, Purwitasari, Sanjaya ER, & Natha, *Data in Brief* 56 (2024) 110781. DOI [10.1016/j.dib.2024.110781](https://doi.org/10.1016/j.dib.2024.110781) | Artikel akses terbuka Elsevier |
| BaliSentiLex | Leksikon sentimen bahasa Bali yang dikembangkan dalam tesis (Subbab 3.7), dasar fitur TF1–TF2. Belum dipakai di v1.0 | Karya pengembang |
| Dua teks contoh satua di [`src/apps/analysis/data/sample_satua/`](src/apps/analysis/data/sample_satua/) | Teks pendek baru untuk tombol "Coba contoh satua", warm-up model, dan test. **Disusun dengan bantuan Claude** dari pola bahasa satua, bukan salinan teks dataset, agar dataset riset tidak ikut dipublikasikan di repo | Bagian dari repo (BSD-3-Clause) |
| Data pengguna | Akun, teks yang dianalisis, dan hasilnya disimpan di PostgreSQL milik PrasiBali. Tidak dikirim ke pihak ketiga, tidak dipakai untuk melatih model, dan bisa dihapus pengguna (hapus riwayat satu per satu, semua riwayat, atau akun). Lihat halaman Kebijakan Privasi di aplikasi | - |

## 4. Framework, runtime, database, dan hosting

| Komponen | Versi | Fungsi | Lisensi |
|---|---|---|---|
| Python | 3.11 | Bahasa pemrograman backend dan AI | PSF License |
| Django | 5.2 LTS | Framework web: ORM, auth, admin, CSRF, i18n | BSD-3-Clause |
| django-allauth | 65.21 | Registrasi, verifikasi email, login, reset password, rate limit | MIT |
| django-environ | 0.14 | Konfigurasi dari `.env` | MIT |
| Django Templates + gettext | - | Render HTML di server; antarmuka Indonesia dan Inggris | BSD-3-Clause |
| Tailwind CSS | 4.3.3 (standalone CLI) | Styling; CSS hasil build di-commit, tanpa Node.js | MIT |
| HTMX | 2.0.4 (disajikan lokal) | Pengiriman analisis dan hasil bertahap tanpa muat ulang halaman | 0BSD |
| Alpine.js | 3.14.8 (disajikan lokal) | Interaksi kecil: panel Mode Peneliti, menu, tema | MIT |
| Gunicorn | 23 | WSGI server produksi (worker sync, `--preload`) | MIT |
| WhiteNoise | 6.12 | Menyajikan file statis dari container | MIT |
| PostgreSQL | 16 (`postgres:16-alpine`) | Database akun, riwayat (`AnalysisRun` dengan kolom JSON), kuota harian, cache | PostgreSQL License |
| psycopg | 3.3 | Driver PostgreSQL | LGPL-3.0 |
| Caddy | 2.10 (`caddy:2.10-alpine`) | Reverse proxy, HTTPS otomatis, header keamanan | Apache-2.0 |
| Let's Encrypt | - | Sertifikat TLS untuk `prasibali.tech` | Layanan gratis (ISRG) |
| Docker Engine + Compose | - | Container lokal dan produksi (`docker-compose.yml`, `docker-compose.prod.yml`) | Apache-2.0 |
| Image dasar | `python:3.11-slim` | Basis image aplikasi (multi-stage, user non-root) | PSF / Debian |
| Hostinger VPS KVM 1 | Ubuntu, 1 vCPU, 4 GB RAM | Hosting produksi | Layanan berbayar |
| Domain `prasibali.tech` | - | Alamat publik, DNS di hPanel Hostinger | Layanan Hostinger |
| Hostinger Email (SMTP) | `smtp.hostinger.com:587` STARTTLS | Email verifikasi dan reset password dari `noreply@prasibali.tech` | Layanan Hostinger |
| GitHub + GitHub Actions | - | Repositori dan CI (ruff + pytest dengan PostgreSQL) | Layanan GitHub |

## 5. Library open-source

Versi AI/NLP dipin persis di [`requirements.txt`](requirements.txt) agar pickle tesis (dibuat dengan scikit-learn 1.2.1) dapat dimuat dan hasilnya sama.

**AI / NLP**

| Paket | Versi | Fungsi di PrasiBali | Lisensi |
|---|---|---|---|
| `balinese-nlp` | 2.4.2 | SatuaNER dan model NER lain, alias clustering, praproses, POS tagger, pengelompokan kalimat, ekstraktor fitur, pemuat FastText (karya pengembang) | BSD-3-Clause |
| scikit-learn | 1.2.1 | Estimator classifier, TF-IDF, label encoder | BSD-3-Clause |
| sklearn-crfsuite | 0.3.6 | Antarmuka CRF untuk SatuaNER | MIT |
| python-crfsuite | 0.9.10 | Implementasi CRFsuite | MIT |
| gensim | 4.3.3 | Memuat model FastText | LGPL-2.1 |
| hmmlearn | 0.3.0 | Dependensi POS tagger / model HMM | BSD-3-Clause |
| PyTorch (CPU) | 2.3.0 | Dependensi `balinese-nlp` | BSD-3-Clause |
| Transformers | 4.33.3 | Dependensi `balinese-nlp` | Apache-2.0 |
| tokenizers | 0.13.3 | Dependensi Transformers | Apache-2.0 |
| huggingface-hub | 0.33.0 | Mengunduh embedding FastText dari Hugging Face | Apache-2.0 |
| pandas | 1.5.3 | Struktur data pengelompokan kalimat dan fitur | BSD-3-Clause |
| NumPy | 1.24.4 | Komputasi numerik | BSD-3-Clause |
| SciPy | 1.10.1 | Dependensi scikit-learn | BSD-3-Clause |
| openpyxl | 3.1.5 | Dependensi `balinese-nlp` (membaca kamus praproses) | MIT |
| NLTK | 3.10 | Dependensi turunan `balinese-nlp` | Apache-2.0 |
| matplotlib | 3.6.3 | Dependensi turunan `balinese-nlp` (tidak dipakai untuk render) | Matplotlib License (PSF-based) |
| statsmodels | 0.14.1 | Dependensi turunan `balinese-nlp` | BSD-3-Clause |
| jaro-winkler | 2.0.3 | Dependensi turunan `balinese-nlp` (metode kemiripan string) | GPL-3.0 |
| krippendorff | 0.6.0 | Dependensi turunan `balinese-nlp` (evaluasi anotasi; tidak dipanggil aplikasi) | GPL-3.0-or-later |

**Web dan API**

| Paket | Versi | Fungsi | Lisensi |
|---|---|---|---|
| Django REST Framework | 3.18 | Tercantum di `requirements.txt` untuk REST API yang direncanakan; belum dipakai di v1.0 | BSD-3-Clause |
| drf-spectacular | 0.30 | Dokumentasi OpenAPI untuk REST API yang direncanakan; belum dipakai di v1.0 | BSD-3-Clause |

Paket lain di tabel §4 (Django, django-allauth, django-environ, psycopg, WhiteNoise, Gunicorn) juga termasuk library open-source.

**Development (tidak dipasang di produksi, [`requirements-dev.txt`](requirements-dev.txt))**

| Paket | Fungsi | Lisensi |
|---|---|---|
| pytest, pytest-django, pytest-cov | Test otomatis (244 test) | MIT / BSD-3-Clause / MIT |
| ruff | Linter | MIT |
| pre-commit | Hook kualitas kode | MIT |
| ipykernel | Notebook uji model | BSD-3-Clause |

Catatan lisensi copyleft: gensim (LGPL-2.1), psycopg (LGPL-3.0), jaro-winkler (GPL-3.0), dan krippendorff (GPL-3.0+) dipakai sebagai paket terpasang dari PyPI. Kodenya tidak disalin atau dimodifikasi di repo ini.

## 6. Template dan boilerplate

| Bagian | Keterangan |
|---|---|
| Struktur proyek | Dibuat dari `django-admin startproject` (bawaan Django), lalu disusun ulang menjadi `config/` dan `apps/` |
| Template autentikasi | Template bawaan django-allauth ditimpa dengan template sendiri di `src/templates/account/` dan `src/templates/allauth/` |
| UI | Tidak memakai UI kit, tema, atau template pihak ketiga. Sistem desain "Endek Indigo" ditulis sendiri di [`DESIGN.md`](DESIGN.md) dan diterapkan dengan Tailwind |
| Starter kit / SaaS boilerplate | Tidak ada |

## 7. AI coding assistant

| Alat | Penyedia | Dipakai untuk |
|---|---|---|
| **Claude Code** (CLI dan ekstensi IDE; model Claude Opus) | Anthropic | Menulis dan merefaktor kode Django, layanan pipeline, test pytest, Dockerfile dan skrip deploy, terjemahan, `DESIGN.md`, dokumentasi (termasuk README dan dokumen ini), dan dua teks contoh satua |
| **Claude.ai** (chat dan Project) | Anthropic | Perencanaan sesi kerja, penyusunan konteks proyek dan aturan kerja (`CLAUDE.md`) |

Logo PrasiBali dibuat bersama Claude sebagai vektor SVG (lihat §9).

Batas penggunaan:

- Claude **tidak** dipakai di dalam produk. Tidak ada panggilan ke API Anthropic atau LLM lain saat aplikasi berjalan.
- Model AI produk (NER, alias clustering, classifier, embedding) dan dataset adalah hasil riset pengembang sebelum kompetisi, bukan buatan AI coding assistant.
- Keputusan arsitektur, pemilihan model, angka F1 referensi (dibaca dari buku tesis), dan konfigurasi produksi ditentukan dan diperiksa pengembang. Semua kode ditinjau dan diuji (244 test, ruff, CI), dan tim bertanggung jawab penuh atas source code yang disubmit.

## 8. Komponen pra-kompetisi

| Sudah ada sebelum kompetisi | Pemilik | Status di PrasiBali |
|---|---|---|
| Tesis S2 *Identifikasi Tokoh dan Penokohan pada Teks Cerita Berbahasa Bali Menggunakan Pendekatan Berbasis Aturan dan Supervised Machine Learning* (ITS, 2024) | I Made Satria Bimantara | Sumber semua metode, eksperimen, dan F1 referensi |
| SatuaNER dan model NER pembanding; alias clustering berbasis aturan | Pengembang (publikasi iiWAS 2023) | Dipakai lewat paket `balinese-nlp` 2.4.2, tidak diubah |
| Paket PyPI [`balinese-nlp`](https://pypi.org/project/balinese-nlp/2.4.2/) 2.4.2 | Pengembang | Dependensi; tidak ada kode paket yang disalin ke repo |
| Pickle classifier peran (semua eksperimen leksikon dan word vector, varian M1 dan M2) dan label encoder | Pengembang | Dimuat apa adanya; tidak dilatih ulang |
| Embedding FastText bahasa Bali di Hugging Face | Pengembang | Fitur TF5 |
| Balinese Story Texts Dataset (Mendeley Data, *Data in Brief*) dan BaliSentiLex | Pengembang dan rekan penulis | Data latih model; tidak disertakan di repo |
| Repositori riset [BaliStoryAnalyzer](https://github.com/satriabimantara/balinese_storyanalyzer) dan paket `balistoryanalyzer` | Pengembang | Hanya dirujuk; tidak diubah dan tidak dipakai sebagai dependensi |
| Aplikasi web lama **BaliNarrativeNLP** (Django) | Pengembang | Hanya rujukan: perilaku praproses konteks klasifikasi mengikuti aplikasi lama agar hasil model sama. Kodenya tidak dipakai di repo ini |

| Dibangun atau ditingkatkan untuk kompetisi (repo ini, 2–4 November 2026) |
|---|
| Aplikasi web PrasiBali dari nol: akun dengan verifikasi email, ruang kerja analisis, hasil bertahap dengan HTMX, riwayat, kuota, dwibahasa, tema terang/gelap |
| Layanan AI aplikasi: katalog model dengan whitelist, registry model dengan cache, adaptor ekstraksi fitur (TF4, TF5, TF4+TF5), pemuat FastText lokal/Hugging Face, pencatatan `model_version` |
| Mode Peneliti dengan 5 model NER, 5 metode alias, dan 24 konfigurasi classifier beserta F1 referensi tesis |
| Perbaikan terhadap paket: urutan alias clustering yang deterministik, cache POS tagger (analisis satua contoh dari sekitar 2,7 detik menjadi 0,03 detik), penanganan folder kerja `saved_file` agar aman di container non-root |
| Identitas visual (logo, sistem desain, pola ikat), halaman beranda, fitur, tentang, dan privasi |
| Infrastruktur produksi: Docker multi-stage, Caddy, backup harian, deploy lewat `git push`, header keamanan, logging JSON, health check |
| 244 test otomatis dan GitHub Actions CI |

## 9. Aset pihak ketiga dan kredit

| Aset | Sumber | Lisensi |
|---|---|---|
| Font **Schibsted Grotesk** (teks antarmuka) | Google Fonts | SIL Open Font License 1.1 |
| Font **Noto Serif Balinese** (aksara Bali di beranda) | Google Fonts | SIL Open Font License 1.1 |
| Font Plus Jakarta Sans dan Noto Sans Balinese (di dalam logo, sudah diubah menjadi outline) | Google Fonts | SIL Open Font License 1.1 |
| Ikon garis (SVG inline) | [Lucide](https://lucide.dev) | ISC |
| Logo PrasiBali dan ikon aplikasi ([`assets/PrasiBali-Logo/`](assets/PrasiBali-Logo/)) | Dibuat untuk PrasiBali bersama Claude (Anthropic) sebagai vektor SVG | Milik pengembang |
| Pola pita ikat ([`scripts/generate_ikat.py`](scripts/generate_ikat.py)) | Pola geometris generik yang dibangkitkan skrip, terinspirasi teknik ikat, bukan replika motif endek tertentu | Milik pengembang |
| Tangkapan layar di [`screenshots/`](screenshots/) | Diambil dari aplikasi PrasiBali | Milik pengembang |
| Sertifikat TLS | Let's Encrypt | Layanan gratis (ISRG) |

Font dimuat dari Google Fonts; semua script dan ikon disajikan dari server PrasiBali sendiri, tanpa CDN pihak ketiga.

---

**Pernyataan:** Kami menyatakan bahwa informasi di atas benar dan lengkap. Kami bertanggung jawab atas penggunaan teknologi, source code, data, library, API, model AI, dan aset yang digunakan pada produk.

I Made Satria Bimantara, S.Kom., M.Kom. (Ketua Tim) · Dr. Ir. Ngurah Agus Sanjaya ER, S.Kom., M.Kom. · Prof. Dr. Ir. Diana Purwitasari, S.Kom., M.Sc.

4 November 2026
