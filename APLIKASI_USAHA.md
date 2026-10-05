# Rancangan aplikasi sebagai jenis tersendiri, terikat ke kernel usahanya

> **Status: disetujui dan dibangun, 6 Oktober 2026** (hasil di §9).
> Langkah 2 dari urutan sesudah keputusan di `DESIGN_NOTES.md` §15. Dokumen
> kerja: setelah dibangun, ringkasannya pindah ke `REFACTOR_P2.md` dan
> `DESIGN_NOTES.md`, lalu dokumen ini dihapus.

## 1. Keadaan hari ini

- **Aplikasi belum dibedakan dari modul.** Aplikasi hanyalah versi beku yang
  menyematkan versi lain dan menyebut tabel yang dibutuhkan. Tidak ada yang
  menandainya sebagai aplikasi, apalagi sebagai milik satu usaha.
- **Satu server, satu kernel, satu toko modul.** Halaman Aplikasi
  menawarkan versi apa pun di toko. Formulir bisa menulis ke kernel lewat
  versi apa pun, termasuk modul komunitas yang tidak pernah dipilih usaha itu.
- **Kernel tidak tahu milik siapa dirinya.** Membekukan aplikasi Kemah Ceria
  ke kernel usaha lain tidak dicegah apa pun.
- **Membekukan dan mulai memakai belum dipisah.** Begitu dibekukan, sebuah
  versi langsung bisa dipakai untuk mencatat. Tidak ada catatan sejak kapan
  usaha memakainya, atau kapan ia diganti.

## 2. Yang diusulkan, singkatnya

1. **Aplikasi ditandai sebagai aplikasi**, milik satu usaha, di berkas
   keterangan modulnya.
2. **Kernel usaha menyatakan milik siapa dirinya**, satu kali saat
   disiapkan.
3. **Membekukan dan memasang adalah dua keputusan.** Membekukan berarti
   susunannya disetujui. Memasang berarti staf mulai mencatat lewat aplikasi
   itu sejak tanggal tertentu. Pemasangan dicatat di kernel usaha, jadi
   riwayatnya bisa ditanyakan dengan dua jam seperti angka lain.
4. **Aplikasi pribadi**: tidak masuk koleksi bersama, tidak bisa disematkan
   modul lain, dan tidak bisa dipasang di usaha lain.

## 3. Aplikasi sebagai jenis

Berkas keterangan (`package.yaml`) aplikasi menyebut dua hal baru:

```yaml
name: "@kemahceria/sewa"
kind: application
business: kemahceria
```

- `kind` hanya bisa satu dari empat: `core`, `library`, `module`,
  `application`. Tanpa `kind`, sebuah modul dianggap modul komunitas
  (`module`), jadi modul yang sudah ada tidak berubah.
- `business` wajib untuk aplikasi dan dilarang untuk jenis lain.
- Ini bukan bagian dari makna. Isi kelas dan slot tidak berubah. Yang berubah
  adalah siapa pemiliknya dan siapa yang boleh memakainya.

Yang ditegakkan:

| aturan | ditolak kalau |
|---|---|
| aplikasi tidak bisa disematkan | modul atau aplikasi lain mengimpor sebuah aplikasi |
| aplikasi tidak masuk koleksi bersama | katalog bersama dan pencarian agent tidak menampilkannya, kecuali di server usaha pemiliknya |
| aplikasi dibekukan ke kernel usahanya | kernel yang dipakai menyatakan milik usaha lain, atau belum menyatakan milik siapa |

Tambahan khusus satu usaha, seperti kelas yang hanya dipakai Kemah Ceria,
tinggal di aplikasinya sendiri. **Jenis "modul pribadi" belum dibuat**, karena
belum ada kebutuhan yang membuktikannya (aturan pertumbuhan §4.4).

## 4. Kernel usaha menyatakan milik siapa dirinya

Saat kernel disiapkan, satu pernyataan pertama ditulis: kernel ini milik usaha
`kemahceria`. Pernyataan ini dicatat seperti fakta lain di catatan yang hanya
bertambah, tanpa kolom baru dan tanpa tabel baru.

- Kernel yang belum menyatakannya bisa dibaca seperti biasa, tetapi tidak
  bisa menerima aplikasi.
- Kernel pengembangan (`uniti_dev`) menjadi milik usaha contoh `demo`.
  `@demo/stock` menjadi aplikasinya.

## 5. Memasang aplikasi

Memasang adalah satu pernyataan di kernel usaha: "aplikasi `@kemahceria/sewa`
v1 dipakai sejak 8 Oktober 2026". Yang ikut terjadi:

- **Kosakata semua versi yang dipakainya didaftarkan ke kernel usaha.** Ini
  isi "salinan kosakata dari versi yang dipakainya" di §15.5.
- **Mengganti ke v2** adalah pernyataan baru dengan tanggal mulai baru. V1
  tetap tercatat sebagai yang dipakai sebelumnya.
- **Mencabut** aplikasi adalah pencabutan pernyataan itu. Catatan
  transaksinya tetap ada, karena catatan milik usaha, bukan milik aplikasi.
- **Yang memasang adalah pemilik proses.** Agent tidak bisa memasang, sama
  seperti agent tidak bisa membekukan.

Akibatnya:

| | sebelum | sesudah |
|---|---|---|
| staf mengisi formulir | lewat versi apa pun di toko | hanya lewat aplikasi yang terpasang pada tanggal transaksinya |
| halaman Aplikasi | semua versi di toko | aplikasi yang terpasang lebih dulu; yang lain ditandai "pratinjau, belum dipasang" |
| "aplikasi apa yang dipakai pada bulan Agustus?" | tidak bisa dijawab | dibaca dari kernel, dengan dua jam |

Membaca angka lewat aplikasi yang belum dipasang tetap boleh, sebagai
pratinjau. Itulah cara pemilik melihat v2 terhadap data sungguhan sebelum
memutuskan pindah (§15.6 langkah 5).

## 6. Tempat tinggal toko pribadi

Toko pribadi usaha adalah **folder berkas tersendiri**, bukan isi kernel:

```
usaha/kemahceria/packages/@kemahceria/sewa/   aplikasi, pribadi
packages/@uniti/...                           core dan pustaka umum
<koleksi bersama>/@komunitas/...              modul komunitas
```

- Server satu usaha membaca folder pribadinya dulu, lalu koleksi bersama.
  Toko modul hari ini sudah bisa membaca beberapa folder berurutan, jadi
  tidak ada mesin baru.
- Berkas versi tidak pernah berubah, sama seperti di koleksi bersama.
  Peristiwanya (dibekukan, dipasang) tercatat di kernel usaha.
- Memindahkan toko pribadi ke dalam kernel tetap mungkin nanti, tanpa
  mengubah aturan di atas.

## 7. Dalam praktik

Dua server dengan dua kernel, persis bentuk babak uji ulang (langkah 5):

| server | membaca modul dari | kernelnya | dipakai oleh |
|---|---|---|---|
| komunitas | koleksi bersama | log komunitas (tempat pembekuan modul komunitas dicatat) | pembuat modul |
| Kemah Ceria | folder pribadi Kemah Ceria, lalu koleksi bersama | kernel Kemah Ceria | penyusun aplikasi, pemilik, Sari |

Satu server untuk satu usaha, seperti ERP yang satu database untuk satu
perusahaan. Satu server untuk banyak usaha urusan nanti; aturan di atas tidak
perlu berubah untuknya.

**Yang tidak masuk langkah ini:**
- aturan umum siapa boleh membekukan di bawah nama apa (langkah 3);
- panduan agent per peran (langkah 4);
- perbaikan formulir yang dicatat di uji lingkungan kosong;
- kernel Uniti sebagai catatan.

## 8. Yang perlu diputuskan pemilik

1. **Membekukan dan memasang dipisah**, dan pemasangan dicatat di kernel
   dengan tanggal mulai? Atau cukup "yang terakhir dibekukan langsung
   dipakai"?
2. **Staf hanya bisa mengisi lewat aplikasi yang terpasang**, sedangkan
   membaca lewat versi lain tetap boleh sebagai pratinjau?
3. **Satu aplikasi hanya untuk satu usaha.** Implementor yang ingin memakai
   susunan yang sama untuk banyak klien membuat modul komunitas, atau
   menyalinnya ke nama usaha klien. Setuju, atau aplikasi boleh menjadi
   templat yang dipasang di banyak usaha?
4. **Toko pribadi berupa folder berkas tersendiri** per usaha, bukan di dalam
   kernel?
5. **Belum ada jenis "modul pribadi"**: tambahan khusus usaha tinggal di
   aplikasinya?

## 9. Hasil (6 Oktober 2026)

Pemilik menyetujui kelima keputusan di §8 sesuai saran. Semuanya dibangun
pada hari yang sama, tanpa panggilan model.

- **Jenis di berkas keterangan.** `kind` (core, library, module, application)
  dan `business` untuk aplikasi. Core dan pustaka umum sekarang menyebut
  jenisnya; `@demo/stock` menjadi aplikasi milik usaha contoh `demo`. Modul
  yang tidak menyebut jenis tetap modul komunitas.
- **Aturan yang ditegakkan:**
  - aplikasi tidak bisa disematkan (`pins_an_application`);
  - aplikasi usaha lain tidak masuk katalog, termasuk aturan hitungannya,
    baik di halaman katalog maupun di pencarian agent;
  - aplikasi tidak bisa dibekukan, didaftarkan, atau dipasang ke kernel usaha
    lain (`wrong_business`) atau ke kernel yang belum menyatakan pemiliknya
    (`kernel_not_declared`);
  - kernel hanya bisa menyatakan pemiliknya satu kali (`kernel_owned`);
  - formulir hanya mencatat lewat versi yang terpasang untuk tanggal
    transaksinya (`not_installed`), dan penolakannya menyebut versi yang
    terpasang hari itu.
- **Memasang dan menghentikan** adalah pernyataan di kernel dengan tanggal
  mulai, dibaca dengan dua jam. Saat dipasang, kosakata semua versi yang
  disematkan aplikasi ikut didaftarkan. Mendaftarkan versi yang sudah dikenal
  kernel sekarang tidak menulis apa pun, termasuk catatan tindakan kosong.
- **Studio** bisa memulai aplikasi (`start` dengan `kind` dan `business`).
  Core tetap ditulis tangan. Panduan agent tetap di bawah 20.000 karakter
  (19.995) dengan satu kalimat dipendekkan.
- **Halaman Aplikasi** menawarkan aplikasi usaha ini lebih dulu, dimulai dari
  versi yang terpasang, dan menandainya "in use". Setiap versi menyebut
  apakah ia sedang dipakai, pratinjau, atau milik usaha lain. Versi yang belum
  dipakai punya formulir pemasangan untuk pemilik.
- **Test:** 8 test baru di `tests/business/test_business.py` dengan kernel
  kosong tersendiri, 1 test katalog baru, dan 2 test tampilan baru. Test
  pustaka sekarang mencatat lewat aplikasi kecil yang menyematkan modul
  sewa, dan membuktikan bahwa pencatatan lewat modulnya sendiri ditolak.
- **Dicek di Chrome** (server pemeriksaan port 8206, kernel sementara
  `uniti_appcheck`):
  - v2 terbuka otomatis sebagai "in use since 1 Jan 2026";
  - v4 tampil sebagai pratinjau dengan formulir pemasangan; dipasang mulai
    10 Oktober;
  - pada tanggal 12 Oktober v4 tampil sebagai yang dipakai;
  - formulir lewat v3 untuk 12 Oktober ditolak dengan pilihan "catat lewat
    v4" atau "minta pemilik memasang v3".

  Dari pemeriksaan ini ditambahkan dua hal: tanda "in use" di pilihan versi,
  dan konfirmasi sesudah memasang versi untuk tanggal yang akan datang.
  Server sudah dimatikan.
