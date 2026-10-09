# Rancangan aturan siapa boleh membekukan di bawah nama apa

> **Status: disetujui dan dibangun, 6 Oktober 2026** (hasil di §9). Langkah 3 dari urutan
> sesudah keputusan di `DESIGN_NOTES.md` §15. Dokumen kerja: setelah
> dibangun, ringkasannya pindah ke `REFACTOR_P2.md` dan `DESIGN_NOTES.md`,
> lalu dokumen ini dihapus.

## 1. Keadaan hari ini

- **Nama depan modul** (`@uniti`, `@demo`, `@kemahceria`) hanya dicek
  bentuknya. Siapa pun yang menulis namanya di kolom "who freezes it" bisa
  membekukan versi baru `@uniti/party`.
- **Siapa yang membekukan memang dicatat**, di catatan tindakan kernel, tetapi
  tidak ada yang mencocokkannya dengan siapa pun.
- **Aplikasi sudah terikat ke usahanya** (langkah 2), tetapi namanya bebas:
  aplikasi usaha `demo` boleh bernama `@probe/shop`.
- **Belum ada login.** Orang dikenali dari nama yang ia tulis sendiri.

Akibatnya aturan §15.4 ("hanya pemilik sebuah nama yang boleh membekukan
versi baru di bawah nama itu") baru tertulis, belum dijalankan.

## 2. Yang diusulkan, singkatnya

1. **Setiap nama depan punya pemilik**: satu orang atau lebih. Ini dicatat di
   kernel sebagai pernyataan bertanggal, jadi bisa ditanyakan dengan dua jam
   ("siapa pemilik `@uniti` pada bulan Agustus?").
2. **Yang pertama membekukan di bawah nama baru menjadi pemiliknya.**
   Sesudah itu, hanya pemiliknya yang bisa membekukan di bawah nama itu.
3. **Pemilik bisa menambah dan mencabut pemilik lain.** Sebuah nama tidak
   pernah tanpa pemilik.
4. **Nama aplikasi adalah nama usahanya**: aplikasi usaha `kemahceria` harus
   bernama `@kemahceria/...`. Orang yang menyatakan pemilik kernel usaha
   menjadi pemilik pertama nama usaha itu.

## 3. Pemilik nama dicatat di kernel

Pernyataan "nama `@komunitas-sewa` dimiliki Budi sejak 8 Oktober 2026"
ditulis ke kernel tempat versi dibekukan, seperti pemasangan aplikasi di
langkah 2. Tidak ada kolom baru dan tidak ada tabel baru.

- **Kernel komunitas** mencatat pemilik nama modul komunitas, pustaka umum,
  dan core. Kernel usaha mencatat pemilik nama usahanya.
- **Mendaftarkan kosakata** versi milik orang lain ke kernel usaha tidak
  dicek pemilik namanya. Mendaftarkan bukan membuat; itu membaca karya orang
  lain.
- **Batasnya, sampai kernel Uniti ada:** setiap kernel menjaga nama sendiri.
  Dua kernel bisa saja mencatat pemilik berbeda untuk nama yang sama. Yang
  berlaku untuk koleksi bersama adalah kernel komunitas. Nanti kernel Uniti
  menjadi satu-satunya tempat nama dicatat (§15.5), dan aturannya tetap sama.

Pilihan lainnya adalah satu berkas di toko modul (`@uniti/owners.yaml`) yang
menyebut pemiliknya. Berkas ikut terbawa bersama modul, tetapi bisa diubah
siapa pun tanpa jejak. Karena itu kernel yang disarankan.

## 4. Cara sebuah nama mendapat pemilik

| keadaan | yang terjadi saat membekukan |
|---|---|
| nama belum pernah dimiliki | yang membekukan menjadi pemiliknya, di tindakan yang sama, dan tercatat terang |
| orang itu salah satu pemiliknya | dibekukan seperti biasa |
| orang lain | ditolak, dan tidak ada yang ditulis |

Penolakan menyebut pemilik nama itu dan memberi tiga jalan, sesuai §15.4:

- minta salah satu pemiliknya membekukan, atau menambahkan Anda sebagai
  pemilik;
- salin ke nama Anda sendiri;
- hubungkan lewat modul penghubung atau aplikasi Anda sendiri.

Agent tidak bisa membekukan, jadi agent tidak pernah menjadi pemilik nama.

**Data lama.** Kernel pengembangan sudah berisi versi yang dibekukan sebelum
aturan ini, oleh nama orang yang macam-macam. Di sana nama-nama itu belum
punya pemilik. Saat kernel pengembangan dibangun ulang, `@uniti` dan `@demo`
diberi pemilik dengan pernyataan yang jelas.

## 5. Menambah dan mencabut pemilik

- **Menambah** pemilik adalah pernyataan baru dari salah satu pemilik yang
  ada. Satu nama boleh punya beberapa pemilik, misalnya satu tim.
- **Mencabut** juga pernyataan, dan riwayatnya tetap. Versi yang dulu
  dibekukan orang itu tidak berubah.
- **Pemilik terakhir tidak bisa mencabut dirinya.** Kalau bisa, nama itu jadi
  tanpa pemilik, dan siapa pun yang membekukan berikutnya akan memilikinya.
- **Memindahkan nama** ke orang lain berarti menambah orang baru, lalu
  mencabut diri sendiri.

## 6. Nama aplikasi adalah nama usahanya

| | sekarang | sesudahnya |
|---|---|---|
| nama aplikasi usaha `kemahceria` | bebas | harus `@kemahceria/...` |
| pemilik pertama `@kemahceria` | tidak ada | orang yang menyatakan pemilik kernel usaha itu |
| penyusun aplikasi dari mitra implementor | membekukan atas nama siapa saja | ditambahkan sebagai pemilik `@kemahceria` oleh pemilik usaha |

Ini sejalan dengan keputusan langkah 2: implementor yang memakai susunan yang
sama untuk klien lain menyalinnya ke nama klien itu.

`@probe/shop` di test pustaka menjadi `@demo/shop`.

## 7. Batas yang perlu diketahui

- **Ini belum pengamanan.** Tanpa login, siapa pun bisa menulis nama orang
  lain. Aturan ini membuat catatan jujur dan mencegah salah langkah, misalnya
  agent atau orang yang salah nama membekukan di bawah `@uniti`. Login dan
  tanda tangan adalah langkah lain, nanti.
- **Membuat draft tetap bebas.** Siapa pun boleh mencoba di Studio di bawah
  nama apa pun. Aturan ini berlaku saat membekukan. Halaman Studio akan
  menyebut pemilik nama draft itu sejak awal, supaya tidak kaget di akhir.
- **Yang tidak masuk langkah ini:**
  - fitur "salin ke nama sendiri" (penolakan hanya menyebutnya sebagai
    jalan);
  - panduan agent per peran (langkah 4);
  - kernel Uniti sebagai satu tempat nama dicatat.

## 8. Yang perlu diputuskan pemilik

1. **Pemilik nama dicatat di kernel** sebagai pernyataan bertanggal? Atau
   cukup berkas di toko modul?
2. **Yang pertama membekukan di bawah nama baru otomatis menjadi
   pemiliknya**? Atau nama harus diklaim dulu sebagai langkah tersendiri?
3. **Pemilik bisa menambah dan mencabut pemilik lain**, dan pemilik terakhir
   tidak bisa mencabut dirinya?
4. **Nama aplikasi wajib sama dengan nama usahanya**, dan orang yang
   menyatakan pemilik kernel usaha menjadi pemilik pertama nama itu?
5. **Aturan berlaku saat membekukan saja**, sedangkan membuat draft tetap
   bebas?

## 9. Hasil (6 Oktober 2026)

Pemilik menyetujui kelima keputusan di §8 sesuai saran. Semuanya dibangun
pada hari yang sama, tanpa panggilan model.

- **Bagian baru `components/owners`.** Setiap pemilik sebuah nama adalah satu
  pernyataan di kernel dengan tanggal mulai. Mencabut juga pernyataan
  bertanggal, jadi riwayatnya tetap.
- **Saat membekukan:**
  - nama yang belum pernah dimiliki menjadi milik orang yang membekukan,
    dicatat di tindakan pembekuan itu sendiri;
  - pemiliknya membekukan seperti biasa;
  - orang lain ditolak (`not_an_owner`) sebelum berkas apa pun ditulis.
    Penolakannya menyebut pemilik nama itu dan tiga jalan keluar.
- **Menambah dan mencabut pemilik** hanya bisa dilakukan pemilik. Pemilik
  terakhir tidak bisa dicabut (`last_owner`).
- **Nama aplikasi adalah nama usahanya** (`name_not_the_business`). Orang
  yang menyatakan pemilik kernel usaha menjadi pemilik pertama nama usaha itu.
  Test pustaka memakai `@demo/shop`, bukan `@probe/shop` lagi.
- **Menyiapkan kernel.** Versi `@uniti` sampai di kernel usaha dengan cara
  didaftarkan, bukan dibekukan. Karena itu ada satu langkah penyiapan
  (`first`) yang memberi nama tanpa pemilik kepada satu orang. Kernel
  pengembangan memakainya untuk `@uniti`, supaya nama itu tidak jatuh ke
  orang pertama yang membekukan di bawahnya. Langkah ini tidak dibuka di
  halaman.
- **Mendaftarkan dan memasang tidak dicek** pemilik namanya.
- **API:**
  - `GET /api/names` menunjukkan pemilik setiap nama, atau satu nama;
  - `POST /api/names/add` dan `/api/names/remove`;
  - keadaan draft di Studio membawa pemilik namanya.
- **Studio:**
  - di bawah judul draft tertulis siapa yang boleh membekukannya, atau bahwa
    nama itu belum dimiliki;
  - formulir pembekuan menyebutnya lagi, dan penolakan tampil lengkap dengan
    jalan keluarnya;
  - formulir itu sekarang terbuka di atas ruang kerja, tidak lagi mendorong
    ruang kerja ke bawah.
- **Test:**
  - 5 test baru di `tests/owners/test_owners.py`, dengan kernel kosong
    tersendiri;
  - 1 test tampilan baru;
  - test yang dulu membekukan di bawah satu nama dengan nama orang yang
    berbeda-beda sekarang memakai satu pemilik per nama: `dev` untuk
    `@demo`, `probe` untuk `@probe`;
  - 335 test Python dan 42 test tampilan lulus.
- **Dicek di Chrome** (server pemeriksaan port 8207, kernel sementara
  `uniti_appcheck`):
  - draft `@demo/notes` menyebut "only an owner of @demo freezes under it:
    dev";
  - membekukan sebagai `sari` ditolak dengan nama pemiliknya dan tiga jalan
    keluar;
  - membekukan sebagai `dev` berhasil menjadi v1;
  - draft `@budi/notes` menyebut bahwa nama itu belum dimiliki.

  Server sudah dimatikan.
