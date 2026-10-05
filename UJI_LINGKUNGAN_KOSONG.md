# Uji dari lingkungan kosong: apakah sistem modular ini bekerja

> **Dokumen kerja sementara**, seperti `COMPOSITION_EXPERIMENT.md`. Hidup
> selama uji ini, lalu hasilnya dipindahkan ke `REFACTOR_P2.md` dan dokumen ini
> dihapus. Ditulis 4 Oktober 2026, sesudah temuan sesi tahap 4 diperbaiki.

## 1. Pertanyaannya

Semua uji agent sejauh ini mendapat bantuan yang tidak terlihat: catatan stok
sudah tersedia dari modul contoh (@demo), jadi agent hanya menulis
hitungannya. Uji ini mencabut bantuan itu. Ada lima pertanyaan:

1. Bisakah agent membangun dari kosong: menentukan apa yang dicatat, mengisi
   peran dasar dari inti, lalu menulis contoh dan rumusnya?
2. Bisakah orang awam memakai hasilnya, yaitu mengisi transaksi lewat
   formulir dan membaca angka yang benar?
3. Apakah modul dipakai ulang? Aplikasi kedua harus memakai catatan dari
   langkah pertama, bukan membuat ulang.
4. Bisakah modul direvisi ke versi 2 sementara datanya sudah berjalan, tanpa
   kehilangan catatan lama?
5. Bisakah modul pencatatan diganti dengan buatan orang lain, sementara
   contoh usaha tetap menjadi penjaga angkanya?

## 2. Lingkungan

- **Database baru** (`uniti_blank`, dengan `uniti_blank_ops` untuk tabel
  hasil hitungan). Isinya hanya skema dan inti (`@uniti/core` v1 dan v2).
  Database pengembangan tidak tersentuh.
- **Tempat modul baru** di `build/blank/packages`. Isinya kosong; inti dibaca
  dari `packages`.
- **Server uji** di port 8204, dengan pengaturan agent tersendiri
  (`build/blank/agent.yaml`, lewat `UNITI_AGENT_CONFIG`).
  `config/agent.yaml` tidak diubah.
- **Model**: Gemini 3.8 Flash untuk agent dan akuntan, sama seperti tahap 4.

## 3. Peran

- **Claude** berperan sebagai pemilik usaha. Ia menulis dalam bahasa
  Indonesia sehari-hari, tidak tahu istilah teknis, dan menjawab pertanyaan
  agent sesuai cerita di bagian 4. Ia tidak pernah menyebut nama kelas,
  kolom, atau modul, dan tidak membetulkan pekerjaan agent dengan tangan.
- **Agent** membangun lewat Studio, mengikuti urutannya: rencana, contoh,
  rumus, lalu siap dibekukan.
- **Persetujuan dan pembekuan** dilakukan Claude sebagai pemilik, lewat
  tombol di Studio.
- **Kebenaran tersembunyi** (bagian 5) ditulis sebelum uji dan tidak pernah
  terlihat oleh agent. Agent tidak bisa membaca berkas; alatnya hanya
  Studio.

## 4. Skenario usaha

**Kemah Ceria** (fiktif) adalah usaha kecil penyewaan alat kemah, dikelola
pemiliknya, Sari. Selama ini semuanya dicatat di buku tulis.

Alat yang dimiliki:

| Alat | Dibeli 5 Okt | Tambahan |
|---|---|---|
| Tenda 4 orang | 6 | |
| Tenda 2 orang | 4 | |
| Kompor portabel | 5 | +2 pada 10 Okt |
| Sleeping bag | 10 | |
| Matras | 10 | |

Cara kerjanya:
- Pelanggan menyewa beberapa alat sekaligus, lalu mengembalikannya beberapa
  hari kemudian.
- Saat menyewa, pelanggan menitipkan uang jaminan. Uang itu dikembalikan
  saat alat kembali.
- Alat yang kembali rusak tidak bisa disewakan sampai diperbaiki. Alat yang
  hilang tidak lagi menjadi milik toko.

Jawaban Sari kalau agent bertanya:
- Jumlah alat dihitung per buah.
- Uang dalam rupiah.
- Tanggal yang penting adalah hari alat keluar dan hari alat kembali.
- Satu penyewaan bisa berisi beberapa jenis alat.

Transaksi minggu pertama (diisi di langkah 2):

| Tanggal | Kejadian |
|---|---|
| 5 Okt | Pembelian alat (tabel di atas) |
| 6 Okt | Andi menyewa Tenda 4 orang ×2 dan Kompor ×1; jaminan Rp300.000 |
| 7 Okt | Budi menyewa Tenda 2 orang ×1, Sleeping bag ×2, Matras ×2; jaminan Rp150.000 |
| 8 Okt | Andi mengembalikan semua alatnya; jaminan Rp300.000 dikembalikan |
| 8 Okt | Citra menyewa Tenda 4 orang ×3, Kompor ×2, Sleeping bag ×6; jaminan Rp500.000 |
| 9 Okt | Andi menyewa Tenda 2 orang ×2 dan Matras ×4; jaminan Rp200.000 |
| 10 Okt | Beli Kompor ×2 lagi |
| 10 Okt | Budi mengembalikan semua alatnya; jaminan Rp150.000 dikembalikan |
| 11 Okt | Andi mengembalikan semua alat sewaan 9 Okt; jaminan Rp200.000 dikembalikan |
| 11 Okt | Dewi menyewa Tenda 4 orang ×1, Kompor ×1, Sleeping bag ×2; jaminan Rp150.000 |

Kejadian sesudahnya (langkah 4):
- 11 Okt: satu matras dari pengembalian Andi ternyata rusak. Sari lupa
  mencatatnya.
- 13 Okt: Citra mengembalikan Tenda 4 orang ×3, Kompor ×2 dan Sleeping
  bag ×5. Satu sleeping bag hilang. Jaminan Rp500.000 dikembalikan; sleeping
  bag yang hilang dibayar terpisah dan tidak dicatat di sini.

## 5. Langkah, permintaan pemilik, dan kebenarannya

### Langkah 1: aplikasi pertama dibangun dari kosong (Chrome)

Permintaan Sari: *"Saya mau tahu berapa alat yang ada di gudang dan berapa
yang sedang disewa, per jenis alat."*

Yang diamati:
- apa yang dibuat agent: satu modul berisi catatan sekaligus hitungan, atau
  catatan dan hitungan dipisah;
- peran inti yang diisi (barang yang dihitung, kejadian, pergerakan);
- satuan dan arti tanggal;
- apakah contoh-contohnya menangkap kesalahan yang penting: arah keluar dan
  masuk, dan alat yang sudah kembali;
- apakah ketiga persetujuan ditanyakan dengan benar: rencana, contoh, dan
  pembekuan.

Selesai bila modulnya dibekukan sebagai v1.

### Langkah 2: transaksi diisi lewat formulir (Chrome, tanpa model)

Semua transaksi minggu pertama diisi di area Aplikasi, satu per satu, lewat
formulir yang dibuat sistem. Yang diamati: apakah formulirnya bisa dipahami
orang awam, dan apakah angkanya cocok dengan kebenaran.

Kebenaran per 12 Oktober:

| Alat | Milik toko | Sedang disewa | Di gudang |
|---|---|---|---|
| Tenda 4 orang | 6 | 4 | 2 |
| Tenda 2 orang | 4 | 0 | 4 |
| Kompor portabel | 7 | 3 | 4 |
| Sleeping bag | 10 | 8 | 2 |
| Matras | 10 | 0 | 10 |

**Titik periksa pemilik.** Kalau langkah 1 atau 2 gagal, langkah berikutnya
tidak berarti. Hasilnya dilaporkan dulu sebelum lanjut.

### Langkah 3: aplikasi kedua memakai ulang (Chrome)

Permintaan Sari, di modul baru: *"Saya juga mau tahu uang jaminan pelanggan
yang masih saya pegang, per pelanggan."*

Yang diamati:
- apakah agent menemukan modul langkah 1 di katalog dan memakainya, bukan
  mendeklarasikan penyewaan lagi;
- bila jaminan belum tercatat di modul langkah 1, jalan mana yang dipilih:
  merevisi modul itu, atau menambah catatan jaminan yang merujuk ke
  penyewaan; dan apakah ia menanyakannya ke Sari.

Kebenaran per 12 Oktober: Andi 0, Budi 0, Citra Rp500.000, Dewi Rp150.000.
Totalnya Rp650.000.

### Langkah 4: revisi ke versi 2 dengan data berjalan (Chrome atau API)

Permintaan Sari, di modul langkah 1: *"Sekarang ada alat yang rusak dan
hilang. Yang rusak jangan dihitung siap disewa, yang hilang sudah bukan
milik saya."*

Kejadian langkah 4 diisi lewat formulir sesudah versi 2 dibekukan.
Kebenaran per 13 Oktober:

| Alat | Milik toko | Sedang disewa | Di gudang | Rusak | Siap disewa |
|---|---|---|---|---|---|
| Tenda 4 orang | 6 | 1 | 5 | 0 | 5 |
| Tenda 2 orang | 4 | 0 | 4 | 0 | 4 |
| Kompor portabel | 7 | 1 | 6 | 0 | 6 |
| Sleeping bag | 9 | 2 | 7 | 0 | 7 |
| Matras | 10 | 0 | 10 | 1 | 9 |

Selain itu: catatan minggu pertama tetap terhitung tanpa diisi ulang, dan
contoh versi 1 tetap lulus. Jaminan per 13 Oktober: Citra 0 dan Dewi
Rp150.000.

### Langkah 5: modul pencatatan diganti (API, lalu tampilan dicek di Chrome)

Cerita: Sari mulai memakai aplikasi kasir "SewaPro" (fiktif), yang membawa
modul pencatatan sewanya sendiri. Modul itu dibuat Claude dengan tangan di
Studio sebagai penulis lain, dengan nama kelas dan kolom berbeda, dan mengisi
peran inti yang sama. Agent tidak ikut membuatnya.

Permintaan Sari: *"Mulai besok penyewaan dicatat lewat SewaPro. Tolong
hitungan alat saya ikut membacanya."*

Yang diamati:
- agent menyambungkan ulang rumusnya ke catatan SewaPro;
- contoh usaha yang sama tetap lulus;
- apakah agent bertanya, dan apakah ia jujur, soal catatan buku yang lama.
  Catatan lama tetap ada di log tetapi tidak lagi dibaca. Tidak ada angka
  "benar" yang ditetapkan untuk ini; yang diuji adalah apakah sistem
  menunjukkannya, bukan menyembunyikannya.

## 6. Batas waktu dan biaya

Batasnya dinaikkan dari tahap 4, karena membangun dari kosong lebih berat.
Kenaikan ini hanya berlaku di server uji.

- **Per permintaan**: 40 panggilan model, 1 juta token, $0,40. Sebelumnya 25
  panggilan, 600 ribu token, $0,20.
- **Per panggilan model**: 90 detik. Sebelumnya 60 detik.
- **Per langkah**:
  - langkah 1: paling banyak 12 permintaan, $2,50;
  - langkah 2: tanpa model, $0;
  - langkah 3: 8 permintaan, $1,50;
  - langkah 4: 6 permintaan, $1,00;
  - langkah 5: 8 permintaan, $1,50.
- **Total**: paling banyak $7. Perkiraan wajarnya $3–4.
- **Waktu**: sekitar 4–6 jam kerja, dibagi 2–3 sesi, dengan titik periksa
  sesudah langkah 2. Server uji menyala paling lama 2 jam sekali jalan. Bila
  berhenti, pemilik diberi tahu dan server tidak dinyalakan ulang diam-diam.

Aturan berhenti:
- Satu langkah melewati batasnya: berhenti dan lapor.
- Layanan model gagal tiga kali berturut-turut: berhenti dan lapor.
- Agent melanggar urutan atau persetujuan: dicatat sebagai temuan dan uji
  berlanjut, karena sistem harus menolaknya.

## 7. Yang diukur di setiap langkah

- angka benar atau tidak, dibanding kebenaran;
- persetujuan yang diminta dengan benar, dan langkah yang ditolak sistem;
- yang dibuat ganda, bukan dipakai ulang;
- mutu graph: peran terisi, satuan, keterangan, label berbahasa Indonesia;
- apakah peta, panel, dan formulir bisa dipahami orang awam;
- biaya, jumlah panggilan, dan waktu.

## 8. Hasil

**Persiapan (4 Oktober 2026, tanpa model).** Database `uniti_blank` dan
`uniti_blank_ops` dibuat, skema dipasang, inti v1 dan v2 didaftarkan (log
berisi 2 catatan). Tempat modul `build/blank/packages` kosong. Server uji
menyala di port 8204 dengan batas baru; katalog dan Studio di Chrome hanya
menunjukkan inti.

**Langkah 1.**
- Temuan kecil (tanpa model): kolom nama modul di "Build with the agent"
  sudah berisi "@", sehingga nama yang diketik menjadi "@@...". Server
  menjawab dengan galat 500, bukan penolakan yang jelas.
- Permintaan 1 ($0,019, 3 panggilan, 32 detik): agent membaca katalog (hanya
  inti), tidak membangun apa pun, lalu bertanya: catat pembelian, keluar dan
  kembali sewa (gudang dan sewa terhitung), atau hanya sewa dan kembali.
  Sari memilih yang pertama.
- Permintaan 2 ($0,029, 3 panggilan): rencana, tanpa membangun. Yang
  dicatat: jenis alat, pengadaan, pengeluaran sewa, pengembalian (jenis,
  tanggal, jumlah). Angka: sedang disewa dan stok gudang per jenis alat, per
  tanggal. Bahasa orang biasa, tanpa nama teknis. Pelanggan dan "satu sewa
  berisi beberapa alat" tidak ikut dicatat. Disetujui.
- Permintaan 3 ($0,192, 18 panggilan, 4 menit): satu modul berisi catatan
  dan hitungan. Alat Kemah mengisi peran barang (Resource). Pengadaan,
  Pengeluaran Sewa dan Pengembalian mengisi peran kejadian (Event) dengan
  tanggal kejadiannya, tetapi **tidak** mengisi peran pergerakan (Flow):
  jumlah dan alat tidak diikat ke `amount` dan `affects`. Satuan "unit",
  label Indonesia di semua tabel dan kolom. Satu contoh lewat akuntan (4
  jenis alat, beli, dua kali sewa, satu kali kembali); angkanya dihitung
  ulang dan benar. Contoh hanya memeriksa satu tanggal, jadi pembacaan
  sebelum alat kembali tidak diuji. Disetujui.
- Catatan tampilan: bahasa halaman tetap "English" sampai dipilih sendiri;
  nama contoh tampil "Rental cycle" dengan label Indonesianya dalam kurung;
  kode baris (`eq_stove`) tampil di daftar angka contoh; setelah contoh
  disetujui tidak ada tombol "lanjut", orangnya harus mengetik.
- Permintaan 4 ($0,033, 4 panggilan): rumus sekaligus. Total pengadaan,
  disewa dan dikembalikan dijumlah per alat; sedang disewa = disewa −
  dikembalikan; stok gudang = pengadaan − sedang disewa. Contoh lulus,
  siap dibekukan.
- Langkah 1 sampai siap dibekukan: 4 permintaan, 28 panggilan, $0,27,
  sekitar 12 menit. Dibekukan sebagai v1 oleh "sari" atas persetujuan
  pemilik.

**Langkah 2.**
- Alat pertama dan pembelian pertama diisi lewat formulir di Chrome. Sisa 29
  transaksi dikirim ke alamat yang sama dengan isian yang sama (bentuk
  formulirnya identik per tabel). Total 31 transaksi, tanpa model.
- Angka per 12 Oktober **cocok semua** dengan kebenaran (milik toko, sedang
  disewa, di gudang untuk kelima alat). Diperiksa juga 7 dan 9 Oktober:
  angka per tanggal benar, termasuk alat yang belum dan sudah kembali.
  Asal-usul angka bisa diklik: "sedang disewa" Tenda 4 orang menunjukkan
  tiga catatan sewa yang dijumlah.
- Formulir **belum bisa dipakai orang awam**:
  - semuanya berbahasa Inggris dan memakai nama teknis (`equipment_name`,
    `acquisition_quantity`, `p_acquisition`, "State a Equipment"), padahal
    label Indonesianya ada di modul;
  - orangnya harus mengarang alamat ("URI", `prefix:name`) untuk tiap
    catatan;
  - tanggal diisi dua kali ("Valid from" dan tanggal kejadiannya), dan
    "Valid from" mengikuti jam halaman, bukan tanggal kejadian;
  - tanggal kejadian dan jumlah berupa kotak teks biasa, tanpa pemilih
    tanggal atau angka;
  - sesudah disimpan, tabel di bawahnya tidak diperbarui, dan pada jam
    halaman sekarang catatan bertanggal depan tidak terlihat sama sekali;
  - tabel hitungan menawarkan "State a EquipmentStock", padahal tabel itu
    dihitung, bukan diisi;
  - baris tabel hitungan menampilkan alamat (`alat:kompor`), bukan nama
    alat, dan kolom stok gudang tersembunyi di geseran ke kanan.
- Pilihan alat di formulir sewa berupa daftar nama alat yang sudah dicatat,
  dan ini sudah baik.
- Titik periksa: pemilik meminta kelemahan formulir dan tampilan dicatat
  untuk dikerjakan lain waktu, dan uji dilanjutkan.

**Langkah 3** (modul baru `@kemahceria/jaminan`).
- Permintaan 1 ($0,036, 5 panggilan): agent mencari di katalog ("kemahceria",
  "customer", "party") dan membaca modul langkah 1. Dari pikirannya: ia
  melihat modul itu tidak mencatat pelanggan maupun uang. Lalu ia bertanya
  soal mata uang dan potongan jaminan. Sari: rupiah, dicatat saat diterima
  dan dikembalikan, tanpa potongan.
- Permintaan 2 ($0,009, 1 panggilan): rencana modul **berdiri sendiri**:
  Pelanggan, Penerimaan Jaminan, Pengembalian Jaminan, dan saldo per
  pelanggan per tanggal. Tidak ada yang dipakai ulang dari langkah 1, tetapi
  tidak ada yang dibuat ganda juga (penyewaan tidak dideklarasikan ulang).
  Agent tidak bertanya apakah jaminan perlu dikaitkan ke penyewaannya. Ia
  juga tidak menawarkan revisi modul langkah 1. Disetujui.
- Permintaan 3 ($0,121, 11 panggilan): Pelanggan hanya mengisi peran
  "sesuatu" (Thing), bukan peran pihak, karena inti belum punya peran pihak.
  Penerimaan dan pengembalian mengisi peran kejadian, tanpa peran
  pergerakan. Uang memakai satuan IDR dan desimal. Satu contoh lewat
  akuntan (Budi dan Siti); angkanya benar, tetapi memuat pengembalian
  sebagian, padahal Sari bilang tidak ada potongan. Disetujui.
- Permintaan 4 ($0,029, 5 panggilan): rumus terima dan kembali dijumlah per
  pelanggan, saldo = terima − kembali. Contoh lulus, siap dibekukan.
- Langkah 3 sampai siap dibekukan: 4 permintaan, 22 panggilan, $0,20.
  Dibekukan sebagai v1 atas persetujuan pemilik.
- Data: pelanggan Andi lewat formulir di Chrome, sisanya (3 pelanggan, 5
  jaminan diterima, 3 dikembalikan) lewat alamat formulir yang sama. Saldo
  per 12 Oktober **cocok**: Andi 0, Budi 0, Citra Rp500.000, Dewi
  Rp150.000, total Rp650.000. Tampil sama di Chrome.
- Karena terpisah, setiap penyewaan diisi di dua tempat oleh orangnya (alat
  di modul sewa, jaminan di modul jaminan), tanpa yang menyambungkan
  keduanya: nama penyewa tidak ada di catatan sewa, dan jaminan tidak bisa
  ditelusuri ke penyewaannya.

**Analisa: kenapa modul jaminan terputus** (diminta pemilik sebelum langkah
4, tanpa model; dari catatan panggilan, panduan agent, dan kode Studio).

Mekanisme yang sudah ada:
- satu modul bisa memakai modul lain yang sudah dibekukan dan merujuk ke
  tabelnya (seperti `@demo/stock` memakai catalog dan inventory);
- rumus bisa menjumlah tabel modul lain, atau semua tabel yang mengisi satu
  peran;
- modul bisa direvisi ke versi baru, tetapi hanya dari sesi modul itu.

Penyebab, berlapis:
1. **Rancangan langkah 1 (agent).** Sari sudah bilang di kalimat pertama
   bahwa pelanggan menyewa beberapa alat sekaligus. Agent mencatat hanya
   baris per alat (alat, tanggal, jumlah) karena cuma itu yang dibutuhkan
   angka yang diminta. Tidak ada "penyewaan" sebagai satu kejadian (siapa,
   kapan, alat apa saja), dan tidak ada pelanggan. Panduan mengarahkan
   rencana ke "angka apa yang keluar", tidak ke "kejadian usaha apa yang
   terjadi dan siapa yang terlibat". Jadi modul dibangun pas untuk satu
   pertanyaan, dan pertanyaan berikutnya tidak punya pijakan.
2. **Batas sesi (rancangan sistem).** Agent hanya boleh membangun di modul
   yang dibuka; modul lain hanya dibaca ("not changed from here"). Nama
   modul dipilih orangnya **sebelum** agent tahu kebutuhannya: kolom nama
   wajib diisi di Studio. Di uji ini nama baru itu dipilih oleh skenario
   (langkah 3 ditulis "di modul baru"), jadi jalan "revisi modul sewa"
   memang tertutup sejak awal. Ini kesalahan rancangan uji juga.
3. **Tidak ada jalan yang bersih untuk menyambung, bahkan kalau agent mau.**
   Merujuk ke catatan sewa dari modul jaminan bisa, tetapi catatan sewa per
   baris alat: jaminan Citra harus menunjuk salah satu dari tiga baris.
   Menambah kolom pelanggan ke tabel sewa dari modul lain tidak bisa (tabel
   hanya diubah pemiliknya, dan ini disengaja).
4. **Agent tidak jujur soal sambungan itu (agent).** Di pikirannya ia
   menulis pertanyaan "apakah jaminan terkait penyewaan tertentu?" lalu
   menjawabnya sendiri: "sepertinya tidak". Ia tidak menanyakannya ke Sari
   dan tidak menyebutnya di bagian "yang belum bisa" di rencananya. Padahal
   panduan meminta bertanya "apakah kejadian yang sama juga dicatat di tempat
   lain".
5. **Inti belum punya kosakata bersama untuk pihak dan transaksi.** Peran
   yang ada hanya barang, kejadian, dan pergerakan. "Pelanggan" atau "satu
   transaksi dengan beberapa baris" tidak punya peran, jadi modul lain tidak
   bisa menemukannya lewat peran. Agent juga melewatkan peran pergerakan di
   kedua modul, padahal standar meminta peran diisi.

Kesimpulan: bukan satu sebab. Mekanisme dasarnya ada (memakai dan merujuk
modul lain, revisi). Kesalahan agent ada di langkah 1 (memodelkan untuk
angka, bukan untuk kejadian usaha) dan di langkah 3 (tidak bertanya, tidak
menyebutnya). Celah rancangan sistem ada di pilihan "modul mana" yang
diambil orang sebelum agent menilai, dan di sesi yang tidak bisa mengusulkan
perubahan ke modul lain.

### Keputusan pemilik sesudah analisa (6 Oktober 2026)

Pemilik tidak melanjutkan ke langkah 4. Ia meminta evaluasi yang lebih luas:
untuk apa modul dipakai, siapa penggunanya, dan bagaimana aplikasi dibentuk
dalam praktik, dengan ERP sebagai bahan pembanding. Hasilnya diputuskan dan
dicatat di `DESIGN_NOTES.md` §15:

- **Empat jenis, dipisahkan:** core, pustaka umum (pihak, barang dan satuan,
  uang, dokumen nota dengan baris), modul komunitas (termasuk modul
  penghubung), dan aplikasi (pribadi, milik satu usaha).
- **Peran pengguna dipisah:** penjaga inti, pembuat modul, penyusun aplikasi,
  pemilik proses, staf, pemeriksa. Agent membantu semuanya dan tidak memiliki
  apa pun.
- **Kepemilikan:** hanya pemilik sebuah nama yang membekukan versi di
  bawahnya. **Tidak ada perluasan** kelas milik modul lain; modul terhubung
  hanya dengan menunjuk.
- **Kernel per usaha**, bukan per aplikasi. Graph bersama tetap di toko berkas
  untuk sekarang; kernel Uniti sebagai catatan menyusul.

Akibatnya untuk uji ini: **uji berhenti sesudah langkah 3.** Langkah 1–3
mencampur tiga peran sekaligus — pemilik usaha menjadi pembuat modul dan
penyusun aplikasi di toko yang kosong, tanpa pustaka umum — jadi langkah 4
(revisi) dan 5 (penukaran) di atas susunan ini tidak akan mengukur hal yang
benar. Uji diulang setelah pustaka umum, aplikasi sebagai jenis tersendiri,
dan panduan agent per peran ada, dalam dua babak:

1. "Komunitas" membuat pustaka umum dan modul penyewaan serta jaminan yang
   umum.
2. Pemilik Kemah Ceria menyusun aplikasinya lewat agent dari koleksi itu, di
   kernel usahanya sendiri; lalu revisi dan penukaran modul seperti langkah 4
   dan 5 lama.

Biaya model yang terpakai sampai berhenti: **$0,47 dari batas $7**
(langkah 1 $0,27; langkah 3 $0,20; langkah 2 tanpa model). Lingkungan kosong
(`uniti_blank`, `build/blank/packages`) dibiarkan apa adanya sebagai bukti.
