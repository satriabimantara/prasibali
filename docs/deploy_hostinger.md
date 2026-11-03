# Deploy PrasiBali.ai v1.0 ke Hostinger VPS KVM 1 (`prasibali.tech`)

Panduan ini diikuti urut dari atas ke bawah. Bagian A–E dikerjakan **sekali** saat deploy pertama. Bagian F adalah rutinitas setiap ada rilis baru: cukup `git push prod master` dari laptop.

| Komponen | Nilai |
|---|---|
| VPS | Hostinger KVM 1: 1 vCPU, 4 GB RAM, 50 GB NVMe, Ubuntu 26.04 LTS 64 bit, tanpa control panel |
| Alamat | `https://prasibali.tech` (`www.prasibali.tech` dialihkan ke sana), IP 187.124.141.29 |
| Email aplikasi | mailbox `noreply@prasibali.tech` lewat SMTP Hostinger (`smtp.hostinger.com:587`, STARTTLS) |
| Layanan | Docker Compose (`docker-compose.prod.yml`): Caddy (HTTPS otomatis), Django + Gunicorn, PostgreSQL, backup harian |
| Rilis | laptop `git push prod master` → hook di server → `deploy/server/deploy.sh` → `docker compose up -d --build` |

Penanda perintah:

- `PS>`: PowerShell di laptop, dari folder repo `#15-prasibali.ai`;
- `root$`: di VPS sebagai `root`;
- `$`: di VPS sebagai user `deploy`.

Sudah siap (diperiksa 3 November 2026):

- DNS `prasibali.tech` dan `www` → 187.124.141.29;
- MX `mx1/mx2.hostinger.com`, SPF `include:_spf.mail.hostinger.com`, dan DKIM `hostingermail1._domainkey`;
- kunci SSH laptop terdaftar di `root`.

## Apakah KVM 1 cukup?

Ya. Angka berikut dari uji penuh image produksi dengan batas seperti KVM 1 (1 vCPU, 2 worker, batas memori 3.500 MB); rinciannya di `docs/deploy.md` bagian "Memori dan jumlah worker".

| Ukuran | Hasil |
|---|---|
| Puncak memori container `web` (12 analisis + 3 klien bersamaan, termasuk SVM + TF5) | 2.910 MB; OOM 0, restart 0 |
| Postgres | 83 MB |
| Perkiraan total dengan Ubuntu + Caddy | sekitar 3,5 GB dari 4 GB (swap 4 GB sebagai pengaman) |
| Satua terpanjang (16.876 karakter): 1 klien / 3 klien bersamaan | 1,1–1,7 detik / 1,1–4,7 detik |
| Siap melayani setelah container start | sekitar 2 menit |

Coolify tidak dipasang: kebutuhan minimumnya 2 core CPU, dan proxy-nya bentrok dengan Caddy. Pilihan kontrol panel gratis ada di bagian G.

---

## A. Persiapan di hPanel (sekali, sekitar 10 menit)

Nama menu hPanel bisa sedikit berbeda menurut bahasa tampilan dan pembaruan Hostinger. Yang dicari selalu bagian **VPS** dan **Emails** untuk domain `prasibali.tech`.

### A1. Buka port di firewall VPS

Ada dua lapisan firewall: firewall hPanel (di luar server) dan UFW (di dalam server, dipasang otomatis di langkah B). Keduanya harus membuka port yang sama.

1. hPanel → **VPS** → pilih VPS 187.124.141.29 → **Security** (Keamanan) → **Firewall**.
2. **Create firewall configuration** (Tambah konfigurasi firewall), beri nama `prasibali`.
3. Tambahkan aturan **Accept** dengan sumber **Any**:

   | Protokol | Port | Fungsi |
   |---|---|---|
   | TCP | 22 | SSH dan `git push prod` |
   | TCP | 80 | HTTP (Let's Encrypt dan pengalihan ke HTTPS) |
   | TCP | 443 | HTTPS |
   | UDP | 443 | HTTP/3 |

4. Aktifkan konfigurasi itu untuk VPS ini (**Activate** atau **Synchronize**).

Jangan membuka port lain (misalnya 5432 Postgres atau 8000 Gunicorn); keduanya hanya dipakai di dalam jaringan Docker.

### A2. Buat mailbox `noreply@prasibali.tech`

1. hPanel → **Emails** → pilih domain `prasibali.tech` → **Email accounts** (Akun email) → **Create email account**.
2. Nama: `noreply`, password: buat password kuat dan simpan di password manager. Password ini adalah `EMAIL_HOST_PASSWORD` di langkah D2.
3. Lupa password: di daftar akun email, menu titik tiga pada `noreply@prasibali.tech` → **Change password**.

Pengaturan SMTP bisa dilihat di hPanel → **Emails** → **Connect apps & devices** (atau *Configuration settings*). Aplikasi memakai `smtp.hostinger.com`, port **587**, **STARTTLS** sebagai bawaan; port 465/SSL adalah cadangan (bagian H).

### A3. Akses darurat

- **Browser terminal**: hPanel → VPS → **Overview** → tombol **Browser terminal**. Dipakai bila SSH dari laptop gagal.
- **Password root VPS** (hanya untuk browser terminal atau console; SSH memakai kunci): hPanel → VPS → **Settings** → **Root password** → ubah. Isi sendiri dan jangan ditulis di repo atau chat.

### A4. Cek DNS dari laptop

```powershell
PS> Resolve-DnsName prasibali.tech -Type A
PS> Resolve-DnsName www.prasibali.tech
```

Keduanya harus berujung di `187.124.141.29`.

---

## B. Siapkan VPS (sekali, sekitar 10–15 menit)

Skrip `deploy/server/setup_vps.sh` melakukan semuanya dan aman dijalankan ulang:

1. update sistem, zona waktu Asia/Makassar, swap 4 GB;
2. Docker Engine + Compose (dari repo Docker; bila repo Docker belum mendukung Ubuntu 26.04, otomatis memakai paket Ubuntu);
3. UFW: OpenSSH, 80/tcp, 443/tcp, 443/udp;
4. user `deploy` (grup docker) dengan kunci SSH yang sama dengan root, dan login SSH **hanya dengan kunci** (login dengan password dimatikan);
5. tujuan `git push`: repo `~deploy/prasibali.git` dengan hook yang men-deploy otomatis ke `~deploy/prasibali`.

```powershell
PS> scp deploy\server\setup_vps.sh root@prasibali.tech:
PS> ssh root@prasibali.tech "bash setup_vps.sh"
```

Di akhir, skrip mencetak `Docker version ...`, status UFW, dan "Next steps". **Sebelum menutup sesi**, buka PowerShell baru dan pastikan user `deploy` bisa masuk:

```powershell
PS> ssh deploy@prasibali.tech "echo ok && docker --version && free -h"
```

Jika gagal, jangan logout dari root. Perbaiki lewat browser terminal (A3), misalnya periksa `/home/deploy/.ssh/authorized_keys`.

---

## C. Unggah model pretrained (sekali, sekitar 30 MB)

Folder `models/` tidak ada di git. Bundel berisi tepat model yang dipakai v1.0, dibaca dari katalog model:

- 9 pickle classifier word vector (M1: TF4, TF5, TF4+TF5; M2: DT, GNB, KNN, MLP, RF, SVM);
- label encoder;
- `SHA256SUMS`.

Model leksikon belum dipakai di v1.0. FastText 300 dimensi (2,4 GB) **tidak** diunggah: container mengunduhnya sekali dari Hugging Face saat start pertama dan menyimpannya di volume `hf_cache`.

```powershell
PS> .venv\Scripts\python.exe scripts\bundle_models.py
PS> scp dist\prasibali-models-v1.0.tar.gz deploy@prasibali.tech:
PS> ssh deploy@prasibali.tech "tar -xzf prasibali-models-v1.0.tar.gz -C prasibali/models && cd prasibali/models && sha256sum -c SHA256SUMS && rm ~/prasibali-models-v1.0.tar.gz"
```

Semua baris harus `OK`. `deploy.sh` mengulang pemeriksaan ini sebelum setiap deploy.

Jika suatu saat Hugging Face tidak bisa diakses dari server, buat bundel lengkap dengan `scripts\bundle_models.py --with-fasttext` (sekitar 2,4 GB) dan unggah dengan cara yang sama. Untuk mengganti model di kemudian hari: buat bundel baru, unggah, ekstrak, lalu jalankan `bash ~/prasibali/deploy/server/deploy.sh` di server.

---

## D. Deploy pertama (sekitar 30–45 menit, sebagian besar build image)

### D1. Kirim kode dari laptop

Pastikan semua perubahan sudah di-commit, termasuk `.env.example`. Yang dikirim hanya isi commit, bukan file yang belum di-commit.

```powershell
PS> git status
PS> git remote add prod deploy@prasibali.tech:prasibali.git
PS> git push prod master
```

Output akan berisi `Checked out ...` dan `Deploy started in the background`. Pada push pertama, log deploy berhenti dengan `.env is missing`. **Itu wajar**; lanjutkan ke D2.

### D2. Buat dan isi `.env` di server

```powershell
PS> ssh deploy@prasibali.tech
```

```bash
$ bash ~/prasibali/deploy/server/init_env.sh
$ nano ~/prasibali/.env
```

`init_env.sh` sudah mengisi semua nilai, termasuk `DJANGO_SECRET_KEY` dan `POSTGRES_PASSWORD` acak yang dibuat di server. Isi tiga baris yang masih kosong:

| Variabel | Isi | Didapat dari |
|---|---|---|
| `EMAIL_HOST_PASSWORD` | password mailbox `noreply@prasibali.tech` | langkah A2 (hPanel → Emails → Email accounts) |
| `DEMO_USER_EMAIL` | email akun demo juri, misalnya `demo@prasibali.tech` atau alamat lain milik Anda | Anda tentukan |
| `DEMO_USER_PASSWORD` | password akun demo (minimal 8 karakter, tidak umum) | Anda tentukan, lalu kirim ke panitia lewat formulir resmi |

Simpan di nano dengan `Ctrl+O`, `Enter`, lalu keluar dengan `Ctrl+X`. Jangan ubah `POSTGRES_PASSWORD` setelah deploy pertama: password itu dipakai saat database dibuat.

### D3. Jalankan deploy

Masih di server sebagai `deploy`:

```bash
$ setsid nohup bash ~/prasibali/deploy/server/deploy.sh >> ~/prasibali/deploy.log 2>&1 < /dev/null &
$ tail -f ~/prasibali/deploy.log
```

Tekan `Ctrl+C` untuk berhenti mengikuti log; deploy tetap berjalan walau SSH terputus. Urutannya:

1. build image (20–40 menit di 1 vCPU);
2. `migrate`, lalu `warm_models` (pertama kali mengunduh FastText 2,4 GB dari Hugging Face);
3. Gunicorn menyala dan Caddy mengambil sertifikat Let's Encrypt;
4. log berakhir dengan `Deploy ... finished: web is healthy`.

### D4. Buat akun demo juri

```bash
$ cd ~/prasibali
$ docker compose -f docker-compose.prod.yml exec web python manage.py create_demo_user
```

Output: `Demo user created: ...`. Password tidak pernah dicetak.

---

## E. Verifikasi

Dari laptop:

```powershell
PS> curl.exe -s https://prasibali.tech/healthz
PS> curl.exe -sI https://www.prasibali.tech/
PS> curl.exe -sI https://prasibali.tech/
```

Hasil yang diharapkan:

- `/healthz` mengembalikan `{"status": "ok", "database": "ok"}`;
- `www` mengembalikan `301` ke `https://prasibali.tech/`;
- halaman utama mengembalikan `200` dengan header `strict-transport-security`, `content-security-policy`, dan `x-frame-options: DENY`.

Uji email SMTP dari server, ke alamat yang bisa Anda buka:

```bash
$ cd ~/prasibali
$ docker compose -f docker-compose.prod.yml exec web python manage.py sendtestemail alamat-anda@contoh.com
```

Pengirimnya harus `PrasiBali.ai <noreply@prasibali.tech>`; periksa juga folder spam. Jika gagal, lihat bagian H.

Uji manual di browser (sebaiknya jendela privat):

1. **Daftar** di `https://prasibali.tech/daftar/` → email "konfirmasi" datang dari `noreply@prasibali.tech` → klik tautannya (`https://prasibali.tech/akun/confirm-email/...`).
2. **Masuk** → **Analisis** → klik satu contoh satua → **Analisis teks** → hasil tampil.
3. **Lanjutan (Mode Peneliti)** → pilih SVM + TF5 (M2) → analisis lagi.
4. **Riwayat** → buka detail → hapus satu.
5. **Profil** → ubah nama → simpan (tidak ada email). **Pengaturan** → ganti bahasa ke English.
6. **Akun → Email** → tambah alamat lain → email konfirmasi datang.
7. Keluar → **Lupa kata sandi?** → email reset datang → set kata sandi baru → masuk dengan kata sandi baru.
8. Masuk dengan akun demo juri (D4).

---

## F. Rutinitas rilis berikutnya

Setiap ada perubahan yang siap dipublikasikan:

```powershell
PS> git add ... ; git commit -m "..."
PS> git push prod master
PS> ssh deploy@prasibali.tech tail -f prasibali/deploy.log
```

Selebihnya otomatis, tanpa konfigurasi ulang:

- hook `post-receive` meng-checkout commit baru ke `~/prasibali`; `.env`, `models/`, dan `backups/` tidak tersentuh;
- `deploy.sh` memeriksa `.env` dan model, membangun image baru, lalu mengganti container dan menunggu status `healthy`;
- migrasi database berjalan otomatis saat container start.

Build berikutnya hanya beberapa menit, karena layer dependensi tersimpan di cache; build lama hanya bila `requirements.txt` berubah. Jika build gagal, **versi lama tetap berjalan** dan log menulis `DEPLOY FAILED`. Push ke GitHub tetap terpisah: `git push origin master`.

| Keperluan | Perintah |
|---|---|
| Versi yang sedang berjalan | `ssh deploy@prasibali.tech cat prasibali/REVISION` |
| Deploy ulang commit yang sama (misalnya setelah mengubah `.env`) | `ssh deploy@prasibali.tech "setsid nohup bash prasibali/deploy/server/deploy.sh >> prasibali/deploy.log 2>&1 < /dev/null &"` |
| Batalkan rilis (cara aman) | `git revert <sha>` lalu `git push prod master` |
| Kembali paksa ke commit lama | `git push prod <sha-lama>:master --force` |

Hanya branch `master` yang di-deploy; push ke branch lain diabaikan.

---

## G. Operasional harian

```bash
$ cd ~/prasibali
$ docker compose -f docker-compose.prod.yml ps                       # status semua layanan
$ docker compose -f docker-compose.prod.yml logs --tail 100 web      # log aplikasi (JSON)
$ docker stats --no-stream && free -h                                # memori
$ docker compose -f docker-compose.prod.yml restart web              # restart aplikasi
```

- **Backup database** berjalan otomatis setiap hari pukul 02.00 WITA ke `~/prasibali/backups/` dan disimpan 14 hari. Backup sekarang: `docker compose -f docker-compose.prod.yml exec backup sh /usr/local/bin/backup.sh now`. Unduh ke laptop: `PS> scp deploy@prasibali.tech:prasibali/backups/*.dump .\backups\`. Cara restore ada di `docs/deploy.md` bagian 9.
- **Backup mingguan Hostinger** (snapshot VPS): hPanel → VPS → **Backups**.
- **Kontrol panel gratis (opsional)**:
  - hPanel sudah mencakup reboot, firewall, snapshot, grafik CPU/RAM, dan browser terminal.
  - Bila ingin tampilan web, pasang **Cockpit** (`sudo apt install cockpit`). Cockpit hanya berjalan saat dibuka, jadi hampir tidak memakai RAM. Jangan buka port 9090 di firewall; akses lewat tunnel `PS> ssh -L 9090:localhost:9090 deploy@prasibali.tech`, lalu buka `http://localhost:9090`.
  - Jangan pasang CyberPanel atau CloudPanel, karena keduanya bentrok dengan Caddy di port 80/443.

---

## H. Troubleshooting

| Gejala | Penyebab dan perbaikan |
|---|---|
| `ssh deploy@...` ditolak | Kunci tidak tersalin. Masuk lewat browser terminal, cek `/home/deploy/.ssh/authorized_keys`, jalankan ulang `bash setup_vps.sh` sebagai root |
| `setup_vps.sh` gagal memasang Docker di 26.04 | Jalankan `root$ apt-get install -y docker.io docker-compose-v2 docker-buildx`, lalu ulangi skrip |
| Log: `.env is missing` / `models/ is empty` / `sha256sum` gagal | Kerjakan D2 atau C, lalu jalankan ulang deploy (tabel di F) |
| Log: `web is unhealthy` | Baca 60 baris log yang dicetak. `Model warm-up failed` biasanya berarti unduhan Hugging Face gagal (pakai bundel `--with-fasttext`) |
| Sertifikat HTTPS gagal (`docker compose ... logs caddy`) | Port 80/443 belum terbuka di firewall hPanel (A1) atau DNS belum mengarah ke VPS (A4) |
| `sendtestemail` gagal: autentikasi | `EMAIL_HOST_USER` harus alamat lengkap `noreply@prasibali.tech` dan `EMAIL_HOST_PASSWORD` harus password mailbox itu (A2) |
| `sendtestemail` timeout di port 587 | Di `.env` tambahkan `EMAIL_PORT=465`, `EMAIL_USE_TLS=False`, `EMAIL_USE_SSL=True`, lalu deploy ulang |
| Email masuk spam | Pastikan DKIM aktif (hPanel → Emails → Email deliverability) dan SPF/MX tidak diubah |
| `Killed`, `oom_kill`, atau `WORKER TIMEOUT` di log | Turunkan `GUNICORN_WORKERS=1` di `.env`, lalu deploy ulang; cek `free -h` dan swap |
| Perubahan `.env` tidak berlaku | Container membaca `.env` saat dibuat: jalankan deploy ulang (tabel di F) atau `docker compose -f docker-compose.prod.yml up -d` |

---

## Lampiran: uji email Hostinger dari laptop (lokal)

Secara bawaan, settings lokal (`config.settings.dev`) hanya mencetak email ke konsol. Untuk mencoba pengiriman sungguhan dari laptop, ubah baris email di `.env` lokal (jangan di-commit). Baris `EMAIL_HOST=smtp.gmail.com` yang lama harus diganti:

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=noreply@prasibali.tech
EMAIL_HOST_PASSWORD=<password mailbox noreply>
DEFAULT_FROM_EMAIL="PrasiBali.ai <noreply@prasibali.tech>"
```

```powershell
PS> .venv\Scripts\python.exe src\manage.py sendtestemail alamat-anda@contoh.com
PS> .venv\Scripts\python.exe src\manage.py runserver
```

Lalu coba daftar, lupa kata sandi, dan tambah email di `http://localhost:8000`. Tautan di email lokal memakai `http://localhost:8000`; di server memakai `https://prasibali.tech`. Hapus baris `EMAIL_BACKEND` untuk kembali ke mode konsol.
