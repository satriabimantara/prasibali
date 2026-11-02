# Logo PrasiBali

Konsep: **Lontar Naskah**. Huruf P dari bilah lontar berujung mata pengrupak, berisi baris goresan, dengan satu token merah sebagai entitas tokoh yang dikenali.

## Makna
- **Bilah lontar:** media prasi, tempat teks dan gambar berada pada satu lembar. Karena itu logo tetap relevan saat produk menjadi multimodal.
- **Ujung pengrupak:** ujung batang P meniru mata pisau untuk menggores lontar.
- **Baris goresan:** teks satua Bali yang dianalisis.
- **Token merah:** kata yang dikenali sebagai tokoh, seperti hasil NER. Bentuknya dapat disesuaikan untuk modalitas lain.
- **Siluet balon ucapan:** satua adalah tradisi tutur.

## Warna
| Nama | Hex | Pemakaian |
|---|---|---|
| Jelaga | #221C16 | Logo di latar terang, latar gelap |
| Lontar | #E8CF9C | Logo di latar gelap, latar ikon |
| Token terang | #D9603F | Token pada P jelaga |
| Token gelap | #B8432B | Token pada P lontar, favicon |

## Isi paket
- `svg/`: berkas master vektor. Semua teks sudah menjadi outline, jadi tidak perlu memasang font.
- `png/`: latar transparan. Tanda 1024, 2048, dan 4096 px; logo lebar 4096 px.
- `pdf/`: logo vektor untuk cetak.
- `app-icon/`: ikon aplikasi 1024 px, sudut bulat dan persegi.
- `web/`: favicon, ikon perangkat, manifest, gambar berbagi tautan, dan `head-snippet.html`.

Nama varian: `latar-terang`, `latar-gelap`, `hitam`, `putih`. `logo-aksara` memuat aksara Bali; `logo` tanpa aksara. Varian hitam dan putih dipakai untuk cetak satu warna, dan seluruh baris di dalam P berlubang mengikuti warna latar.

## Aturan pakai
- Jarak kosong di sekeliling logo minimal setinggi satu baris goresan dikali dua.
- Di bawah 32 px gunakan favicon; versi lengkap dengan aksara sebaiknya tidak dipakai di bawah lebar 200 px.
- Jangan mengubah warna, memiringkan, atau meregangkan logo.

## Sebelum dipublikasikan
Ejaan aksara Bali pada varian `logo-aksara` dan `og-image-aksara.png` belum divalidasi ahli. Mintakan pemeriksaan ke penyuluh bahasa Bali. Varian `logo` dan `og-image.png` tidak memuat aksara dan dapat dipakai lebih dulu.

## Kredit dan lisensi
- Tulisan Latin: Plus Jakarta Sans SemiBold, SIL Open Font License 1.1.
- Aksara Bali: Noto Sans Balinese Medium, SIL Open Font License 1.1.
- Logo dibuat bersama Claude (Anthropic) sebagai vektor SVG, untuk dicantumkan pada AI & Technology Disclosure.
