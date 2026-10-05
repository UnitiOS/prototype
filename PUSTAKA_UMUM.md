# Rancangan pustaka umum `@uniti/*` — versi pertama

> **Status: disetujui dan dibangun, 6 Oktober 2026** (hasil di §9).
> Langkah 1 dari urutan sesudah keputusan di `DESIGN_NOTES.md` §15. Dokumen
> kerja: setelah dibangun, ringkasannya pindah ke `REFACTOR_P2.md` dan
> `DESIGN_NOTES.md`, lalu dokumen ini dihapus.

## 1. Yang harus diperbaiki, dan tidak lebih

Uji lingkungan kosong memperlihatkan dua lubang yang seharusnya diisi
pustaka umum:

1. **Tidak ada pihak bersama.** Modul jaminan membuat "pelanggan" sendiri,
   jadi Budi di modul sewa dan Budi di modul jaminan adalah dua hal yang tidak
   saling kenal.
2. **Tidak ada bentuk transaksi.** Sewa dicatat per baris alat, tanpa satu
   catatan "Citra menyewa tiga alat pada 8 Oktober". Akibatnya jaminan tidak
   punya tempat untuk menempel.

Pustaka umum versi pertama hanya mengisi dua lubang itu, ditambah satu hal
yang hampir setiap modul butuhkan: **barang**. Yang lain menunggu sampai ada
modul yang benar-benar membutuhkannya (aturan pertumbuhan §4.4).

## 2. Isinya: tiga modul kecil

Tiga modul terpisah, bukan satu. Alasannya sama dengan ERP: tiap modul bisa
naik versi atau diganti sendiri-sendiri. Semua nama dalam bahasa Inggris
mengikuti standar pencatatan, dengan label bahasa Indonesia di sampingnya.

### `@uniti/party` — pihak

| kelas | isi | peran core |
|---|---|---|
| `Party` (Pihak) | `party_name` (nama; pengenalnya), `party_kind` (orang atau organisasi; boleh kosong) | Thing |

- Satu orang atau satu organisasi **satu kali**, dipakai semua modul.
- **Tidak ada kelas Pelanggan atau Pemasok.** Pelanggan bukan jenis pihak,
  melainkan kedudukan seseorang di sebuah transaksi. Budi bisa menyewa hari
  ini dan menjual tenda bekasnya ke kita bulan depan, dan ia tetap satu Budi.
  ERP sampai di kesimpulan yang sama (satu "Partner" di Odoo).
- Kontak, alamat, dan NPWP tidak dimasukkan. Itu urusan modul CRM atau pajak,
  yang menunjuk ke `Party`.

### `@uniti/item` — barang

| kelas | isi | peran core |
|---|---|---|
| `Item` (Barang) | `item_name` (nama; pengenalnya) | Resource |

- Satu barang satu kali: tenda yang disewakan, dibeli, dan dijual adalah
  `Item` yang sama.
- Hal khusus satu fungsi bisnis tidak ditaruh di sini. Contohnya tarif sewa
  per hari: itu catatan milik modul sewa sendiri, misalnya "Tarif sewa" yang
  menunjuk ke `Item`.
- **Satuan belum menjadi kelas.** Satuan tetap ditulis di setiap angka seperti
  sekarang. Kelas satuan baru berguna kalau konversi satuan dibangun, dan itu
  ada di daftar compiler yang tumbuh sesuai kebutuhan.

### `@uniti/transaction` — bentuk transaksi

Dua **peran**, bukan kelas yang diisi data. Setiap modul membuat kelas
transaksinya sendiri (Penyewaan, Pembelian, Penerimaan jaminan) lalu mengisi
peran ini. Dengan begitu kepemilikannya tetap jelas.

| peran | yang wajib disebut kelas pengisinya | turunan dari |
|---|---|---|
| `Transaction` (Transaksi) | `counterparty`: pihak lawan transaksi, sebuah `Party` | core `Event`, jadi juga wajib punya tanggal |
| `TransactionLine` (Baris transaksi) | `part_of`: transaksi yang memuat baris ini | — |

Yang didapat dari peran ini:
- Agent dan orang yang mencari di koleksi bersama menemukan semua jenis
  transaksi lewat satu kata, misalnya "semua transaksi dengan Budi".
- Modul lain bisa **menunjuk ke sebuah transaksi**. Penerimaan jaminan
  menunjuk ke penyewaan yang dijaminnya.
- Standar pencatatan bisa memeriksa bahwa setiap baris menunjuk ke
  transaksinya.

Baris yang memindahkan barang, seperti baris sewa, juga mengisi peran core
`Flow` (berapa banyak, barang apa), seperti sekarang.

## 3. Contoh: Kemah Ceria di atas pustaka ini

Gambaran, bukan bagian pustaka. Ini yang akan dibangun "komunitas" di babak 1
uji ulang.

```
@uniti/party       Party ── Budi, Citra, Dewi, Andi
@uniti/item        Item  ── Tenda 4 orang, Kompor, ...

modul sewa         Rental (Transaction)       → counterparty: Party, tanggal
                   RentalLine (TransactionLine + Flow)
                                              → part_of: Rental, Item, jumlah
                   ReturnLine ...             → part_of: Rental, Item, jumlah
                   EquipmentStock (hitungan per Item)

modul jaminan      DepositReceipt (Transaction) → counterparty: Party,
                                                  secures: Rental, jumlah uang
                   DepositRefund (Transaction)  → ...
                   DepositBalance (hitungan per Party)
```

Budi tercatat satu kali. Jaminan Citra menunjuk ke penyewaannya, bukan ke
salah satu dari tiga barisnya.

## 4. Yang sengaja tidak dimasukkan

| tidak dimasukkan | kenapa |
|---|---|
| Uang sebagai modul | Untuk satu mata uang cukup aturan: satuan setiap jumlah uang adalah kode ISO 4217 (`IDR`). Itu bisa ditambahkan ke standar pencatatan. Modul uang baru diperlukan untuk banyak mata uang dan kurs |
| Kelas satuan | lihat `@uniti/item` |
| Kalender, alamat, kontak | belum ada modul yang membutuhkannya |
| Pelanggan dan pemasok sebagai kelas | lihat `@uniti/party` |
| Status transaksi (draft, lunas, batal) | setiap fungsi bisnis punya daur hidupnya sendiri; belum ada pola bersama yang terbukti |

## 5. Aturan pemakaian

1. **Modul menunjuk ke `Party` dan `Item`, tidak menurunkannya.** Kalau
   setiap modul membuat "Barang Sewa" turunan `Item` dan "Barang Jual"
   turunan `Item`, satu tenda terpecah menjadi dua jenis, persis masalah yang
   mau diperbaiki. Ini sejalan dengan keputusan tanpa perluasan.
2. **Cari dulu, jangan buat ulang.** Panduan agent (langkah 4) mengajarkan:
   pihak dan barang selalu dari pustaka umum.
3. **Pustaka umum dimiliki penjaga inti.** Hanya mereka yang membekukan versi
   di bawah `@uniti` (aturan kepemilikan nama, langkah 3).

## 6. Batas yang perlu diketahui sekarang

Compiler belum bisa **mengelompokkan lewat satu lompatan**. Contohnya
"jumlah alat yang sedang disewa Budi": baris sewa → penyewaannya → Budi. Hal
ini sudah ada di daftar irisan 5 ("kunci lewat satu lompatan rujukan").

- Yang tetap bisa dihitung: stok per barang (dari baris), saldo jaminan per
  pihak (jaminan menunjuk langsung ke pihak), dan semua angka di uji Kemah
  Ceria.
- Yang belum bisa: total baris per pihak lawan transaksi.
- **Akibat kecil kedua:** baris yang mengisi `Flow` wajib punya tanggal
  sendiri, karena compiler belum bisa mengambil tanggal dari transaksinya.
  Untuk sementara baris menyalin tanggal transaksinya.

Begitu pola transaksi dengan baris dipakai, kebutuhan "satu lompatan" akan
cepat terasa. Itu kandidat kuat sesudah pustaka ini.

## 7. Cara membangunnya

- Lewat langkah-langkah Studio yang sama dengan yang dipakai semua orang,
  tanpa menulis YAML dan tanpa model. Ditandai sebagai pekerjaan orang
  (penjaga inti), yang saya jalankan atas nama pemilik. Pembekuannya dengan
  persetujuan pemilik.
- Disimpan di `packages/@uniti/` di samping core.
- Diuji dengan test:
  - ketiga modul lolos standar dan pembekuan;
  - katalog menemukan `Party`, `Item`, `Transaction` dan `TransactionLine`;
  - satu modul contoh kecil yang memakai ketiganya bisa dibekukan, dan
    angkanya benar.

## 8. Yang perlu diputuskan pemilik

1. Tiga modul (`party`, `item`, `transaction`) dengan isi di atas, atau ada
   yang ditambah atau dikurangi?
2. Pelanggan dan pemasok bukan kelas, melainkan kedudukan di transaksi?
3. Modul **dilarang** menurunkan `Party` dan `Item`, ditegakkan oleh
   pembekuan, atau cukup diajarkan lewat panduan?
4. Uang dan satuan cukup sebagai aturan dulu, bukan modul?
5. "Kunci lewat satu lompatan" di compiler dikerjakan sesudah pustaka ini,
   sebelum uji ulang, atau nanti?

## 9. Hasil (6 Oktober 2026)

Pemilik menyetujui kelima keputusan di §8 sesuai saran. Semuanya dibangun
pada hari yang sama, tanpa panggilan model.

- **Tiga modul dibekukan** di `packages/@uniti/` sebagai v1 dan didaftarkan
  ke log pengembangan:
  - `party`: `Party` dengan nama dan jenis (orang/organisasi);
  - `item`: `Item` dengan nama;
  - `transaction`: peran `Transaction` dan `TransactionLine`.
- **Cara membangunnya.** `party` dan `item` dibangun lewat langkah Studio
  sebagai orang. `transaction` ditulis tangan seperti core, karena Studio
  tidak punya langkah untuk membuat peran, lalu dibekukan lewat gerbang yang
  sama, lengkap dengan transkripnya.
- **Nama pengikat.** `counterparty` dan `part_of` menjadi
  `transaction_counterparty` dan `line_transaction`, mengikuti standar nama
  slot.
- **Larangan menurunkan kelas milik modul lain** (`kind_of_foreign_class`)
  ditegakkan di pembekuan dan langsung di langkah Studio. Panduan agent ikut
  mengajarkannya lewat langkah "pakai ulang" di prosedur standar.
- **Satu lompatan di compiler.** Kunci pengelompokan boleh ditulis
  `slot.slot`, misalnya baris sewa dikelompokkan per pelanggan dari
  penyewaannya. Lompatan dibaca dengan aturan dua jam yang sama. Lompatan ini
  diikuti oleh:
  - asal-usul sel;
  - katalog dan laporan peran;
  - peta "cara angka dihitung" di Studio, termasuk saat mengikuti contoh.

  Dua lompatan ditolak sebagai "belum bisa". Lompatan lewat slot yang tidak
  menunjuk ke catatan ditolak (`not_a_reference`).
- **Panduan agent:** 19.990 karakter, di bawah batas 20.000.
- **Test:** 8 test baru di `tests/modules/test_library.py`. Isinya modul
  contoh penyewaan + jaminan di atas pustaka: Budi tercatat satu kali,
  jaminan menunjuk ke penyewaan, angka per pelanggan lewat lompatan di contoh,
  di tabel, dan di asal-usul sel. Ada juga 1 test tampilan baru. Total 321
  test Python dan 38 test tampilan lulus.
- **Dicek di Chrome.** Server pemeriksaan di port 8205 dipakai atas toko
  sementara `build/libcheck`. Baris "Customer out, budi" menunjukkan dua baris
  sewa lewat `r1`, totalnya 3 dan tercentang, dengan kalimat penjelasan yang
  menyebut lompatannya. Server sudah dimatikan.
