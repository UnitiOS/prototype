# Rancangan panduan agent per peran

> **Status: disetujui dan dibangun, 6 Oktober 2026** (hasil di §9). Langkah 4 dari
> urutan sesudah keputusan di `DESIGN_NOTES.md` §15. Dokumen kerja: setelah
> dibangun, ringkasannya pindah ke `REFACTOR_P2.md` dan `DESIGN_NOTES.md`,
> lalu dokumen ini dihapus.

## 1. Keadaan hari ini

- **Satu panduan untuk semua orang.** Panduan sudah mengajarkan "cari dulu di
  katalog, pakai ulang yang sudah ada". Tetapi panduan belum mengenal empat
  jenis modul. Ia tidak menjelaskan apa yang masuk pustaka umum, apa yang
  masuk modul komunitas, dan apa yang masuk aplikasi.
- **Agent bisa memulai modul jenis apa pun**, tetapi tidak ada yang
  memberitahunya jenis mana yang harus dipilih. Halaman Studio juga tidak
  menanyakannya. Kalau tidak disebut, modul baru menjadi modul komunitas.
- **Katalog yang dibaca agent tidak menyebut jenis modul.** Agent tidak bisa
  membedakan pustaka umum dari modul komunitas biasa.
- **Rencana** yang diajukan agent menyebut apa yang dibangun, dari catatan
  mana, angka apa yang keluar, dan apa yang belum bisa. Rencana itu tidak
  menyebut apa yang diambil dari koleksi bersama. Rencana juga tidak menyebut
  apa yang kurang dan seharusnya dibuat di tempat lain.
- **Pelajaran dari uji lingkungan kosong** (`UJI_LINGKUNGAN_KOSONG.md`):
  - agent memodelkan hanya untuk angka yang diminta, bukan untuk kejadian
    usahanya (siapa menyewa apa, kapan);
  - agent menjawab sendiri pertanyaan "apakah jaminan terkait penyewaan
    tertentu?", padahal seharusnya ditanyakan ke orangnya.
- **Panduan sudah 19.995 dari batas 20.000 karakter.** Tidak ada ruang untuk
  menambah apa pun tanpa memendekkan bagian lain atau menaikkan batasnya.

## 2. Yang diusulkan, singkatnya

1. **Peran mengikuti jenis modul yang dibuka**, bukan pengakuan orangnya.
2. **Satu panduan dengan satu bagian per peran.** Catatan pembuka di setiap
   pesan menyebut peran mana yang berlaku.
3. **Untuk modul baru, agent bertanya dulu**: untuk usaha ini saja, atau
   untuk dipakai banyak usaha?
4. **Rencana mendapat dua bagian baru**: apa yang diambil dari koleksi, dan
   apa yang kurang serta seharusnya ada di mana. Sistem menolak rencana yang
   diajukan sebelum agent mencari di katalog.
5. **Kalau penyusun aplikasi menemukan bagian umum yang belum ada**, agent
   menawarkan dua pilihan kepada orangnya, dan orangnya yang memilih.

## 3. Peran ditentukan dari jenis modul

Satu percakapan dengan agent selalu tentang satu modul. Jenis modul itu sudah
tercatat sejak langkah 2, jadi perannya sudah diketahui tanpa ditanyakan.

| modul yang dibuka | peran yang dibantu agent | yang ditekankan panduan |
|---|---|---|
| pustaka umum (`@uniti/...`) | penjaga inti | hanya yang dipakai hampir semua usaha |
| modul komunitas | pembuat modul | umum untuk satu jenis usaha, bukan untuk satu usaha |
| aplikasi | penyusun aplikasi | susun dari koleksi, buat hanya yang khusus usaha ini |
| core | tidak ada | core tetap ditulis tangan |

Pemilik proses, staf, dan pemeriksa tidak membangun modul, jadi mereka tidak
mendapat bagian di panduan ini. Pemilik proses tetap menyetujui rencana dan
contoh angka lewat percakapan, seperti sekarang.

**Kenapa satu panduan, bukan panduan terpisah per peran.** Petunjuk awal
agent dikirim di setiap panggilan model. Kalau isinya selalu sama, penyedia
model bisa menyimpannya dan menagih lebih murah. Peran cukup disebut di
catatan pembuka yang sudah ada ("modul ini dibuka, keadaannya begini"),
ditambah satu kalimat: "ini aplikasi usaha demo, Anda membantu
penyusunnya".

**Modul yang belum ada.** Jenisnya belum tercatat. Aturannya:
- nama `@uniti/...` berarti pustaka umum;
- selain itu, agent menanyakannya di tahap memahami kebutuhan, lalu memulai
  modul dengan jenis yang dijawab. Aplikasi wajib bernama sesuai nama
  usahanya (langkah 3), dan catatan pembuka menyebut nama usaha itu.

## 4. Isi panduan per peran

**Untuk semua peran:**
- Cari dulu di koleksi. Pihak (pelanggan, pemasok), barang, dan dokumen
  dengan baris diambil dari pustaka umum. Modul menunjuk ke sana; ia tidak
  membuat ulang atau menurunkannya.
- Rencanakan di sekitar kejadian usaha dan siapa yang terlibat (satu
  penyewaan oleh satu pelanggan, berisi beberapa alat), bukan hanya angka
  yang diminta hari ini. Angka berikutnya membutuhkan pijakan itu.
- Pertanyaan tentang sambungan (apakah jaminan menempel ke penyewaannya?)
  ditanyakan ke orangnya, tidak dijawab sendiri.
- Yang kurang disebut jenisnya dan pemiliknya. Kalau milik orang lain, ada
  tiga jalan: minta pemiliknya, salin ke nama sendiri, atau hubungkan dari
  modul atau aplikasi sendiri.

**Penjaga inti (pustaka umum):**
- hanya yang dipakai hampir semua usaha, sekecil mungkin;
- tanpa aturan hitung khusus satu jenis usaha;
- menyediakan peran, supaya modul lain bisa mengisinya.

**Pembuat modul (modul komunitas):**
- umum untuk satu jenis usaha (misalnya penyewaan), bukan untuk satu usaha;
- tidak menyebut nama usaha mana pun;
- contoh angka memakai orang dan barang rekaan;
- bentuknya harus cocok untuk usaha lain yang sejenis.

**Penyusun aplikasi (aplikasi):**
- susun dari koleksi dan sematkan versinya;
- buat hanya yang khusus usaha ini: aturan hitung yang menggabungkan modul,
  laporan yang diminta usaha ini, dan contoh dengan angka usaha ini sendiri;
- bagian umum yang belum ada: sebutkan, lalu tawarkan pilihan (§6).

Bahasa panduan tetap Inggris, tidak menyebut nama usaha mana pun, dan nama
yang juga ada di kode diambil dari kode, seperti aturan panduan sekarang.

## 5. Rencana yang lebih jelas

Kartu rencana di Studio mendapat dua bagian baru:

| bagian | contoh untuk Kemah Ceria |
|---|---|
| diambil dari koleksi | pelanggan dari pustaka umum; penyewaan dan jaminan dari modul penyewaan komunitas |
| kurang, dan seharusnya di tempat lain | "denda keterlambatan" berlaku umum untuk penyewaan, jadi seharusnya ada di modul penyewaan (milik komunitas). Pilihan: dibuat di aplikasi ini dulu, atau menunggu |

**Sistem menolak rencana yang diajukan sebelum agent mencari di katalog**
dalam percakapan itu. Ini satu-satunya aturan baru yang dicek mesin. Sisanya
panduan, dan baru bisa diukur di uji dua babak (langkah 5).

Katalog yang dibaca agent juga akan menyebut jenis setiap modul: pustaka
umum, modul komunitas, atau aplikasi usaha ini.

## 6. Kalau bagian umum belum ada di koleksi

Misalnya penyusun aplikasi Kemah Ceria butuh denda keterlambatan, dan modul
penyewaan komunitas belum mencatatnya. Agent menyebutnya di rencana, lalu
orangnya memilih:

- **dibuat di aplikasi ini dulu.** Langsung bisa dipakai, tetapi hanya usaha
  ini yang memakainya. Kalau nanti modul komunitas menambahkannya, data lama
  tetap tercatat di aplikasi.
- **menunggu.** Agent berhenti di bagian itu. Pembuat modul menambahkannya ke
  modul komunitas, lalu aplikasi menyematkan versi barunya.

Agent tidak memilihkan. Di uji dua babak, babak 1 sudah menyiapkan koleksi,
jadi keadaan ini diharapkan jarang terjadi.

## 7. Ruang panduan dan batas yang perlu diketahui

**Ruang.** Bagian per peran dan aturan "cari dulu" menambah sekitar 2.000
karakter. Ada dua jalan:

- **naikkan batas ke 22.000 karakter.** Petunjuk awal menjadi sekitar 10%
  lebih panjang. Tambahannya kira-kira 500 token per panggilan, jadi biaya
  naik kurang dari satu sen per permintaan;
- **tetap 20.000**, dengan memindahkan satu bagian (misalnya penjelasan
  "lubang" di draft) ke topik yang dibaca agent hanya saat perlu. Risikonya,
  agent lebih sering memanggil untuk membaca topik itu, atau salah
  memahaminya.

Saran saya: naikkan ke 22.000.

**Batas:**
- Langkah ini sebagian besar panduan. Mesin hanya mengecek tiga hal: peran
  dari jenis modul, jenis modul baru, dan "cari dulu sebelum merencanakan".
- Membangunnya tidak memakai panggilan model. Test memakai model tiruan.
  Hasil nyatanya baru terlihat di uji dua babak (langkah 5), yang memakai
  model dan akan saya umumkan dulu batas panggilan, biaya, dan waktunya.
- **Yang tidak masuk langkah ini:**
  - fitur "salin ke nama sendiri";
  - mengusulkan perubahan ke modul milik orang lain dari percakapan;
  - membantu pemilik proses, staf, dan pemeriksa;
  - pengecekan mesin bahwa modul komunitas tidak menyebut nama usaha.

## 8. Yang perlu diputuskan pemilik

1. **Peran mengikuti jenis modul yang dibuka**, tanpa orangnya memilih
   peran?
2. **Satu panduan dengan bagian per peran**, dan perannya disebut di catatan
   pembuka? Atau panduan terpisah per peran?
3. **Untuk modul baru, agent menanyakan** "untuk usaha ini saja atau untuk
   banyak usaha" sebelum memulai? Atau halaman Studio yang menanyakannya
   saat nama modul diisi?
4. **Rencana mendapat dua bagian baru**, dan sistem menolak rencana yang
   diajukan sebelum agent mencari di katalog?
5. **Bagian umum yang belum ada**: agent menawarkan dua pilihan (dibuat di
   aplikasi dulu, atau menunggu), dan orangnya yang memilih?
6. **Batas panduan dinaikkan ke 22.000 karakter**? Atau tetap 20.000 dengan
   memindahkan satu bagian?

## 9. Hasil (6 Oktober 2026)

Pemilik menyetujui keenam keputusan di §8 sesuai saran, dan meminta agar
pemeriksaan juga memakai agent sungguhan, asal dikendalikan dan diawasi.

**Yang dibangun:**
- **Panduan mendapat bagian "kinds"** di petunjuk awal: tiga jenis modul
  yang dibangun, peran yang dibantu masing-masing, dan aturan untuk semua
  peran (cari dulu, pihak dan barang dan dokumen dari pustaka umum,
  rencanakan di sekitar kejadian usaha, tanyakan sambungan, sebut yang
  kurang). Contohnya memakai pesanan dan pembayaran, bukan penyewaan, supaya
  uji dua babak tidak diberi jawaban.
- **Catatan pembuka setiap permintaan menyebut jenis modul yang dibuka**:
  "bagian pustaka umum, Anda membantu penjaganya", "modul komunitas, Anda
  membantu pembuatnya", atau "aplikasi usaha demo, Anda membantu
  penyusunnya". Untuk modul yang belum ada: nama `@uniti/...` dimulai sebagai
  pustaka umum; selain itu agent diminta bertanya dulu.
- **Katalog yang dibaca agent menyebut jenis setiap modul.**
- **Rencana mendapat dua bagian**: "diambil dari koleksi" dan "kurang, dan
  seharusnya di mana". Kartu rencana di Studio menampilkannya.
- **Rencana sebelum mencari di katalog dikembalikan ke agent**, sebelum
  sampai ke orangnya.
- **Batas panduan naik ke 22.000 karakter.** Sekarang 21.983.

**Test:** 1 test baru untuk catatan pembuka per jenis modul; test rencana
sekarang memeriksa bahwa rencana sebelum mencari di katalog dikembalikan;
test katalog memeriksa jenis modul. 336 test Python dan 42 test tampilan
lulus.

**Pemeriksaan dengan agent sungguhan** (Gemini 3.8 Flash, salinan toko
pemeriksaan dan kernel `uniti_appcheck`, batas 15 panggilan dan $0,10 per
permintaan). Pemilik toko kue membuka modul baru `@demo/orders` dan meminta
total nilai pesanan per pelanggan.

| permintaan | yang terjadi | panggilan | biaya |
|---|---|---|---|
| 1 | mencari di katalog lebih dulu, menemukan pustaka umum, lalu bertanya: khusus usaha ini atau untuk banyak usaha? | 6 | $0,03 |
| 2 ("khusus toko saya") | bertanya cukup total per pelanggan atau juga per pesanan | 4 | $0,04 |
| 3 ("cukup per pelanggan") | rencana: pelanggan, barang, dan bentuk transaksi diambil dari pustaka umum | 1 | $0,02 |
| 4 (rencana diajukan ulang) | rencana yang sama | 1 | $0,02 |

Total 12 panggilan, $0,11, sekitar 3 menit.

**Temuan:**
- Bertanya jenis modul, mencari dulu, dan mengambil dari pustaka umum
  berjalan seperti yang diminta.
- **Bagian "seharusnya di tempat lain" tetap kosong.** Pesanan dengan
  baris berlaku umum untuk usaha yang menjual, jadi seharusnya disebut
  sebagai calon modul komunitas, dengan pilihan "buat di aplikasi dulu atau
  menunggu". Sesudah permintaan 3, panduan dipertegas: yang dicatat setiap
  usaha sejenis (pesanan, pembayaran) bukan milik satu usaha. Permintaan 4
  hanya mengulang rencana dari percakapan, jadi belum membuktikan apakah
  kalimat itu bekerja. Ini dilihat lagi di uji dua babak.
- Agent sekali membuka bagian panduan yang sudah ada di petunjuk awalnya.
  Sistem menjawab "sudah ada"; biayanya kecil, tetapi tetap satu putaran.

**Dicek di Chrome** (server pemeriksaan port 8208 di atas salinan toko yang
sama, tanpa panggilan model): kartu rencana `@demo/orders` menampilkan
"Taken from what others built". Bagian "Missing, and where it belongs" tampil
setelah satu baris contoh diisi sementara di salinan percakapan. Bagian yang
kosong tidak ditampilkan. Server sudah dimatikan.
