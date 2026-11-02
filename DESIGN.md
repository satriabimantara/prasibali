---
version: "1.0"
name: Endek Indigo
product: PrasiBali.ai
description: Sistem desain PrasiBali.ai, aplikasi web analisis tokoh dalam satua Bali. Disiplin dasbor fintech premium (putih bersih, satu aksen indigo, panel bergaris tipis) dengan identitas Bali lewat aksara Prasi dan pola ikat endek. Tema terang adalah bawaan, tema gelap lewat tombol.
locale: id-ID

colors:
  bg: "#F7F8FC"
  surface: "#FFFFFF"
  surface-selected: "#EEF0FB"
  ink: "#111A33"
  muted: "#56607A"
  accent: "#3341B8"
  accent-hover: "#2A36A0"
  accent-press: "#222C85"
  on-accent: "#FFFFFF"
  line: "#E1E5F0"
  line-strong: "#7A83A0"
  protagonis: "#0A4A61"
  protagonis-bg: "#E1F2F7"
  antagonis: "#B04E0C"
  antagonis-bg: "#FCEDE0"
  danger: "#B3261E"
  danger-bg: "#FDECEA"
  success: "#1B6B45"
  success-bg: "#E6F4EC"
  warning: "#7A5200"
  warning-bg: "#FDF3DC"

colors-dark:
  bg: "#0C1224"
  surface: "#141B33"
  surface-selected: "#1E2748"
  ink: "#EDF0FA"
  muted: "#A3ACC6"
  accent: "#A3AEFF"
  accent-hover: "#B6BFFF"
  accent-press: "#8E9AF5"
  on-accent: "#0C1224"
  line: "#2A3352"
  line-strong: "#737EA3"
  protagonis: "#A9E2F5"
  protagonis-bg: "#11323F"
  antagonis: "#EC9450"
  antagonis-bg: "#3E2613"
  danger: "#FFB4AB"
  danger-bg: "#40191A"
  success: "#8FDDB2"
  success-bg: "#123525"
  warning: "#F2C66D"
  warning-bg: "#3A2C0E"

typography:
  family-ui: "'Schibsted Grotesk', system-ui, -apple-system, 'Segoe UI', sans-serif"
  family-aksara: "'Noto Serif Balinese', serif"
  display:
    fontSize: "clamp(40px, 5.4vw, 68px)"
    fontWeight: 500
    lineHeight: 1.04
    letterSpacing: "-0.03em"
  page-title:
    fontSize: 26px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  panel-title:
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  section-title:
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.35
  lead:
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.55
  story:
    fontSize: 17px
    fontWeight: 400
    lineHeight: 1.8
  body:
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
  caption:
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1.3
  stat:
    fontSize: 30px
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.02em"
    fontVariantNumeric: tabular-nums
  aksara:
    fontSize: "clamp(56px, 7vw, 96px)"
    fontWeight: 400
    lineHeight: 1.25

rounded:
  sm: 6px
  md: 8px
  lg: 12px
  full: 999px

spacing:
  "1": 4px
  "2": 8px
  "3": 12px
  "4": 16px
  "5": 20px
  "6": 24px
  "8": 32px
  "10": 40px
  "16": 64px

sizes:
  control-min-height: 44px
  control-large-height: 46px
  sidebar-width: 224px
  story-max-width: 72ch
  lead-max-width: 54ch
  content-max-width: 1440px

breakpoints:
  sm: 640px
  md: 768px
  lg: 1024px
  xl: 1280px

motion:
  fast: 120ms
  base: 180ms
  easing: "cubic-bezier(0.2, 0, 0, 1)"

components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.md}"
    minHeight: "{sizes.control-min-height}"
    padding: "0 16px"
    fontSize: 14px
    fontWeight: 600
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    borderColor: "{colors.line}"
    rounded: "{rounded.md}"
    minHeight: "{sizes.control-min-height}"
    padding: "0 16px"
    fontSize: 14px
    fontWeight: 600
  input:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    borderColor: "{colors.line-strong}"
    rounded: "{rounded.md}"
    minHeight: "{sizes.control-large-height}"
    padding: "0 12px"
  panel:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.line}"
    rounded: "{rounded.lg}"
    padding: 24px
  stat-card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.line}"
    rounded: "{rounded.lg}"
    padding: "14px 16px"
  nav-item:
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    minHeight: "{sizes.control-min-height}"
    padding: "0 12px"
  nav-item-active:
    backgroundColor: "{colors.surface-selected}"
    textColor: "{colors.ink}"
    fontWeight: 600
  role-badge-protagonis:
    backgroundColor: "{colors.protagonis-bg}"
    textColor: "{colors.protagonis}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
  role-badge-antagonis:
    backgroundColor: "{colors.antagonis-bg}"
    textColor: "{colors.antagonis}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
  entity-protagonis:
    backgroundColor: "{colors.protagonis-bg}"
    textColor: "{colors.protagonis}"
    borderBottom: "2px solid currentColor"
    padding: "1px 3px"
  entity-antagonis:
    backgroundColor: "{colors.antagonis-bg}"
    textColor: "{colors.antagonis}"
    borderBottom: "2px dashed currentColor"
    padding: "1px 3px"
---

# DESIGN.md: Endek Indigo untuk PrasiBali.ai

Dokumen ini adalah sumber kebenaran tampilan PrasiBali.ai. Saat membangun atau mengubah antarmuka:

1. Pakai token dari dokumen ini. Jangan menulis warna, ukuran huruf, atau radius di luar token.
2. Ikuti spesifikasi komponen dan halaman di bawah sebelum membuat pola baru.
3. Jika perlu pola yang belum ada, buat dari token yang sama lalu tambahkan ke dokumen ini.
4. Selesaikan dengan daftar periksa di bagian akhir.

## Ringkasan produk

| Hal | Keputusan |
|---|---|
| Produk | PrasiBali.ai: analisis tokoh dalam teks satua Bali |
| Fungsi AI | Mengenali tokoh, mengelompokkan nama lain (alias), mengklasifikasi peran protagonis atau antagonis |
| Pengguna | Juri lomba, peneliti, guru, siswa, Balai Bahasa, dan Dinas Kebudayaan |
| Bahasa antarmuka | Indonesia (bawaan) dan Inggris, lewat gettext |
| Tema | Terang sebagai bawaan, tombol ke tema gelap |
| Mode | Sederhana sebagai bawaan, Lanjutan untuk peneliti |
| Alur | Landing, lalu wajib login, lalu ruang kerja |
| Teknologi | Django MVT, Tailwind CSS v4, HTMX |

## Prinsip

- **Tenang dan tepercaya.** Latar putih, garis tipis, satu warna aksen. Kesan premium datang dari tipografi dan jarak yang rapi, bukan dekorasi.
- **Teks cerita adalah pusatnya.** Hasil AI ditampilkan langsung pada teks satua, lalu dijelaskan di panel tokoh.
- **Istilah teknis tidak menghalangi.** Mode Sederhana tidak menampilkan nama model. Mode Lanjutan menampilkannya.
- **Identitas Bali secukupnya.** Aksara Prasi dan pola ikat hanya muncul di landing dan halaman autentikasi. Ruang kerja tetap netral.
- **Warna tidak bekerja sendirian.** Peran tokoh selalu dibedakan lewat warna, bentuk garis, dan teks.

## Warna

Nilai heksadesimal ada di frontmatter. Komponen hanya memakai nama token.

| Token | Dipakai untuk |
|---|---|
| `bg` | Latar halaman, latar input |
| `surface` | Panel, kartu, sidebar, header |
| `surface-selected` | Item navigasi aktif, tokoh terpilih, hover baris |
| `ink` | Teks utama |
| `muted` | Teks pendukung, label data, navigasi tidak aktif |
| `accent` | Tombol utama, tautan, cincin fokus, aksara Prasi, pola ikat |
| `line` | Garis pemisah dan tepi panel |
| `line-strong` | Tepi input dan kontrol yang harus terlihat |
| `protagonis`, `protagonis-bg` | Hanya untuk peran protagonis |
| `antagonis`, `antagonis-bg` | Hanya untuk peran antagonis |
| `danger`, `success`, `warning` beserta `-bg` | Hanya untuk umpan balik sistem |

Aturan:

- Warna peran tidak boleh dipakai untuk tombol, status sistem, atau dekorasi.
- Jangan memakai gradien, bayangan berwarna, atau warna tambahan.
- Tombol hover memakai `accent-hover`, bukan efek `filter`.
- Kontras token teks sudah dihitung minimal 4.5:1 terhadap latarnya, dan `line-strong` minimal 3:1. Jangan mengganti nilai tanpa menghitung ulang.

## Tipografi

- **Schibsted Grotesk** dipakai untuk seluruh antarmuka dan teks satua, dengan bobot 400, 500, dan 600.
- **Noto Serif Balinese** hanya dipakai untuk aksara Prasi.
- Muat font dengan `display=swap`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+Balinese&family=Schibsted+Grotesk:wght@400;500;600&display=swap">
```

Aturan:

- Gunakan sentence case. Jangan memakai huruf kapital semua untuk label.
- Panjang baris teks satua maksimal `72ch`.
- Angka statistik memakai `tabular-nums`.
- Teks satua diberi `lang="ban"` agar pembaca layar dan pemeriksa ejaan tidak menganggapnya bahasa Indonesia.
- Tidak ada ukuran huruf di bawah 13px.

## Tata letak

- Jarak mengikuti skala `spacing` dengan kelipatan 4px.
- Kelompokkan elemen dengan flex atau grid dan `gap`, bukan margin antarelemen.
- Padding halaman: `clamp(16px, 5vw, 64px)` di landing, `clamp(16px, 3vw, 32px)` di ruang kerja.
- Tepi panel 1px `line` tanpa bayangan. Bayangan hanya untuk elemen yang mengambang: dropdown, dialog, toast (`0 8px 24px rgb(17 26 51 / 0.12)`, di tema gelap `0 8px 24px rgb(0 0 0 / 0.4)`).

### Perilaku responsif

| Lebar | Ruang kerja |
|---|---|
| Di bawah 768px | Satu kolom: header, ringkasan, teks cerita, panel tokoh. Sidebar menjadi menu di bagian atas |
| 768px sampai 1023px | Sidebar tetap di atas, teks cerita dan panel tokoh satu kolom |
| 1024px ke atas | Sidebar 224px, teks cerita fleksibel, panel tokoh sekitar 320px dan `sticky` |

Tidak boleh ada gulir horizontal pada halaman. Tabel lebar diletakkan di kotak `overflow-x-auto`.

## Bentuk dan gerak

- Radius: `md` untuk tombol dan input, `lg` untuk panel, `sm` untuk lencana. `full` hanya untuk indikator bulat.
- Gerak hanya sebagai tanggapan atas aksi pengguna. Jangan memakai animasi masuk saat gulir.
- Durasi `fast` untuk hover dan `base` untuk membuka elemen.
- Hormati `prefers-reduced-motion: reduce` dengan menghentikan transisi dan animasi.

## Identitas Bali

### Aksara Prasi

Aksara Bali untuk "Prasi" diletakkan tepat di atas judul utama landing.

```html
<div lang="ban" role="img" aria-label="Prasi dalam aksara Bali" class="font-aksara text-accent leading-tight text-[clamp(56px,7vw,96px)]">&#x1B27;&#x1B44;&#x1B2D;&#x1B32;&#x1B36;</div>
```

- Urutan kode: U+1B27 (pa), U+1B44 (adeg-adeg), U+1B2D (ra), U+1B32 (sa), U+1B36 (ulu).
- Gunakan hanya di landing dan halaman autentikasi, satu kali per halaman.
- Jangan menambah aksara Bali lain tanpa validasi ahli.

### Pola ikat endek

Pola geometris generik yang terinspirasi teknik ikat, bukan replika motif endek tertentu. Dipakai sebagai pita di atas formulir masuk, tinggi 132px, warna `accent`, dan `aria-hidden="true"`. Buat sekali sebagai partial SVG statis:

```python
# scripts/generate_ikat.py -> menulis templates/partials/ikat.html
rects = []
for y in range(6):
    for x in range(24):
        d = abs(((x + 6) % 12) - 6) + abs(y - 2.5)
        edge = 1 if (x * 7 + y * 13) % 5 == 0 else 0
        o = 1 if d + edge < 4.5 else 0.45 if d + edge < 5.5 else 0.1
        rects.append(f'<rect x="{x}" y="{y}" width="1" height="1" opacity="{o}"/>')
svg = (
    '<svg viewBox="0 0 24 6" preserveAspectRatio="none" shape-rendering="crispEdges" '
    'fill="currentColor" aria-hidden="true" class="block h-[132px] w-full text-accent">'
    + "".join(rects) + "</svg>"
)
open("templates/partials/ikat.html", "w", encoding="utf-8").write(svg)
```

## Komponen

Setiap kontrol interaktif memiliki keadaan default, hover, fokus, aktif, nonaktif, dan memuat. Fokus selalu memakai cincin `2px solid accent` dengan `outline-offset: 2px`. Target sentuh minimal 44px, kecuali nama tokoh di dalam baris teks.

### Tombol

| Varian | Dipakai untuk | Aturan |
|---|---|---|
| Utama | Satu aksi terpenting per area, seperti "Analisis teks" | Latar `accent` |
| Sekunder | Aksi pendamping, seperti "Unduh hasil (CSV)" | Latar `surface`, tepi `line`, tepi `muted` saat hover |
| Bahaya | Aksi yang menghapus data | Teks `danger`, wajib konfirmasi |

- Label memakai kata kerja yang menjelaskan hasilnya.
- Saat memuat: tombol nonaktif dan label berubah, misalnya "Menganalisis...".
- Gunakan `<button>` untuk aksi dan `<a>` untuk pindah halaman.

### Formulir

- Label selalu terlihat di atas input, ukuran `label`. Placeholder bukan pengganti label.
- Kesalahan muncul di bawah input dengan teks `danger`, dihubungkan lewat `aria-describedby`, dan `aria-invalid="true"` pada input.
- Pasang `autocomplete` yang sesuai pada formulir masuk dan daftar.
- Area teks satua minimal 12 baris, `lang="ban"`, dengan contoh satua yang bisa dimuat satu klik.
- Render field Django lewat `{% form_field field %}` (`apps/accounts/templatetags/form_tags.py`, partial `partials/form_field.html`). Tag ini memasang kelas, `aria-invalid`, dan `aria-describedby` sesuai aturan di atas. Halaman allauth memakai pola yang sama lewat override `templates/allauth/elements/`.

| Kelas | Dipakai untuk |
|---|---|
| `.field` | Pembungkus label, kontrol, bantuan, dan kesalahan (`gap` 8px) |
| `.field-label` | Label di atas kontrol, ukuran `label` |
| `.input`, `.select` | Kontrol teks dan pilihan, tinggi 46px, tepi `line-strong` |
| `.check` + `.checkbox` | Kotak centang 20px di dalam label setinggi minimal 44px |
| `.help` | Teks bantuan, ukuran `caption`, warna `muted` |
| `.field-error` | Kesalahan di bawah input, warna `danger` |
| `.alert--info/success/warning/danger` | Pesan sistem dan kesalahan formulir umum |
| `.link` | Tautan di dalam teks, warna `accent`, bergaris bawah |
| `.btn-danger` | Tombol bahaya: teks `danger`, tepi `danger` saat hover |

Ukuran huruf tersedia sebagai utilitas Tailwind dari token: `text-page-title`, `text-panel-title`, `text-section-title`, `text-lead`, `text-body`, `text-label`, `text-caption`. Ukuran bawaan Tailwind dimatikan.

### Header ruang kerja

Berisi judul cerita di kiri, lalu pengalih mode, tombol tema, dan tombol utama "Analisis teks baru" di kanan. Membungkus ke baris baru di layar sempit.

### Pengalih mode

```html
<div role="group" aria-label="Mode tampilan">
  <button type="button" aria-pressed="true">Sederhana</button>
  <button type="button" aria-pressed="false">Lanjutan</button>
</div>
```

| Konten | Sederhana | Lanjutan |
|---|---|---|
| Teks cerita bertanda dan peran tokoh | Ya | Ya |
| Nama lain dan jumlah kemunculan | Ya | Ya |
| Label entitas dan nomor kelompok | Tidak | Ya |
| Nama model dan pilihan model | Tidak | Ya |
| Unduh hasil (CSV) | Tidak | Ya |

Label entitas mengikuti definisi tesis, dan penjelasannya tampil sebagai teks bantuan:

| Label | Arti untuk pengguna |
|---|---|
| `ADJ` | Nama yang berasal dari sifat, seperti I Belog |
| `PNAME` | Nama diri, seperti Made Bhaskara |
| `GODS` | Dewa atau tokoh suci, seperti Bhatara Indra |
| `ANM` | Hewan atau benda yang dipersonifikasi, seperti I Kancil |
| `OBJ` | Sebutan tanpa nama diri, seperti memene |

Pilihan model diambil dari konfigurasi backend. Jangan menulis daftar model di template.

### Kartu ringkasan

Tiga kartu: "Kelompok tokoh", "Protagonis", dan "Antagonis". Isinya dihitung dari hasil analisis. Jangan menampilkan angka contoh atau metrik yang tidak dihitung sistem.

### Sorotan tokoh pada teks

```html
<button type="button" class="entity entity--protagonis" data-group-id="4" aria-pressed="false">Ni Bawang</button>
```

- Protagonis: `protagonis` di atas `protagonis-bg`, garis bawah utuh.
- Antagonis: `antagonis` di atas `antagonis-bg`, garis bawah putus-putus.
- Terpilih: semua kemunculan kelompok yang sama diberi `outline: 2px solid currentColor` dengan `outline-offset: 1px`.
- `display: inline`, mengikuti font dan tinggi baris teks, tanpa memengaruhi jarak baris.
- Keyboard: gunakan roving tabindex. Hanya satu sorotan yang masuk urutan Tab, panah kiri dan kanan berpindah antarsorotan, Enter atau Spasi memilih.

### Daftar tokoh

- Setiap baris adalah `<button aria-pressed>` berisi nama tokoh dan lencana peran.
- Baris terpilih memakai `surface-selected` dan bobot 600.
- Memilih tokoh di daftar memperbarui sorotan dan panel detail, begitu juga sebaliknya.

### Panel detail tokoh

Judul nama tokoh, lalu "Disebut sebagai" dan "Kemunculan". Mode Lanjutan menambahkan label entitas, nomor kelompok, dan model yang dipakai.

Pada tahap ini jangan menampilkan skor keyakinan atau persentase, karena model klasifikasi belum menghasilkan probabilitas. Sisakan ruang tata letak agar skor bisa ditambahkan kelak tanpa mengubah struktur panel.

### Umpan balik

| Keadaan | Tampilan | Contoh teks |
|---|---|---|
| Kosong | Penjelasan singkat dan aksi | "Belum ada analisis. Tempel teks satua untuk memulai." |
| Memuat | Kerangka teks dan panel, tombol nonaktif, `aria-busy="true"` | "Menganalisis teks..." |
| Teks tidak valid | Pesan di bawah input | "Teks terlalu pendek. Masukkan minimal satu paragraf." |
| Tidak ada tokoh | Panel informasi `warning` | "Tidak ada tokoh yang dikenali. Periksa apakah teks berbahasa Bali." |
| Model gagal | Panel `danger`, teks masukan tetap tersimpan, tombol "Coba lagi" | "Analisis gagal karena model tidak merespons. Teks Anda tidak hilang." |
| Sesi berakhir | Arahkan ke halaman masuk dengan pesan | "Sesi Anda berakhir. Masuk lagi untuk melanjutkan." |

Jangan menampilkan persentase kemajuan palsu.

## Halaman

### Landing `/`

Urutan konten di kolom kiri:

1. Aksara Prasi
2. Judul: "Analisis tokoh satua Bali dalam satu ruang kerja."
3. Paragraf: "Kenali tokoh, satukan nama lain, dan lihat peran protagonis atau antagonis dari teks berbahasa Bali."
4. Kutipan contoh dengan sorotan peran

Kolom kanan berisi kartu masuk: pita ikat, judul "Masuk ke akun Anda", Email, Kata sandi, tombol "Masuk", dan "Buat akun baru". Di bawahnya tiga panel: "Kenali tokoh", "Satukan nama lain", dan "Lihat perannya".

Jangan menambahkan statistik, testimoni, logo mitra, atau klaim akurasi yang belum didukung data.

### Masuk dan daftar `/masuk`, `/daftar`

Satu kartu di tengah dengan aksara Prasi dan pita ikat. Penjelasan singkat, tanpa sidebar.

- Layout: `templates/allauth/layouts/entrance.html`, dipakai juga oleh halaman aktivasi (verifikasi email terkirim, konfirmasi email, reset kata sandi). Header tipis berisi nama produk di kiri serta pengalih bahasa (Indonesia/English, `aria-pressed`) dan tombol tema di kanan. Aksara Prasi di atas kartu, pita ikat di bagian atas kartu, tautan "Kebijakan privasi" di bawah kartu.
- Daftar: email, nama lengkap, institusi (opsional), peran, kata sandi dua kali, bahasa antarmuka, lalu kotak centang persetujuan dengan tautan ke `/privasi/`.

### Akun `/akun/profil`, `/akun/hapus`

Layout `templates/accounts/base_account.html` (juga untuk ganti kata sandi dan email dari allauth): header permukaan `surface` dengan pengalih bahasa, tombol tema, dan tombol "Keluar" (POST). Konten satu panel dengan lebar maksimal 720px dan navigasi Profil, Kata sandi, Email. Tanpa aksara Prasi dan pita ikat. Hapus akun memakai tombol bahaya dan konfirmasi kata sandi.

### Kebijakan privasi `/privasi`

Satu panel dengan lebar baca maksimal `72ch`, header yang sama dengan halaman akun.

### Ruang kerja analisis `/analisis`

Sidebar: "Analisis baru", "Riwayat analisis", "Korpus satua", "Panduan". Tampilkan hanya menu yang halamannya sudah berfungsi.

- **Sebelum analisis:** area teks, tombol "Muat contoh satua", dan tombol utama "Analisis teks". Mode Lanjutan menampilkan pilihan model.
- **Sesudah analisis:** kartu ringkasan, panel teks cerita, daftar tokoh, dan panel detail.

### Halaman lain

Riwayat dan korpus memakai tabel di dalam panel: kepala tabel `label` warna `muted`, baris dipisah `line`, hover `surface-selected`. Halaman panduan memakai lebar baca maksimal `72ch`.

## Bahasa antarmuka

- Pakai bahasa Indonesia yang sederhana, kalimat aktif, dan sentence case.
- Satu aksi memakai nama yang sama di seluruh alur: tombol "Analisis teks", status "Menganalisis...".
- Pesan kesalahan menjelaskan apa yang terjadi dan cara memperbaikinya, tanpa permintaan maaf.
- Istilah baku:

| Pakai | Jangan pakai |
|---|---|
| Tokoh | Entitas, di mode Sederhana |
| Kelompok tokoh | Cluster, character group |
| Disebut sebagai | Alias, di mode Sederhana |
| Protagonis, Antagonis | Predicted as |
| Teks cerita, satua | Input, dokumen |

## Implementasi

### Tailwind CSS v4

Build dengan standalone CLI (tanpa Node): `python scripts/tailwind.py build` (atau `watch`). Hasilnya `src/static/css/app.css` di-commit. File lengkap ada di `src/static/src/input.css`; blok di bawah adalah intinya, ditambah token ukuran huruf dan kelas formulir dari bagian "Formulir".

`static/src/input.css`:

```css
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));

:root {
  --bg: #F7F8FC; --surface: #FFFFFF; --surface-selected: #EEF0FB;
  --ink: #111A33; --muted: #56607A;
  --accent: #3341B8; --accent-hover: #2A36A0; --accent-press: #222C85; --on-accent: #FFFFFF;
  --line: #E1E5F0; --line-strong: #7A83A0;
  --protagonis: #0A4A61; --protagonis-bg: #E1F2F7;
  --antagonis: #B04E0C; --antagonis-bg: #FCEDE0;
  --danger: #B3261E; --danger-bg: #FDECEA;
  --success: #1B6B45; --success-bg: #E6F4EC;
  --warning: #7A5200; --warning-bg: #FDF3DC;
  color-scheme: light;
}

.dark {
  --bg: #0C1224; --surface: #141B33; --surface-selected: #1E2748;
  --ink: #EDF0FA; --muted: #A3ACC6;
  --accent: #A3AEFF; --accent-hover: #B6BFFF; --accent-press: #8E9AF5; --on-accent: #0C1224;
  --line: #2A3352; --line-strong: #737EA3;
  --protagonis: #A9E2F5; --protagonis-bg: #11323F;
  --antagonis: #EC9450; --antagonis-bg: #3E2613;
  --danger: #FFB4AB; --danger-bg: #40191A;
  --success: #8FDDB2; --success-bg: #123525;
  --warning: #F2C66D; --warning-bg: #3A2C0E;
  color-scheme: dark;
}

@theme inline {
  --color-*: initial;
  --color-transparent: transparent;
  --color-current: currentColor;
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-surface-selected: var(--surface-selected);
  --color-ink: var(--ink);
  --color-muted: var(--muted);
  --color-accent: var(--accent);
  --color-accent-hover: var(--accent-hover);
  --color-accent-press: var(--accent-press);
  --color-on-accent: var(--on-accent);
  --color-line: var(--line);
  --color-line-strong: var(--line-strong);
  --color-protagonis: var(--protagonis);
  --color-protagonis-bg: var(--protagonis-bg);
  --color-antagonis: var(--antagonis);
  --color-antagonis-bg: var(--antagonis-bg);
  --color-danger: var(--danger);
  --color-danger-bg: var(--danger-bg);
  --color-success: var(--success);
  --color-success-bg: var(--success-bg);
  --color-warning: var(--warning);
  --color-warning-bg: var(--warning-bg);

  --font-sans: "Schibsted Grotesk", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-aksara: "Noto Serif Balinese", serif;

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

@layer base {
  body { background: var(--bg); color: var(--ink); font-family: var(--font-sans); font-size: 15px; line-height: 1.5; }
  :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
}

@layer components {
  .btn { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 0 16px; border-radius: var(--radius-md); border: 1px solid var(--line); background: var(--surface); color: var(--ink); font-size: 14px; font-weight: 600; line-height: 1; cursor: pointer; transition: border-color 120ms cubic-bezier(0.2, 0, 0, 1), background-color 120ms cubic-bezier(0.2, 0, 0, 1); }
  .btn:hover { border-color: var(--muted); }
  .btn:disabled { opacity: 0.55; cursor: not-allowed; }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
  .btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
  .btn-primary:active { background: var(--accent-press); border-color: var(--accent-press); }

  .panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: 24px; }

  .input { width: 100%; min-height: 46px; padding: 0 12px; border: 1px solid var(--line-strong); border-radius: var(--radius-md); background: var(--bg); color: var(--ink); }
  .input[aria-invalid="true"] { border-color: var(--danger); }

  .entity { display: inline; padding: 1px 3px; border: 0; font: inherit; line-height: inherit; cursor: pointer; }
  .entity--protagonis { color: var(--protagonis); background: var(--protagonis-bg); border-bottom: 2px solid currentColor; }
  .entity--antagonis { color: var(--antagonis); background: var(--antagonis-bg); border-bottom: 2px dashed currentColor; }
  .entity[aria-pressed="true"] { outline: 2px solid currentColor; outline-offset: 1px; }

  .role { display: inline-block; padding: 3px 8px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; }
  .role--protagonis { color: var(--protagonis); background: var(--protagonis-bg); }
  .role--antagonis { color: var(--antagonis); background: var(--antagonis-bg); }
}

html[data-mode="simple"] .adv-only { display: none; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
}
```

### Tema dan mode

Tema terang adalah bawaan dan tidak mengikuti pengaturan sistem. Letakkan skrip ini langsung di `<head>`, sebelum CSS, agar tidak terjadi kilatan tema:

```html
<script>
  (function () {
    var theme = null, mode = null;
    try {
      theme = localStorage.getItem("prasibali-theme");
      mode = localStorage.getItem("prasibali-mode");
    } catch (e) {}
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.dataset.mode = mode === "advanced" ? "advanced" : "simple";
  })();
</script>
```

Tombol tema bertuliskan "Tema gelap" atau "Tema terang", sesuai tema yang akan dituju. Saat tema atau mode berubah, perbarui kelas atau atribut di `<html>`, simpan ke `localStorage`, dan perbarui `aria-pressed`.

### Django dan HTMX

Struktur bawaan, sesuaikan jika repositori sudah punya pola sendiri:

```text
templates/
  base.html                 # head, skrip tema, CSS, HTMX
  base_app.html             # sidebar dan header ruang kerja
  landing.html
  analysis/
    workspace.html
    partials/
      result.html           # kartu ringkasan, teks, tokoh, detail
      story_text.html
      character_list.html
      error.html
  partials/
    ikat.html
    theme_toggle.html
    mode_toggle.html
static/
  src/input.css
  css/app.css               # hasil kompilasi Tailwind
  js/analysis.js            # pilih tokoh dan navigasi keyboard
```

Pola analisis:

```html
<form hx-post="{% url 'analysis:run' %}"
      hx-target="#analysis-result"
      hx-swap="innerHTML"
      hx-indicator="#analysis-loading"
      hx-disabled-elt="find button[type=submit]">
  {% csrf_token %}
  ...
</form>
<div id="analysis-loading" class="htmx-indicator" role="status">Menganalisis teks...</div>
<section id="analysis-result" aria-live="polite"></section>
```

- View mengembalikan partial `result.html` untuk permintaan HTMX dan halaman penuh untuk permintaan biasa.
- Kegagalan model dikembalikan sebagai partial `error.html`, dan teks masukan tidak boleh hilang.
- Setelah hasil masuk, pindahkan fokus ke judul hasil.
- Pemilihan tokoh dilakukan di sisi klien lewat `data-group-id`, tanpa permintaan ke server.
- Kirim data tokoh ke JavaScript dengan `json_script`.

### Keamanan rendering

Teks satua adalah masukan pengguna. Bangun sorotan dari potongan teks dan posisi entitas, lalu render lewat autoescape Django:

```django
{% for seg in segments %}{% if seg.group_id %}<button type="button" class="entity entity--{{ seg.role }}" data-group-id="{{ seg.group_id }}" aria-pressed="false">{{ seg.text }}</button>{% else %}{{ seg.text }}{% endif %}{% endfor %}
```

Jangan memakai filter `|safe` pada teks pengguna, dan jangan menyisipkan tag ke teks dengan penggantian string.

## Lakukan dan hindari

| Lakukan | Hindari |
|---|---|
| Menampilkan hasil AI langsung pada teks cerita | Daftar hasil yang terpisah dari teks |
| Menampilkan hasil apa adanya dari model | Menyembunyikan atau memperbaiki hasil model di template |
| Memakai satu tombol utama per area | Banyak tombol berwarna aksen berdampingan |
| Memakai garis tipis dan jarak untuk memisahkan konten | Bayangan abu-abu di setiap kartu |
| Memakai ikon SVG garis dengan `aria-label` jika tanpa teks | Emoji sebagai ikon |
| Menulis data nyata atau keadaan kosong | Lorem ipsum, angka contoh, testimoni rekaan |

## Daftar periksa sebelum selesai

- [ ] Tidak ada warna, radius, atau ukuran huruf di luar token.
- [ ] Halaman benar di tema terang dan gelap, tanpa kilatan tema saat dimuat ulang.
- [ ] Mode Sederhana tidak menampilkan istilah teknis, dan pilihan mode tersimpan.
- [ ] Peran tokoh terbaca tanpa warna, lewat garis dan teks.
- [ ] Semua kontrol dapat dipakai dengan keyboard dan fokusnya terlihat.
- [ ] Tidak ada gulir horizontal pada lebar 390px, dan target sentuh minimal 44px.
- [ ] Keadaan kosong, memuat, gagal, dan tidak ada tokoh sudah ditangani.
- [ ] Teks pengguna tidak dirender dengan `|safe`.
- [ ] Tidak ada skor keyakinan, statistik, atau klaim yang tidak berasal dari sistem.
- [ ] Akun demo juri tersedia, dan kredensialnya tidak ada di repositori.

## Sebelum rilis publik

- [ ] Ejaan aksara Prasi divalidasi oleh ahli aksara Bali.
- [ ] Teks contoh satua diperiksa ulang terhadap dataset asli.
- [ ] Lisensi font dan aset dicantumkan di bagian Third-party Resources pada README.
