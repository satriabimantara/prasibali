# Deploy PrasiBali.ai ke Hostinger VPS KVM 1 / KVM 2 (Ubuntu 24.04 64 bit)

Panduan langkah demi langkah untuk menjalankan PrasiBali.ai di Hostinger VPS dengan domain `prasibali.id`. Semua layanan berjalan dengan Docker Compose (`docker-compose.prod.yml`), tanpa control panel. Penjelasan umum tentang arsitektur, backup, pembaruan, dan pengukuran memori ada di `docs/deploy.md`; dokumen ini berisi langkah khusus Hostinger.

| Spesifikasi | KVM 1 | KVM 2 |
|---|---|---|
| CPU (AMD EPYC) | 1 vCPU | 2 vCPU |
| RAM | 4 GB | 8 GB |
| Disk NVMe | 50 GB | 100 GB |
| Bandwidth | 4 TB | 8 TB |
| `GUNICORN_WORKERS` | `2` | `3` |
| `WEB_MEM_LIMIT` | `3500m` | `6g` |
| Swap | 4 GB | 2 GB |

Paket web hosting (shared) Hostinger tidak bisa dipakai, karena tidak mendukung Docker maupun model Python.

## Apakah KVM 1 cukup?

Ya, untuk akses juri dengan semua model termasuk TF5, asalkan **tanpa Coolify**. Angka berikut diukur di container Linux (`docs/deploy.md`, bagian "Memori dan jumlah worker"):

| Komponen | RAM terukur |
|---|---|
| Container `web`, 2 worker, setelah analisis KNN + TF4 dan SVM + TF5 | 2,8 GB (model 2,5 GB dibagi master dan worker; tiap worker sekitar 115 MB) |
| Postgres | paling banyak 120 MB |
| Caddy + Ubuntu minimal | sekitar 0,5 GB (perkiraan, tidak diukur) |
| **Total** | **sekitar 3,4 GB dari 4 GB** |

Konsekuensinya:

- Sisa RAM hanya sekitar 0,6 GB, jadi pakai swap 4 GB sebagai pengaman dan jangan menjalankan layanan lain di VPS ini.
- Dengan 1 vCPU, analisis berjalan bergantian: satua contoh 0,1–0,3 detik, satua terpanjang 1–2 detik. Ini cukup untuk beberapa juri, tapi lebih lambat bila banyak yang mengirim satua panjang bersamaan.
- Build image pertama di 1 vCPU lebih lama (sekitar 20–40 menit).
- Start container butuh sekitar 70 detik untuk memuat model.

**Coolify tidak disarankan di KVM 1.** Dokumentasi Coolify menyebut kebutuhan minimum 2 core CPU dan 2 GB RAM untuk Coolify sendiri. KVM 1 hanya punya 1 vCPU, dan RAM-nya sudah terpakai sekitar 3,4 GB oleh PrasiBali.ai. Coolify juga memasang proxy sendiri di port 80/443, sehingga bentrok dengan Caddy di `docker-compose.prod.yml` dan compose harus disesuaikan. Panduan ini memakai Docker Compose langsung: lebih ringan, sudah diuji, dan tetap mudah diperbarui (`git pull` lalu `up -d --build`).

**OS: pakai Ubuntu 24.04 LTS**, bukan 26.04. Docker dan seluruh panduan ini diuji untuk 24.04, dan dokumentasi Coolify pun hanya menyebut LTS sampai 24.04. Ubuntu 26.04 kemungkinan juga berjalan (sudah ada panduan instalasi Docker untuk 26.04), tapi 24.04 lebih aman menjelang tenggat.

KVM 2 memberi ruang lebih (3 worker, sisa RAM sekitar 5 GB). Pilih KVM 2 bila ingin memasang Coolify atau bila juri diperkirakan banyak yang mengakses bersamaan.

Perintah yang diawali `$` dijalankan di VPS sebagai user `deploy`. Perintah yang diawali `PS>` dijalankan di laptop Windows (PowerShell).

## 1. Pesan dan siapkan VPS di hPanel

1. Pilih paket **KVM 1** (atau KVM 2).
2. Lokasi server: pilih data center terdekat dengan juri (Asia, misalnya Indonesia atau Singapura).
3. Sistem operasi: **Ubuntu 24.04 64 bit** polos ("Plain OS", tanpa control panel atau template aplikasi).
4. Buat password root yang kuat, lalu tempel public key SSH laptop:
   - lihat dengan `PS> type $env:USERPROFILE\.ssh\id_ed25519.pub`;
   - buat dulu dengan `PS> ssh-keygen -t ed25519` bila belum ada.
5. Catat IP publik VPS dari hPanel (VPS → Overview).
6. **Firewall hPanel** (VPS → Security → Firewall): buat aturan yang mengizinkan TCP 22, TCP 80, TCP 443, dan UDP 443, lalu aktifkan untuk VPS ini. Firewall hPanel bekerja di luar server; UFW di langkah 2 bekerja di dalam server. Keduanya harus membuka port yang sama.

Masuk pertama kali (atau pakai "Browser terminal" di hPanel):

```powershell
PS> ssh root@IP_VPS
```

## 2. Siapkan server

```bash
apt-get update && apt-get -y upgrade
timedatectl set-timezone Asia/Makassar
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy
mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
```

Uji `PS> ssh deploy@IP_VPS` di jendela lain. Setelah berhasil, matikan login root dan password di `/etc/ssh/sshd_config` (`PermitRootLogin no`, `PasswordAuthentication no`), lalu `systemctl restart ssh`.

Firewall di dalam server:

```bash
$ sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
$ sudo ufw enable
```

Swap sebagai pengaman saat build image dan lonjakan memori: **4 GB untuk KVM 1**, 2 GB untuk KVM 2 (ganti `4G` menjadi `2G`):

```bash
$ sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
$ echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
$ echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf && sudo sysctl --system
```

Docker Engine + Compose dari repositori resmi Docker:

```bash
$ sudo apt-get install -y ca-certificates curl git
$ sudo install -m 0755 -d /etc/apt/keyrings
$ sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
$ sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
$ sudo usermod -aG docker deploy && newgrp docker
$ docker compose version
```

## 3. Ambil kode

```bash
$ git clone https://github.com/satriabimantara/prasibali.ai.git ~/prasibali
$ cd ~/prasibali && mkdir -p models backups
```

Selama repo masih privat, pakai deploy key atau `gh auth login` di VPS.

## 4. Salin folder model dari laptop

Dari PowerShell di akar repo laptop. Total sekitar 2,6 GB; file `100_*` tidak dipakai, jadi tidak disalin.

```powershell
PS> scp -r models\character-classification models\label-encoder models\balisentilex deploy@IP_VPS:~/prasibali/models/
PS> ssh deploy@IP_VPS "mkdir -p ~/prasibali/models/balinese-word-embedding"
PS> scp models\balinese-word-embedding\300_fasttext_model.bin models\balinese-word-embedding\300_fasttext_model.bin.wv.vectors_ngrams.npy deploy@IP_VPS:~/prasibali/models/balinese-word-embedding/
```

Periksa di server:

```bash
$ chmod -R a+rX ~/prasibali/models
$ du -sh ~/prasibali/models/*
$ sha256sum ~/prasibali/models/balinese-word-embedding/300_fasttext_model.bin*
```

Bandingkan hash dengan laptop (`PS> Get-FileHash models\balinese-word-embedding\300_fasttext_model.bin*`). Jika FastText tidak disalin, `warm_models` mengunduhnya sekali dari Hugging Face ke volume `hf_cache`.

## 5. Domain `prasibali.id` dan DNS

Domain `.id` didaftarkan lewat registrar yang terakreditasi PANDI. Hostinger menyediakannya, dan paket VPS memberi domain gratis selama satu tahun; periksa apakah ekstensi `.id` termasuk. Pendaftaran `.id` bisa memerlukan verifikasi dokumen (misalnya KTP), jadi lakukan sedini mungkin.

Jika domain dikelola di hPanel (Domain → DNS / Nameservers → kelola record DNS), buat:

| Tipe | Nama | Isi | TTL |
|---|---|---|---|
| A | `@` | IP_VPS | 300 |
| A | `www` | IP_VPS | 300 |

Hapus record A/AAAA bawaan lain untuk `@` dan `www` yang menunjuk ke server parkir Hostinger. Jika VPS punya IPv6 dan Anda menambahkan record AAAA, pastikan Docker dan Caddy menerima IPv6; bila ragu, cukup pakai record A. Cek dengan:

```bash
$ dig +short prasibali.id
$ dig +short www.prasibali.id
```

## 6. Isi `.env`

Buat `~/prasibali/.env` dengan `nano .env`, lalu `chmod 600 .env`. Nilai tidak pernah di-commit. Daftar lengkap variabel ada di `docs/deploy.md` bagian 5; nilai khusus Hostinger dan `prasibali.id`:

```text
DJANGO_ALLOWED_HOSTS=prasibali.id,www.prasibali.id
CSRF_TRUSTED_ORIGINS=https://prasibali.id,https://www.prasibali.id
SITE_DOMAIN=prasibali.id
# KVM 1 (untuk KVM 2: GUNICORN_WORKERS=3 dan WEB_MEM_LIMIT=6g)
GUNICORN_WORKERS=2
WEB_MEM_LIMIT=3500m
DEFAULT_FROM_EMAIL=PrasiBali.ai <alamat-gmail-anda@gmail.com>
```

Variabel wajib lain:

- `DJANGO_SECRET_KEY` (buat dengan `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`);
- `ACME_EMAIL`;
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`;
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (Gmail App Password);
- `DEMO_USER_EMAIL`, `DEMO_USER_PASSWORD`.

Catatan email: `DEFAULT_FROM_EMAIL` bawaan aplikasi memakai `no-reply@prasibali.ai`. Dengan Gmail SMTP, alamat pengirim harus alamat Gmail itu sendiri (atau alias yang terverifikasi di Gmail), jadi isi variabel ini.

## 7. Build dan jalankan

```bash
$ cd ~/prasibali
$ docker compose -f docker-compose.prod.yml config --quiet
$ docker compose -f docker-compose.prod.yml up -d --build
$ docker compose -f docker-compose.prod.yml logs -f web
```

Build pertama butuh sekitar 20–40 menit di KVM 1 dan 10–20 menit di KVM 2 (torch dan dependensi). Saat start, container `web` menjalankan `migrate`, `createcachetable`, lalu `warm_models` (SatuaNER, classifier bawaan, FastText), memasang `HF_HUB_OFFLINE=1`, lalu menyalakan Gunicorn. Caddy mengambil sertifikat Let's Encrypt untuk `prasibali.id` dan `www.prasibali.id`; `www` dialihkan 301 ke `https://prasibali.id`.

Pemeriksaan:

```bash
$ docker compose -f docker-compose.prod.yml ps                 # web "healthy"
$ curl -s https://prasibali.id/healthz                          # {"status": "ok", "database": "ok"}
$ curl -sI https://www.prasibali.id/ | head -n 3                # 301 ke https://prasibali.id/
$ curl -sI https://prasibali.id/ | grep -iE "strict-transport|content-security"
$ docker stats --no-stream && free -h
```

Jika sertifikat gagal (`docker compose ... logs caddy`), periksa DNS (langkah 5), lalu firewall hPanel dan UFW untuk port 80/443.

## 8. Akun demo juri

```bash
$ docker compose -f docker-compose.prod.yml exec web python manage.py create_demo_user
```

Perintah ini membaca `DEMO_USER_EMAIL` dan `DEMO_USER_PASSWORD` dari `.env` dan tidak pernah mencetak password. Sebelum mengirim kredensial lewat formulir panitia, uji sendiri: masuk dengan akun demo, klik salah satu contoh satua, jalankan "Analisis teks", lalu coba model SVM + TF5 di Mode Peneliti.

## 9. Backup dan pembaruan

- Backup database harian otomatis ke `~/prasibali/backups/` (layanan `backup`). Untuk backup manual dan restore, lihat `docs/deploy.md` bagian 9.
- Backup mingguan gratis Hostinger (snapshot seluruh VPS) melengkapi backup database ini. Aktifkan di hPanel → VPS → Backups.
- Untuk pembaruan aplikasi (`git pull` lalu `up -d --build web`), lihat `docs/deploy.md` bagian 10.
- Jika domain belum aktif saat tenggat: isi `SITE_DOMAIN=IP-VPS-dengan-tanda-hubung.sslip.io`, sesuaikan `DJANGO_ALLOWED_HOSTS` dan `CSRF_TRUSTED_ORIGINS`, lalu `up -d`.
