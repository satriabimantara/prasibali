# Deploy PrasiBali.ai ke VPS (Ubuntu 24.04)

Panduan langkah demi langkah untuk menjalankan PrasiBali.ai di VPS 8 GB RAM / 4 vCPU (Contabo Cloud VPS 10, Singapura) dengan domain `prasibali.ai`. Semua layanan berjalan dengan Docker Compose (`docker-compose.prod.yml`):

| Layanan | Image | Fungsi |
|---|---|---|
| `caddy` | `caddy:2.10-alpine` | HTTPS otomatis (Let's Encrypt) untuk `prasibali.ai` dan `www.prasibali.ai` (dialihkan 301 ke apex), reverse proxy ke Gunicorn |
| `web` | dibangun dari `docker/Dockerfile` (stage `runtime`) | Django + Gunicorn (worker sync, `--preload`), user non-root `app` (uid 1000) |
| `db` | `postgres:16-alpine` | Database, volume `pgdata` |
| `backup` | `postgres:16-alpine` | `pg_dump` harian ke `./backups/` |

Perintah yang diawali `$` dijalankan di VPS sebagai user `deploy`. Perintah yang diawali `PS>` dijalankan di laptop Windows (PowerShell).

## 1. Prasyarat

- Domain `prasibali.ai` (Cloudflare Registrar) dan VPS Ubuntu 24.04 dengan IP publik.
- Kunci SSH ed25519 di laptop (`PS> ssh-keygen -t ed25519` bila belum ada).
- Folder `models/` di laptop (isi `pretrained-models`, tidak ada di git).
- Kredensial yang disiapkan sendiri dan **tidak pernah** ditempel ke repo atau ke Claude Code: `DJANGO_SECRET_KEY`, password Postgres, App Password Gmail, password akun demo, dan `HF_TOKEN` (hanya bila repo embedding privat).

## 2. Siapkan server

Masuk sebagai root sekali, buat user `deploy`, lalu pasang kunci SSH:

```bash
ssh root@IP_VPS
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy                                    # password untuk sudo
mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
```

Matikan login root dan login dengan password (`/etc/ssh/sshd_config`: `PermitRootLogin no`, `PasswordAuthentication no`), lalu `systemctl restart ssh`. Uji `ssh deploy@IP_VPS` dari terminal lain sebelum menutup sesi root.

Firewall:

```bash
$ sudo ufw allow OpenSSH
$ sudo ufw allow 80/tcp
$ sudo ufw allow 443/tcp
$ sudo ufw allow 443/udp      # HTTP/3
$ sudo ufw enable
```

Catatan: Docker menulis aturan iptables sendiri untuk port yang dipublikasikan. Hanya `caddy` yang mempublikasikan port (80/443); `web` dan `db` tidak punya port publik.

Pasang Docker Engine dan plugin Compose dari repositori resmi Docker:

```bash
$ sudo apt-get update && sudo apt-get install -y ca-certificates curl git
$ sudo install -m 0755 -d /etc/apt/keyrings
$ sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
$ sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
$ sudo usermod -aG docker deploy && newgrp docker
$ docker compose version
```

Tambahkan swap 2 GB sebagai pengaman saat build image (pip memasang torch):

```bash
$ sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
$ echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. Ambil kode

```bash
$ git clone https://github.com/satriabimantara/prasibali.ai.git ~/prasibali
$ cd ~/prasibali
$ mkdir -p models backups
```

(Selama repo masih privat, pakai deploy key atau `gh auth login` di VPS.)

## 4. Salin folder model dari laptop

Folder `models/` di laptop berisi `character-classification/`, `label-encoder/`, `balisentilex/`, dan `balinese-word-embedding/`. Di server, folder ini menjadi `~/prasibali/models/` dan di-mount read-only ke `/app/models` (`PRETRAINED_MODELS_DIR=/app/models`).

Dari PowerShell di akar repo laptop (OpenSSH bawaan Windows):

```powershell
PS> scp -r models\character-classification models\label-encoder models\balisentilex deploy@IP_VPS:~/prasibali/models/
PS> ssh deploy@IP_VPS "mkdir -p ~/prasibali/models/balinese-word-embedding"
PS> scp models\balinese-word-embedding\300_fasttext_model.bin models\balinese-word-embedding\300_fasttext_model.bin.wv.vectors_ngrams.npy deploy@IP_VPS:~/prasibali/models/balinese-word-embedding/
```

File `100_*` di `balinese-word-embedding/` tidak dipakai aplikasi (TF5 memakai FastText 300 dimensi) dan tidak perlu disalin, sehingga transfer berkurang sekitar 0,8 GB. Jika WSL atau Git Bash tersedia, `rsync -avP --exclude '100_*' models/ deploy@IP_VPS:~/prasibali/models/` bisa melanjutkan transfer yang terputus.

Periksa hasilnya di server:

```bash
$ du -sh ~/prasibali/models/*
$ sha256sum ~/prasibali/models/balinese-word-embedding/300_fasttext_model.bin*
```

Bandingkan hash dengan laptop (`PS> Get-FileHash models\balinese-word-embedding\300_fasttext_model.bin*`). Pastikan user uid 1000 di container bisa membaca file: `chmod -R a+rX ~/prasibali/models`.

Jika `balinese-word-embedding/300_fasttext_model.bin` tidak disalin, `warm_models` mengunduhnya sekali dari Hugging Face (`satriabimantara/balinese_pretrained_wordembedding`) ke volume `hf_cache`.

## 5. Isi `.env`

Buat `~/prasibali/.env` (`chmod 600 .env`). Nilai tidak pernah di-commit. Variabel yang dipakai produksi:

| Variabel | Isi |
|---|---|
| `DJANGO_SECRET_KEY` | string acak panjang (`python3 -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_ALLOWED_HOSTS` | `prasibali.ai,www.prasibali.ai` |
| `CSRF_TRUSTED_ORIGINS` | `https://prasibali.ai,https://www.prasibali.ai` |
| `SITE_DOMAIN` | `prasibali.ai` (Caddy juga melayani `www.` dan mengalihkannya) |
| `ACME_EMAIL` | email untuk pemberitahuan Let's Encrypt |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | database produksi |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Gmail SMTP dengan App Password |
| `DEMO_USER_EMAIL`, `DEMO_USER_PASSWORD` | akun demo juri (langkah 8) |
| `GUNICORN_WORKERS` | jumlah worker (bawaan `3`; hitung dengan tabel di bagian "Memori dan jumlah worker") |
| `WEB_MEM_LIMIT` | batas memori container `web` (bawaan `6g`) |
| `BACKUP_KEEP_DAYS`, `BACKUP_AT` | retensi backup (bawaan `14` hari) dan jam backup harian (bawaan `02:00` WITA) |
| `ANALYSIS_DAILY_QUOTA` | kuota analisis harian per pengguna (bawaan `10`) |
| `TF5_HF_REPO_ID`, `TF5_FASTTEXT_FILENAME` | kosongkan untuk bawaan (`300_fasttext_model.bin`) |
| `HF_TOKEN` | hanya bila repo embedding privat |
| `DJANGO_LOG_LEVEL` | bawaan `INFO` |

`DATABASE_URL`, `PRETRAINED_MODELS_DIR`, `HF_HOME`, `BALINESE_NLP_WORK_DIR`, dan `ANALYSIS_WARM_ON_START` diisi oleh `docker-compose.prod.yml`. `HF_HUB_OFFLINE=1` dipasang otomatis oleh `docker/entrypoint.sh` setelah `warm_models` berhasil.

> Untuk pengembang: salin nama-nama variabel baru di tabel ini (tanpa nilai) ke `.env.example`. File itu tidak bisa diubah oleh Claude Code karena aturan izin.

## 6. DNS

Di Cloudflare DNS buat dua record A ke IP VPS, status **DNS only** (awan abu-abu) agar Caddy bisa menyelesaikan tantangan Let's Encrypt:

| Tipe | Nama | Isi |
|---|---|---|
| A | `@` | IP_VPS |
| A | `www` | IP_VPS |

Cek dengan `dig +short prasibali.ai` dan `dig +short www.prasibali.ai`.

## 7. Jalankan

```bash
$ cd ~/prasibali
$ docker compose -f docker-compose.prod.yml config --quiet      # validasi .env dan file compose
$ docker compose -f docker-compose.prod.yml up -d --build
$ docker compose -f docker-compose.prod.yml logs -f web
```

Urutan start container `web` (`docker/entrypoint.sh`): `migrate` → `createcachetable` → `warm_models` (SatuaNER, label encoder, classifier bawaan, FastText 300, satu analisis pendek) → `HF_HUB_OFFLINE=1` → Gunicorn (`src/config/gunicorn.conf.py`) dengan `--preload`, sehingga model dimuat sekali di master lalu dibagi ke worker. Healthcheck memberi waktu start 5 menit. Jika `warm_models` gagal, server tetap menyala dan tahap analisis yang terdampak menampilkan pesan ramah.

Pemeriksaan:

```bash
$ docker compose -f docker-compose.prod.yml ps                          # web "healthy"
$ curl -sI https://prasibali.ai/ | grep -iE "strict-transport|content-security|x-frame"
$ curl -sI https://www.prasibali.ai/ | head -n 3                        # 301 ke https://prasibali.ai/
$ curl -s https://prasibali.ai/healthz                                   # {"status": "ok", "database": "ok"}
```

Log semua layanan berbentuk JSON satu baris per event (`docker compose ... logs web | jq .` bila `jq` terpasang). Teks satua tidak pernah dicatat.

## 8. Akun demo juri

```bash
$ docker compose -f docker-compose.prod.yml exec web python manage.py create_demo_user
```

Perintah ini membaca `DEMO_USER_EMAIL` dan `DEMO_USER_PASSWORD` dari `.env`, membuat atau memperbarui akun dengan email terverifikasi, dan tidak pernah mencetak password. Jalankan ulang setelah mengganti password di `.env` (lalu `up -d` agar container membaca `.env` baru). Kredensial dikirim ke panitia lewat formulir resmi, tidak lewat repo.

Superuser untuk `/admin/` (opsional): `docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser`.

## 9. Backup dan restore

Layanan `backup` membuat `./backups/prasibali-YYYYmmdd-HHMM.dump` (format custom `pg_dump -Fc`) setiap hari pada `BACKUP_AT` dan menghapus dump yang lebih tua dari `BACKUP_KEEP_DAYS`.

```bash
$ docker compose -f docker-compose.prod.yml exec backup sh /usr/local/bin/backup.sh now    # backup sekarang
$ ls -lh backups/
$ docker compose -f docker-compose.prod.yml logs backup
```

Salin backup ke luar server secara berkala, misalnya dari laptop: `PS> scp deploy@IP_VPS:~/prasibali/backups/prasibali-*.dump .\backups\`.

Restore (menimpa isi database):

```bash
$ docker compose -f docker-compose.prod.yml stop web
$ docker compose -f docker-compose.prod.yml exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/prasibali-YYYYmmdd-HHMM.dump
$ docker compose -f docker-compose.prod.yml start web
```

## 10. Pembaruan aplikasi

```bash
$ cd ~/prasibali && git pull
$ docker compose -f docker-compose.prod.yml up -d --build web
$ docker image prune -f
```

Migrasi dijalankan otomatis oleh entrypoint. Model tidak diunduh ulang (folder `models/` dan volume `hf_cache` tetap).

## 11. Rencana cadangan

- **Domain belum aktif:** isi `SITE_DOMAIN=IP-VPS-dengan-tanda-hubung.sslip.io` (misalnya `203-0-113-5.sslip.io`), sesuaikan `DJANGO_ALLOWED_HOSTS` dan `CSRF_TRUSTED_ORIGINS`, lalu `up -d`. Caddy mengambil sertifikat untuk alamat itu.
- **Email verifikasi gagal:** periksa App Password Gmail dan log `web`. Sebagai jalan darurat sementara, verifikasi bisa diubah menjadi `optional` (keputusan pengembang, bagian 10 konteks proyek).
- **Memori kurang:** turunkan `GUNICORN_WORKERS` (lihat bagian berikut).
- **VPS bermasalah:** langkah yang sama berlaku di VPS lain; salin `models/`, `.env`, dan backup terakhir.

## Model dan file

| Apa | Lokasi | Ukuran |
|---|---|---|
| Pickle classifier tesis + label encoder | `models/character-classification/`, `models/label-encoder/` | 159 MB + 5 MB |
| Leksikon BaliSentiLex | `models/balisentilex/` | 0,3 MB |
| FastText bahasa Bali 300 dimensi (fitur TF5) | `models/balinese-word-embedding/300_fasttext_model.bin` (14 MB) + `.wv.vectors_ngrams.npy` (2,4 GB) | 2,4 GB |
| SatuaNER dan model NER lain | di dalam paket `balinese-nlp` (image) | kecil |
| Image `prasibali-web` | Docker | sekitar 2,7 GB |

File embedding harus sama dengan yang dipakai melatih pickle TF5: semua estimator TF5 mengharapkan 300 fitur (`n_features_in_`), dan aplikasi menolak embedding dengan `vector_size` lain.

## Memori dan jumlah worker

**Uji penuh 3 November 2026.** Uji ini memakai image hasil `docker/Dockerfile` multi-stage apa adanya: kode, entrypoint, CMD Gunicorn, `collectstatic`, dan CSS hasil build di dalam image, tanpa kode yang di-mount. Image yang dipakai adalah build dari `docker compose up --build`; bedanya dengan image produksi hanya paket dev (pytest, ruff) yang tidak dimuat saat aplikasi berjalan.

Stack yang dijalankan adalah `docker-compose.prod.yml` (`web` + `db`) di Docker Desktop (Linux, WSL 2), dengan model asli di `./models` (FastText dari file lokal). CPU dan memori container dibatasi seperti paket VPS:

- angka per proses dibaca dari `/proc/<pid>/smaps_rollup` (PSS = memori yang dibagi rata antarproses);
- angka container dibaca dari cgroup (`memory.peak`, `memory.events`).

Beban yang dijalankan di setiap skenario:

- 6 analisis satua contoh dan 6 analisis satua terpanjang (16.876 karakter, "Bintang Lara"), masing-masing bergantian dengan model bawaan KNN + TF4 dan SVM + TF5;
- lalu 3 klien bersamaan, masing-masing 4 analisis satua terpanjang.

| Ukuran | KVM 1: 1 vCPU, `GUNICORN_WORKERS=2`, `WEB_MEM_LIMIT=3500m` | KVM 2: 2 vCPU, `GUNICORN_WORKERS=3`, `WEB_MEM_LIMIT=6g` |
|---|---|---|
| Siap melayani sejak `up` | 119 detik | 118 detik |
| `warm_models` (FastText lokal) | 48,5 detik (FastText 43,3 detik) | 44,7 detik (FastText 39,9 detik) |
| Container `web` setelah warm-up | sekitar 2,66 GB | sekitar 2,75 GB |
| Container `web` setelah 12 analisis | 2,86 GB | 2,98 GB |
| Puncak cgroup `web` (termasuk uji bersamaan) | **2.910 MB** | **3.022 MB** |
| Memori dibagi (model) per proses | sekitar 2.515 MB | sekitar 2.515 MB |
| Memori privat master / tiap worker | 139 MB / 114–117 MB | 138 MB / 114–116 MB |
| Postgres (puncak) | 83 MB | 82 MB |
| OOM kill / restart / health | 0 / 0 / healthy | 0 / 0 / healthy |
| Satua contoh, satu klien | 0,11–0,61 detik | serupa |
| Satua terpanjang, satu klien | 1,06–1,66 detik | serupa |
| Satua terpanjang, 3 klien bersamaan | 1,05–4,74 detik (12 analisis dalam 21 detik) | 1,63–2,61 detik (12 analisis dalam 11 detik) |

Juga diperiksa di uji ini: user non-root (uid 1000), manifest static whitenoise tanpa folder `src`, `HF_HUB_OFFLINE=1` dipasang entrypoint sebelum `exec gunicorn`, header CSP/HSTS/`X-Frame-Options: DENY`, dan halaman 404 khusus.

Kesimpulan:

- Sekitar 2,5 GB model (SatuaNER, classifier, label encoder, FastText 300) dimuat sekali di master lalu **dibagi** ke semua worker berkat `--preload`.
- Setiap worker hanya menambah sekitar **115 MB**, termasuk setelah memakai model TF5.
- `warm_models` dan master Gunicorn memuat model secara berurutan, sehingga puncak memori tidak berlipat.
- Caddy dan OS tidak diukur di laptop (TLS hanya berjalan di server). Perkiraannya sekitar 0,5 GB untuk Ubuntu minimal + Caddy.

**Rumus jumlah worker**

```
RAM untuk web    = RAM VPS − OS dan Caddy (sekitar 0,5 GB) − Postgres (0,1 GB) − cadangan (0,5 GB)
batas memori     = floor((RAM untuk web − 2,8 GB) / 0,12 GB) + 1
batas CPU        = jumlah vCPU + 1   (worker sync, analisis CPU-bound: lebih banyak worker tidak mempercepat)
GUNICORN_WORKERS = min(batas memori, batas CPU)
```

| VPS | RAM untuk web | Batas memori | Batas CPU | `GUNICORN_WORKERS` | `WEB_MEM_LIMIT` | Puncak terukur |
|---|---|---|---|---|---|---|
| 4 GB, 1 vCPU (Hostinger KVM 1) | 2,9 GB | 1–2 | 2 | 2 | `3500m` | 2,91 GB |
| 8 GB, 2 vCPU (Hostinger KVM 2) | 6,9 GB | 35 | 3 | 3 | `6g` | 3,02 GB |
| 8 GB, 4 vCPU (rencana awal) | 6,9 GB | 35 | 5 | 5 | `6g` | tidak diukur (sekitar 3,3 GB menurut rumus) |

Yang membatasi adalah CPU, bukan RAM, selama FastText dimuat sekali di master. Di KVM 1, `WEB_MEM_LIMIT=3500m` menyisakan sekitar 0,5 GB untuk OS, Caddy, dan Postgres, sehingga swap 4 GB tetap dianjurkan. VPS dengan RAM di bawah sekitar 3,5 GB tidak muat FastText.

Pantau setelah deploy: `docker stats --no-stream`, `free -h`, `cat /sys/fs/cgroup/memory.events` di container `web` (`oom_kill` harus 0), dan log `web` untuk `Killed` atau `WORKER TIMEOUT`. `ANALYSIS_CLASSIFIER_CACHE_SIZE` (bawaan 4) membatasi jumlah pickle classifier tambahan yang tetap dimuat setelah dipilih di Mode Peneliti. File M1 TF4 sekitar 48 MB per file, dan pemuatan setelah fork dihitung per worker, jadi di KVM 1 sisakan ruang untuk itu atau turunkan nilainya ke 2.

## Kecepatan analisis (model hangat, laptop pengembang)

| Teks | Token | Pipeline lengkap |
|---|---|---|
| Contoh satua (sekitar 2.000 karakter) | 340 | 0,03–0,06 detik |
| Satua terpanjang di dataset, "Bintang Lara" (17.000 karakter) | 2.852 | 1,2 detik (alias clustering 0,9 detik) |

Identifikasi tokoh dulu butuh sekitar 2,7 detik untuk 370 token karena balinese-nlp membuat POS tagger HMM baru untuk setiap token. Aplikasi kini memakai satu tagger bersama dengan cache per token (`services/postag_cache.py`); hasilnya identik (`tests/analysis/test_postag_cache.py`).

## Catatan operasional

- `BALINESE_NLP_WORK_DIR=/app/var`: folder tulis untuk `saved_file` dari `RuleBasedSentenceGrouping`; tidak ada yang ditulis per request.
- `HF_HOME` adalah volume `hf_cache`. `BaliFastText` tidak punya parameter revisi, jadi isi cache (atau file lokal di `models/`) yang mengunci versi embedding.
- Kuota harian (`ANALYSIS_DAILY_QUOTA`) dihitung di tabel `DailyUsage` per hari lokal Asia/Makassar; analisis gagal tidak dihitung, dan admin dapat menurunkan `used` di Django admin.
- Rate limit login/reset password allauth memakai cache database (`django_cache`) yang dibagi semua worker.
- Header keamanan (HSTS, CSP, X-Frame-Options, Referrer-Policy, COOP, Permissions-Policy, cookie Secure/HttpOnly) diatur di `src/config/settings/prod.py`.
