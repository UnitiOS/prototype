# Rencana uji dua babak: komunitas membuat, pemilik usaha menyusun

> **Status: disetujui 7 Oktober 2026, sedang berjalan** (hasil di §9). Langkah 5 dari
> urutan sesudah keputusan di `DESIGN_NOTES.md` §15. Ini lanjutan uji
> lingkungan kosong (`UJI_LINGKUNGAN_KOSONG.md`), yang dihentikan sesudah
> langkah 3 karena mencampur tiga peran sekaligus. Dokumen kerja: hasilnya
> nanti pindah ke `REFACTOR_P2.md`, lalu dokumen ini dihapus.

## 1. Pertanyaannya

Uji pertama menunjukkan modul jaminan terputus dari modul sewa. Penyebabnya
lapisan yang belum ada, bukan hanya agent. Keempat lapisan itu sekarang ada:
pustaka umum, aplikasi sebagai jenis tersendiri, pemilik nama, dan panduan
menurut jenis modul. Uji ini menanyakan apakah susunan itu bekerja kalau
peran dipisah:

1. **Babak 1:** bisakah agent membantu pembuat modul komunitas membuat modul
   penyewaan yang **umum**? Umum artinya: tanpa nama usaha, memakai pihak,
   barang, dan bentuk transaksi dari pustaka umum, dan penyewaan dicatat
   sebagai satu kejadian berisi beberapa baris.
2. **Babak 2:** bisakah agent membantu pemilik Kemah Ceria menyusun
   aplikasinya **dari koleksi itu**? Ia hanya membuat yang khusus usahanya,
   menyebut yang kurang, dan angkanya cocok dengan kebenaran.
3. Bisakah aplikasi direvisi dan modulnya ditukar dengan buatan penulis lain,
   dengan data yang sudah berjalan, tanpa kehilangan catatan lama?

## 2. Lingkungan

Semuanya baru dan terpisah dari lingkungan pengembangan dan uji pertama.

| | babak 1: komunitas | babak 2: Kemah Ceria |
|---|---|---|
| kernel | `uniti_komunitas` (bukan milik usaha mana pun) | `uniti_kemah` (dinyatakan milik usaha `kemahceria` oleh Sari) |
| tempat modul | `build/dua/komunitas` (koleksi bersama) | `build/dua/kemahceria` (pribadi), ditambah koleksi bersama |
| server uji | port 8210 | port 8211 |

- **Pustaka umum dan inti** dibaca dari `packages`. Di kernel komunitas,
  nama `@uniti` diberi pemilik "penjaga" lewat langkah penyiapan, supaya
  tidak bisa diambil orang lain.
- **Pengaturan agent tersendiri** (`build/dua/agent.yaml`). `config/agent.yaml`
  tidak diubah.
- **Model:** Gemini 3.8 Flash untuk agent dan akuntan.
- **Hanya satu server yang menyala pada satu waktu.** Bila server berhenti,
  pemilik diberi tahu dan server tidak dinyalakan ulang diam-diam.

## 3. Peran

Claude memerankan tiga orang. Tidak satu pun dari mereka menyebut nama
kelas, kolom, atau modul, dan tidak ada yang membetulkan pekerjaan agent
dengan tangan.

| orang | babak | menulis sebagai |
|---|---|---|
| **Rudi**, pembuat modul di komunitas penyewaan | 1 | orang yang paham usaha sewa-menyewa secara umum, bukan satu toko |
| **Sari**, pemilik Kemah Ceria | 2 | pemilik usaha kecil, bahasa sehari-hari |
| **Penulis SewaPro** (fiktif) | 2, langkah 2.5 | modulnya ditulis dengan tangan di Studio, tanpa agent |

Persetujuan rencana, contoh, pembekuan, dan pemasangan aplikasi dilakukan
oleh orang yang berperan, lewat tombol di Studio dan halaman Aplikasi.
Kebenaran tersembunyi tidak pernah terlihat oleh agent.

## 4. Babak 1: komunitas membuat modul umum

**Langkah 1.1 — modul penyewaan.** Permintaan Rudi:
*"Saya mau membuat modul untuk usaha penyewaan barang, yang bisa dipakai
toko sewa mana pun. Usahanya membeli barang untuk disewakan. Pelanggan
menyewa beberapa barang sekaligus, lalu mengembalikannya beberapa hari
kemudian. Yang ingin diketahui: berapa barang yang dimiliki, sedang disewa,
dan ada di gudang, per jenis barang."*

**Langkah 1.2 — jaminan.** Permintaan Rudi, sesudah 1.1 dibekukan:
*"Toko sewa biasanya meminta uang jaminan saat menyewa, dan
mengembalikannya saat barang kembali. Saya mau tahu jaminan yang masih
dipegang, per pelanggan."* Agent memilih sendiri: merevisi modul penyewaan,
atau membuat modul jaminan yang menunjuk ke penyewaan.

**Sengaja tidak diminta:** barang rusak dan hilang. Ini muncul di babak 2,
untuk melihat bagaimana bagian umum yang kurang ditangani.

**Yang diamati:**
- tidak ada nama usaha, dan contoh angkanya memakai orang dan barang
  rekaan;
- pelanggan dari pustaka umum (pihak) dan barang dari pustaka umum, bukan
  dibuat ulang;
- penyewaan sebagai satu kejadian berisi beberapa baris (mengisi peran
  transaksi dan baris transaksi);
- jaminan menempel ke penyewaannya, dan agent menanyakannya ke Rudi bila
  belum jelas;
- rencana menyebut apa yang diambil dari pustaka umum;
- peran pergerakan terisi untuk jumlah barang (di uji pertama terlewat).

Selesai bila modulnya dibekukan oleh Rudi. **Titik periksa pemilik**
sesudah babak 1: hasilnya dilaporkan dulu sebelum babak 2.

## 5. Babak 2: Kemah Ceria menyusun aplikasinya

Skenario usaha, transaksi, dan kebenarannya sama dengan uji pertama
(`UJI_LINGKUNGAN_KOSONG.md` §4 dan §5): lima jenis alat, transaksi 5–11
Oktober, dan kejadian rusak dan hilang pada 11 dan 13 Oktober.

**Langkah 2.1 — aplikasi pertama.** Sari membuka aplikasi baru
`@kemahceria/sewa`: *"Saya mau tahu berapa alat yang ada di gudang dan
berapa yang sedang disewa, per jenis alat."* Yang diamati:
- agent mencari dulu, menemukan modul Rudi, dan menyematkannya;
- yang dibuat di aplikasi hanya yang khusus Kemah Ceria;
- angka contohnya memakai alat dan orang Kemah Ceria.

Selesai bila dibekukan dan dipasang oleh Sari.

**Langkah 2.2 — transaksi diisi** lewat formulir (alat pertama di Chrome,
sisanya lewat alamat formulir yang sama), tanpa model. Kebenaran per 12
Oktober sama dengan uji pertama. **Titik periksa pemilik.**

**Langkah 2.3 — jaminan.** Sari, di aplikasi yang sama: *"Saya juga mau
tahu uang jaminan pelanggan yang masih saya pegang, per pelanggan."*
Aplikasi direvisi ke versi 2 dan memakai jaminan dari koleksi. Kebenaran
per 12 Oktober: Citra Rp500.000, Dewi Rp150.000, yang lain 0.

**Langkah 2.4 — rusak dan hilang.** Sari: *"Sekarang ada alat yang rusak
dan hilang. Yang rusak jangan dihitung siap disewa, yang hilang sudah bukan
milik saya."* Rusak dan hilang berlaku umum untuk penyewaan, jadi
diharapkan agent menyebutnya sebagai bagian yang kurang dan menawarkan dua
pilihan. Sari memilih sesuai keputusan pemilik (§8 nomor 4).
- **Kalau "menunggu":** Rudi merevisi modul penyewaan ke versi 2 di babak 1
  (server 8210), lalu Sari kembali ke aplikasinya dan menyematkan versi
  baru itu.
- **Kalau "buat di aplikasi dulu":** agent membuatnya di aplikasi Kemah
  Ceria.

Kejadian 11 dan 13 Oktober diisi sesudahnya. Kebenaran per 13 Oktober sama
dengan uji pertama (Sleeping bag milik toko 9; Matras rusak 1, siap disewa
9). Catatan minggu pertama tetap terhitung tanpa diisi ulang, dan contoh
versi sebelumnya tetap lulus.

**Langkah 2.5 — modul ditukar.** Penulis SewaPro menulis modul penyewaannya
sendiri dengan tangan di Studio (`@sewapro/...`), dengan nama berbeda tetapi
mengisi peran pustaka umum yang sama. Sari: *"Mulai besok penyewaan dicatat
lewat SewaPro. Tolong hitungan saya ikut membacanya."* Yang diamati:
- agent menyambungkan ulang aplikasinya;
- contoh usaha yang sama tetap lulus;
- agent jujur soal catatan lama, yang masih ada di kernel tetapi tidak lagi
  dibaca.

## 6. Batas waktu dan biaya

**Per permintaan:** 30 panggilan model, $0,30, dan 90 detik per panggilan.

| langkah | permintaan paling banyak | biaya paling banyak |
|---|---|---|
| 1.1 modul penyewaan | 8 | $1,50 |
| 1.2 jaminan | 5 | $0,80 |
| 2.1 aplikasi pertama | 6 | $1,00 |
| 2.2 transaksi | tanpa model | $0 |
| 2.3 jaminan di aplikasi | 5 | $0,70 |
| 2.4 rusak dan hilang (termasuk revisi Rudi bila menunggu) | 8 | $1,20 |
| 2.5 modul ditukar | 6 | $0,80 |
| **total** | **38** | **$6,00** |

- **Perkiraan wajar: $2–3.** Uji pertama memakai $0,47 untuk tiga langkah.
  Batas $6 masih di dalam sisa anggaran uji lingkungan kosong ($6,53 dari
  $7).
- **Waktu:** sekitar 4–6 jam kerja, dibagi 2–3 sesi. Ada dua titik periksa:
  sesudah babak 1, dan sesudah transaksi diisi di langkah 2.2.
- **Sebelum setiap langkah** saya sebutkan lagi batasnya. Sesudah setiap
  permintaan, jejaknya saya baca panggilan demi panggilan.

**Aturan berhenti:**
- satu langkah melewati batasnya: berhenti dan lapor;
- layanan model gagal tiga kali berturut-turut: berhenti dan lapor;
- agent melanggar urutan atau persetujuan: dicatat sebagai temuan dan uji
  berlanjut, karena sistem harus menolaknya.

## 7. Yang diukur di setiap langkah

- angka benar atau tidak, dibanding kebenaran;
- yang dipakai ulang dari koleksi, dan yang dibuat ganda;
- apakah yang kurang disebut, di jenis mana, dan pilihan ditawarkan;
- persetujuan yang diminta dengan benar, dan langkah yang ditolak sistem;
- mutu graph: peran terisi, satuan, keterangan, label berbahasa Indonesia;
- biaya, jumlah panggilan, dan waktu.

Kelemahan formulir yang dicatat di uji pertama (bahasa Inggris, nama
teknis, alamat yang harus dikarang) belum diperbaiki. Itu tidak diukur
ulang di sini, kecuali ada yang berubah.

## 8. Yang perlu diputuskan pemilik

1. **Babak 1 mulai dari pustaka umum yang sudah ada** (pihak, barang,
   transaksi), bukan dibuat ulang oleh agent? Saran: ya. Pustaka umum milik
   penjaga inti dan sudah dibekukan di langkah 1.
2. **Isi babak 1:** modul penyewaan umum, lalu jaminan, diminta Rudi dengan
   kata-kata umum. Rusak dan hilang sengaja tidak diminta. Saran: ya.
3. **Satu aplikasi Kemah Ceria yang direvisi bertahap**, bukan aplikasi baru
   untuk setiap pertanyaan? Saran: ya. Begitulah aplikasi dimaksudkan, dan
   ini yang dulu salah di uji pertama.
4. **Di langkah 2.4, Sari memilih "menunggu"**, sehingga Rudi merevisi modul
   komunitas dan Sari menyematkan versi baru? Atau "buat di aplikasi dulu"?
   Saran: menunggu. Jalan ini menguji perpindahan antar pemilik, yang
   menjadi inti susunan baru. Biayanya sedikit lebih besar dan sudah masuk
   batas langkah 2.4.
5. **Batas biaya:** 30 panggilan dan $0,30 per permintaan, total $6, dengan
   perkiraan wajar $2–3?

## 9. Hasil

Pemilik menyetujui kelima keputusan di §8 sesuai saran (7 Oktober 2026).

**Persiapan (tanpa model).**
- Docker dinyalakan. Kernel `uniti_komunitas` dan `uniti_kemah` (masing-masing
  dengan `_ops`) dibuat baru oleh `build/dua/setup.py`. Inti v1 dan v2 serta
  pustaka umum didaftarkan ke keduanya. `@uniti` dimiliki "penjaga" di
  keduanya; kernel Kemah Ceria dinyatakan milik usaha `kemahceria` oleh Sari,
  jadi Sari pemilik pertama nama `@kemahceria`.
- Tempat modul `build/dua/komunitas` dan `build/dua/kemahceria` kosong.
- Pengaturan agent `build/dua/agent.yaml`: 30 panggilan, 1 juta token, $0,30
  per permintaan, 90 detik per panggilan.
- Server babak 1 menyala di port 8210.

**Langkah 1.1 — modul penyewaan (`@komunitas/penyewaan`).**

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | membaca katalog, lalu bertanya: pengembalian per barang (bisa sebagian) atau selalu semua sekaligus? Rudi: per barang | 2 | $0,02 |
| 2 | rencana: pembelian, penyewaan, dan pengembalian, masing-masing satu kejadian dengan rinciannya; pelanggan, pemasok, barang, dan bentuk transaksi dari pustaka umum | 1 | $0,02 |
| 3 | Rudi minta pengembalian menyebut penyewaannya; rencana diperbarui, lalu disetujui | 1 | $0,01 |
| 4 | struktur modul dan satu contoh (kamera dan lensa rekaan) dari akuntan; berhenti di batas anggaran permintaan | 23 | $0,26 |
| 5 | Rudi menyetujui contoh; rumus ditulis dan contoh lulus | 9 | $0,10 |

Total 5 permintaan, 36 panggilan, $0,40, sekitar 9 menit. Dibekukan sebagai v1
oleh Rudi lewat Studio. Rudi menjadi pemilik `@komunitas` karena yang
pertama membekukan di bawahnya.

Yang baik:
- tidak ada nama usaha; contoh memakai barang rekaan;
- pelanggan dan pemasok dari pihak, barang dari pustaka umum; tidak ada yang
  dibuat ulang;
- pembelian dan penyewaan mengisi peran transaksi, rinciannya mengisi peran
  baris transaksi;
- label bahasa Indonesia di semua tabel dan kolom;
- agent bertanya soal pengembalian sebagian sebelum merencanakan.

Temuan:
- **Pengembalian tidak menunjuk ke penyewaannya** di rencana pertama, dan
  agent tidak menanyakannya. Rudi yang meminta.
- **Peran pergerakan tidak diisi** untuk jumlah barang di rincian (sama
  seperti uji pertama). Pengembalian mengisi peran kejadian, bukan
  transaksi.
- **Contoh hanya membaca satu tanggal**, sesudah semua kejadian.
- **Kalimat contoh ditulis dalam bahasa Indonesia** dan diajukan ke Rudi.
  Sesudah disetujui, contoh terkunci untuk agent, dan standar meminta bahasa
  Inggris, jadi draft tertahan. Agent sempat mencoba menghapus contoh yang
  sudah disetujui; sistem menolaknya. Studio menyediakan kotak jawaban untuk
  pertanyaan itu, dan Rudi menuliskannya dalam bahasa Inggris (dikirim lewat
  jalur langkah Studio yang sama), dengan kalimat Indonesianya sebagai label.
  Perbaikan sistem yang perlu: pengajuan contoh seharusnya tertahan sebelum
  sampai ke orangnya bila kalimatnya bukan bahasa Inggris.
- Permintaan 4 memakai hampir seluruh anggaran per permintaan; percakapan
  yang terus dikirim ulang membuat setiap panggilan makin besar (hingga 48
  ribu token masuk, sebagian besar dari cache).

**Langkah 1.2 — jaminan.** Rudi mengajukannya dari modul penyewaannya
sendiri, supaya agent bisa memilih merevisi atau menyarankan modul baru.

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | membaca katalog satu per satu, lalu bertanya: jaminan dicatat di penyewaan dan pengembalian, atau per barang? Rudi: di penyewaan dan pengembalian, Rupiah | 8 | $0,06 |
| 2 | rencana: revisi modul penyewaan; jaminan diterima di penyewaan, dikembalikan di pengembalian; sisa per pelanggan | 1 | $0,01 |
| 3 | revisi dibuka, kolom jaminan ditambah, contoh dengan pelanggan rekaan dari akuntan | 9 | $0,10 |
| 4 | Rudi menyetujui contoh; rumus ditulis, kedua contoh lulus, diajukan siap dibekukan | 4 | $0,03 |

Total 4 permintaan, 22 panggilan, $0,20, sekitar 15 menit. Dibekukan
sebagai v2 oleh Rudi.

Yang baik:
- agent memilih merevisi modul penyewaan, jadi **jaminan menempel ke
  penyewaannya**; inilah yang terputus di uji pertama;
- jaminan yang dikembalikan dihitung ke pelanggan lewat penyewaan yang
  dirujuk pengembalian (satu lompatan);
- kalimat contoh kali ini dalam bahasa Inggris; contoh v1 tetap lulus.

Temuan:
- **Model lambat:** satu panggilan 207 detik, padahal batasnya 90 detik;
  beberapa lainnya 40–56 detik.
- Agent membaca katalog satu bacaan per panggilan (8 panggilan), padahal
  panduan meminta beberapa bacaan sekaligus.

**Babak 1 selesai:** 9 permintaan, 58 panggilan, $0,60, sekitar 25 menit.

**Langkah 2.1 — aplikasi pertama (`@kemahceria/sewa`), berhenti untuk keputusan.**
Server babak 2 di port 8211.

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | mencari di katalog ("sewa", "rental", "kemah"), menemukan modul Rudi, lalu bertanya: khusus Kemah Ceria atau untuk banyak usaha? Sari: khusus Kemah Ceria | 3 | $0,02 |
| 2 | rencana: semua catatan dan hitungan stok dari modul Rudi; alat, pelanggan, dan pemasok dari pustaka umum; tidak ada yang dibuat ulang | 3 | $0,05 |
| 3 | aplikasi dimulai, menyematkan modul Rudi; contoh dengan alat dan pelanggan Kemah Ceria, memeriksa tabel stok milik modul Rudi. Pengajuannya ditolak sistem ("draft belum mendeklarasikan apa pun"); agent lalu membuat ulang tabel stok di aplikasi | 18 | $0,21 |

**Temuan (sistem):** draft yang tidak mendeklarasikan kelas sendiri dianggap
kosong dan tidak bisa dibekukan. Untuk aplikasi, itu bertentangan dengan
maksudnya: aplikasi bisa saja hanya menyusun modul dan membawa contoh angka
usahanya sendiri. Aturan ini mendorong agent membuat ganda yang sudah ada.
Pembekuan sendiri tidak menolaknya; yang menahan adalah pembacaan Studio
("empty") dan pemeriksaan pengajuan agent.

Catatan kerja: klik pertama di Chrome tidak terkirim; menunggu 9 menit
karena alat tunggu saya, bukan sistem.

**Perbaikan sesudah langkah 2.1 (disetujui pemilik, tanpa model).**
- Aplikasi yang menyematkan modul selain inti tidak lagi dianggap kosong,
  walaupun tidak mendeklarasikan kelas sendiri. Contohnya memeriksa tabel
  modul yang disematkan. Studio tidak lagi menanyakan "jenis apa yang
  dikenal modul ini" untuk aplikasi seperti itu (`studio.read.composes`).
- Catatan pembuka untuk aplikasi menyebutnya: aplikasi boleh tidak
  mendeklarasikan apa pun, dan contohnya bisa memeriksa tabel modul yang
  disematkan.
- 1 test baru di `tests/modules/test_library.py`.
- Draft lama dibuang lewat langkah Studio, server 8211 dinyalakan ulang, dan
  langkah 2.1 diulang dari awal.

**Langkah 2.1 diulang.**

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | mencari di katalog, bertanya khusus Kemah Ceria atau umum; Sari: khusus Kemah Ceria | 2 | $0,02 |
| 2 | rencana: semua dari koleksi, bahasanya awam tanpa nama modul | 3 | $0,03 |
| 3 | aplikasi dimulai dan menyematkan modul Rudi; **tidak ada tabel ganda**; contoh Kemah Ceria (tenda dome dan matras, Andi dan Budi) memeriksa tabel stok milik modul Rudi dan lulus; diajukan siap dibekukan | 12 | $0,11 |

Sari menyetujui contoh dan membekukan `@kemahceria/sewa` v1 di Studio (yang
boleh membekukan hanya Sari, dan formulirnya menyebutkan itu). Lalu Sari
memasangnya di halaman Aplikasi, berlaku mulai 1 Oktober 2026.

Langkah 2.1 seluruhnya (percobaan pertama dan ulangan): 6 permintaan, 41
panggilan, $0,44.

Temuan tampilan: sesudah contoh disetujui, tombol pembekuan baru muncul
setelah halaman dimuat ulang (dua kali terjadi, di babak 1 dan 2).

**Langkah 2.2 — transaksi minggu pertama (tanpa model).**
- Alat pertama ("Tenda 4 orang") diisi lewat formulir di Chrome. Sisanya
  dikirim ke alamat formulir yang sama (`build/dua/week1.py`): 5 pihak, 4
  alat, 2 pembelian, 5 penyewaan, 3 pengembalian, masing-masing dengan
  rinciannya, plus jaminan di penyewaan dan pengembalian. Total 46 catatan.
- Formulir aplikasi Kemah Ceria berasal dari modul Rudi v2, jadi kolom
  jaminan sudah ada; jaminan dicatat sekarang, seperti staf akan
  mengisinya.

Angka per 12 Oktober, **cocok semua dengan kebenaran**:

| alat | milik toko | sedang disewa | di gudang |
|---|---|---|---|
| Tenda 4 orang | 6 | 4 | 2 |
| Tenda 2 orang | 4 | 0 | 4 |
| Kompor portabel | 7 | 3 | 4 |
| Sleeping bag | 10 | 8 | 2 |
| Matras | 10 | 0 | 10 |

Jaminan dipegang per 12 Oktober: Andi 0, Budi 0, Citra Rp500.000, Dewi
Rp150.000, **cocok**. Per 7 Oktober angkanya juga benar (alat Andi dan Budi
masih di luar). Halaman Aplikasi menunjukkan setiap kolom berasal dari
`@komunitas/penyewaan`. Kelemahan formulir dari uji pertama masih sama:
alamat catatan harus dikarang, nama kolom berbahasa Inggris, baris tabel
menampilkan alamat (`kc:kompor`), bukan nama alat.

**Langkah 2.3 — jaminan di aplikasi.** Sari, di percakapan aplikasinya:
*"Saya juga mau tahu uang jaminan pelanggan yang masih saya pegang, per
pelanggan."*

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | mencari di katalog (aplikasinya sendiri, "jaminan", "deposit", lalu modul Rudi); rencana: **memakai tabel jaminan yang sudah ada** di modul Rudi, hanya menambah contoh Kemah Ceria; tidak ada bagian yang kurang | 3 | $0,03 |
| 2 | revisi dibuka; satu contoh jaminan (Citra Rp200.000 diterima lalu dikembalikan, Dani Rp150.000 masih dipegang) memeriksa tabel jaminan milik modul Rudi dan lulus; kalimat contohnya berbahasa Inggris; diajukan siap dibekukan | 7 | $0,05 |

- Agent **menyadari jawabannya sudah ada**: tidak ada tabel atau kolom
  baru, perubahan v1 ke v2 hanya satu contoh.
- Sari menyetujui contoh dan membekukan v2. Tombol pembekuan lagi-lagi baru
  muncul setelah halaman dimuat ulang (ketiga kalinya).
- Sari memasang v2 berlaku mulai 8 Oktober 2026. Tanggal ini dipilih supaya
  versi berikutnya (rusak dan hilang, kejadian pertama 11 Oktober) bisa
  dipasang sesudahnya tanpa tumpang tindih. Per 7 Oktober yang dipakai masih
  v1, per 9 Oktober v2. Catatan minggu pertama tidak diisi ulang.

Angka per 12 Oktober lewat v2, **cocok semua**: jaminan Andi 0, Budi 0,
Citra Rp500.000, Dewi Rp150.000; stok kelima alat sama dengan tabel langkah
2.2.

Langkah 2.3: 2 permintaan, 10 panggilan, $0,08 (batas $0,70). Total sejauh
ini $1,12 dari $6.

**Langkah 2.4 — rusak dan hilang.** Sari, di percakapan aplikasinya:
*"Sekarang ada alat yang rusak dan hilang. Yang rusak jangan dihitung siap
disewa, yang hilang sudah bukan milik saya."*

| siapa | permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|---|
| Sari | 1 | mencari di katalog (aplikasinya, modul Rudi, "rusak", "hilang", "damage", "loss"); rencana menyebut **rusak dan hilang sebagai bagian umum yang semestinya ada di modul komunitas**, dan menawarkan dua pilihan: dibangun di aplikasi dulu, atau menunggu | 12 | $0,13 |
| Sari | 2 | Sari memilih menunggu; agent tidak mengubah apa pun, aplikasi tetap v2 | 1 | $0,01 |
| Rudi | 3 | (server 8210) agent bertanya: rusak dan hilang dicatat tersendiri atau di pengembalian, dan apakah perbaikan dicatat; Rudi: hilang saat disewa dicatat di pengembalian, rusak dan perbaikan dicatat tersendiri | 6 | $0,04 |
| Rudi | 4 | rencana: catatan kerusakan, catatan perbaikan, jumlah hilang di baris pengembalian; stok per barang menghitung milik, disewa, gudang, rusak, siap disewa | 2 | $0,05 |
| Rudi | 5 | revisi ke v3 dibangun; contoh baru (kamera dan tripod, satu kamera hilang, tripod rusak lalu satu diperbaiki) lulus; **contoh v1 dan v2 tetap lulus**; Rudi menyetujui dan membekukan v3 | 11 | $0,16 |
| Sari | 6 | (server 8211) "modul komunitas sudah diperbarui"; agent membaca modul Rudi v3 dan merencanakan pindah ke versi itu | 3 | $0,04 |
| Sari | 7 | revisi aplikasi ke v3: modul Rudi v2 diganti v3, plus satu contoh Kemah Ceria (tenda dome: hilang 1, rusak 2, diperbaiki 1) yang lulus; **dua contoh lama tetap lulus**; tidak ada tabel sendiri | 12 | $0,11 |

- Sari membekukan aplikasi v3 dan memasangnya mulai 11 Oktober. Per 9
  Oktober yang dipakai masih v2, per 11 Oktober v3.
- Kejadian diisi sesudahnya: matras rusak 11 Oktober lewat formulir di
  Chrome (pilihan barang di formulir menampilkan nama alat), lalu
  pengembalian Citra 13 Oktober (4 catatan, satu sleeping bag hilang) lewat
  alamat formulir yang sama (`build/dua/week2.py`).
- Pengembalian minggu pertama tidak punya isian "jumlah hilang", dan tetap
  terhitung 0. **Catatan minggu pertama tidak diisi ulang.**

Angka per 13 Oktober lewat v3, **cocok semua dengan kebenaran**:

| alat | milik toko | sedang disewa | di gudang | rusak | siap disewa |
|---|---|---|---|---|---|
| Tenda 4 orang | 6 | 1 | 5 | 0 | 5 |
| Tenda 2 orang | 4 | 0 | 4 | 0 | 4 |
| Kompor portabel | 7 | 1 | 6 | 0 | 6 |
| Sleeping bag | 9 | 2 | 7 | 0 | 7 |
| Matras | 10 | 0 | 10 | 1 | 9 |

Jaminan per 13 Oktober: Citra 0, Dewi Rp150.000, **cocok**.

Temuan:
- Tombol pembekuan masih baru muncul setelah halaman dimuat ulang (keempat
  dan kelima kalinya, di Studio komunitas dan Kemah Ceria).
- Peran pergerakan (Flow) masih belum terisi, walaupun kerusakan,
  perbaikan, dan hilang adalah pergerakan barang.
- Kerusakan dan perbaikan dibuat sebagai catatan satu barang, tanpa baris.
  Cukup untuk kebutuhan ini.
- Satu panggilan model makan 102 detik, padahal batasnya 90 detik.
- Bacaan katalog masih satu modul per panggilan (permintaan 1: 12
  panggilan).

Langkah 2.4: 7 permintaan (Sari 4, Rudi 3), 47 panggilan, $0,54 (batas 8
permintaan dan $1,20). Total sejauh ini $1,66 dari $6.

**Langkah 2.5 — modul ditukar (sedang berjalan).**

Persiapan tanpa model, di server komunitas (8210): penulis SewaPro menulis
`@sewapro/kasir` dengan tangan. Draft dimulai lewat formulir Studio di
Chrome, sisanya lewat langkah Studio yang sama (`build/dua/sewapro.py`, 85
langkah). Isinya pemesanan dan baris pemesanan (mengisi peran transaksi dan
baris transaksi), pengembalian di kasir dan barisnya (dengan jumlah yang
hilang), tabel barang yang sedang di luar, dan tabel jaminan per pelanggan.
Contohnya memakai kayak dan dayung dengan pelanggan rekaan, dan lulus.
Dibekukan oleh "sewapro", yang menjadi pemilik pertama `@sewapro`. SewaPro
sengaja tidak mencatat pembelian, kerusakan, atau perbaikan.

Sari, di aplikasinya (8211): *"Mulai besok, 14 Oktober, penyewaan dan
pengembalian dicatat lewat SewaPro. Tolong hitungan saya ikut membacanya."*

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | membaca SewaPro dan modul Rudi; menjawab **belum bisa**: tabel stok Rudi hanya membaca sewa lama, SewaPro tidak mencatat pembelian dan perbaikan, dan sistem tidak bisa menjumlah mulai tanggal tertentu. Jujur, tetapi melewatkan jalan menjumlah keduanya di aplikasi | 12 | $0,17 |
| 2 | Sari menjelaskan dengan bahasa usaha: pembelian, kerusakan, perbaikan tetap di tempat lama; sewa lama tetap dihitung, jumlahkan keduanya. Rencana: **dua tabel gabungan di aplikasi** (stok dan jaminan) yang membaca catatan lama dan SewaPro; menyebut penghubung ini semestinya ada di modul komunitas | 3 | $0,07 |
| 3 | revisi dibuka, SewaPro disematkan, kolom-kolom tabel stok disiapkan; **berhenti karena batas biaya per permintaan** ($0,30) | 9 | $0,25 |
| 4 | "silakan lanjutkan": tabel jaminan disiapkan, contoh gabungan (tenda dome dan Andi, sewa lama lalu SewaPro) diajukan; angkanya benar; Sari menyetujuinya | 5 | $0,14 |

Belum selesai: aturan hitungnya belum dipasang. Tiga contoh lama tetap
lulus. Sejauh ini 4 permintaan, $0,63 dari batas $0,80.

Temuan: satu panggilan pembangun makan 170 detik dan satu panggilan akuntan
141 detik, jauh di atas batas 90 detik.

Lanjutan (pemilik menaikkan batas langkah 2.5 menjadi $1,00):

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 5 | aturan tabel stok gabungan dipasang; 17 angka stok contoh gabungan lulus; berhenti lagi karena batas per permintaan (dua panggilan tidak terlayani cache, masing-masing sekitar $0,09) | 3 | $0,20 |
| 6 | batas per permintaan diturunkan sementara ke $0,17 supaya langkah tetap di bawah $1,00; agent langsung berhenti sesudah satu panggilan, karena pemeriksaan anggaran menyisakan ruang untuk dua panggilan berharga penuh (sekitar $0,09 masing-masing pada percakapan sepanjang ini) | 1 | $0,01 |

Sisa: 7 angka jaminan di contoh gabungan belum punya aturan. Langkah 2.5
sejauh ini $0,84.

Temuan: pada percakapan panjang (sekitar 110 ribu token), satu permintaan
hanya muat dua sampai tiga panggilan sebelum batas $0,30, walaupun biaya
nyatanya jauh lebih kecil bila cache melayani.

Penyelesaian (pemilik setuju satu permintaan lagi dengan batas $0,30):

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 7 | aturan jaminan gabungan dipasang; **24 angka contoh gabungan lulus**, tiga contoh lama tetap lulus; diajukan siap dibekukan | 3 | $0,13 |

- Sari membekukan v4 dan memasangnya mulai 14 Oktober. Per 13 Oktober yang
  dipakai masih v3, per 14 Oktober v4.
- Sewa sesudahnya dicatat lewat formulir SewaPro di aplikasi: pemesanan
  Budi 14 Oktober di Chrome (pilihan pelanggan menampilkan nama), sisanya
  lewat alamat formulir yang sama (`build/dua/week3.py`, 9 catatan).
  Kebenaran ditetapkan sebelum diisi: Budi memesan Tenda 2 orang ×2 dan
  Matras ×2 (jaminan Rp200.000); Citra memesan Tenda 4 orang ×2, Kompor ×1,
  Sleeping bag ×2 (jaminan Rp300.000); Budi mengembalikan Tenda 2 orang ×2
  dan Matras ×1, satu matras hilang, jaminannya kembali. Sewa lama Dewi
  (11 Oktober) masih di luar.

Angka per 16 Oktober lewat v4, **cocok semua**:

| alat | milik toko | sedang disewa | di gudang | rusak | siap disewa |
|---|---|---|---|---|---|
| Tenda 4 orang | 6 | 3 | 3 | 0 | 3 |
| Tenda 2 orang | 4 | 0 | 4 | 0 | 4 |
| Kompor portabel | 7 | 2 | 5 | 0 | 5 |
| Sleeping bag | 9 | 4 | 5 | 0 | 5 |
| Matras | 9 | 0 | 9 | 1 | 8 |

Jaminan per 16 Oktober: Andi 0, Budi 0, Citra Rp300.000, Dewi Rp150.000,
**cocok**. Per 13 Oktober tabel gabungan sama dengan kebenaran langkah 2.4.
Sewa lama Dewi tetap terhitung tanpa diisi ulang.

Temuan langkah 2.5:
- **Tabel stok lama milik modul Rudi masih tampil di aplikasi** dan per 16
  Oktober angkanya sudah tidak benar (tidak membaca SewaPro: Tenda 4 orang
  sedang disewa 1, seharusnya 3). Agent tidak memberi tahu Sari bahwa ada
  dua tabel stok dan mana yang dipakai.
- **Sewa lama tidak bisa dikembalikan lewat SewaPro**: pengembalian SewaPro
  hanya menunjuk pemesanan SewaPro. Pengembalian alat Dewi nanti harus
  dicatat di formulir lama. Agent tidak menyebutkannya.
- Jawaban pertama agent "belum bisa": jujur soal batasnya, tetapi baru
  menemukan jalan menjumlah keduanya setelah Sari menjelaskan dengan bahasa
  usaha.
- Percakapan panjang membuat setiap panggilan mahal bila cache tidak
  melayani, dan batas per permintaan menghentikan agent tiga kali.
- Di Chrome, alat pencari elemen kadang tidak melihat tombol pembekuan
  walaupun tombolnya ada (diklik lewat halaman).

Langkah 2.5: 7 permintaan, 36 panggilan, $0,97 (batas dinaikkan pemilik ke
$1,00).

**Total uji dua babak: $2,63 dari $6.** Babak 1 $0,60, langkah 2.1 $0,44,
2.3 $0,08, 2.4 $0,54, 2.5 $0,97.
