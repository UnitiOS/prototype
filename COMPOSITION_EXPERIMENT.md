# Eksperimen komposisi — apakah peran bertahan di pemakaian nyata

> **Dokumen kerja sementara**, sama statusnya dengan `REFACTOR_P2.md`: hidup
> selama eksperimen ini, lalu dihapus. Kesimpulan dan hasilnya dipindahkan ke
> `REFACTOR_P2.md` irisan 2.8, yang merujuk ke sini.
>
> Ditulis 24 September 2026 dari satu percakapan analisis. **Dijalankan di sesi
> lain.** Sesi pelaksana membaca dokumen ini dari awal sampai akhir sebelum
> menyentuh apa pun, dan mengisi bagian **Hasil** di akhir. Kode tetap yang
> benar: kalau sesuatu di sini ternyata tidak cocok dengan kode, catat di
> Hasil, jangan diam-diam disesuaikan.

---

## 1. Pertanyaannya

Demo tepung membuktikan peran di skala terkecil: satu peran (`Flow`), dua modul
yang saling bisa ditukar (`@demo/inventory` dan `@rival/stock-moves`), dan
angka yang sama di kedua sisi (86 · 60 · 26). Pemilik proyek menangkap sesuatu
yang benar:

- Peran terlihat sederhana di depan, tetapi kemungkinannya meledak di belakang:
  satu hal bisa mengambil banyak peran, banyak modul bisa mengisi satu peran,
  dan ada arti yang tidak tertangkap bentuk.
- **Ini bukan masalah skala, tetapi masalah utama.** Di P1 masalah ini tidak
  muncul karena seluruh graph ditulis satu penulis secara eksplisit. Tanpa
  sambungan antar modul, tidak ada konflik. P1 tidak pernah menguji klaim
  modular, dan klaim modular itulah yang membedakan Uniti.
- Core tidak boleh membesar sampai menjadi bahasa pemrograman. Tujuan awal core
  dan modul adalah **standardisasi supaya tidak ada konflik antar modul atau
  versi.**

Kalau klaim modular tidak masuk akal di pemakaian nyata, sistemnya tidak akan
bekerja. Jadi ini dibuktikan **sebelum** irisan 3.2 dan 4.

## 2. Tujuan yang diuji

"Tidak ada konflik" tidak bisa dicapai standar apa pun. Konflik ada dua jenis:

| jenis | contoh | bisa dicegah mekanisme? |
|---|---|---|
| **struktur** | nama, versi, bentuk, pengikat | ya, tanpa core membesar |
| **arti** | tanda, satuan, waktu, pencatatan ganda, identitas | tidak seluruhnya; usaha ke sana berakhir sebagai *canonical data model* (ISO 15926) |

Maka target yang diuji adalah:

> **Tidak ada konflik yang diam.** Setiap ketidakcocokan antar modul jatuh ke
> salah satu dari empat jalur: ditolak saat seal, terlihat di laporan
> kecocokan, terdeteksi dari data di laporan kesehatan, atau diselesaikan
> dengan satu pernyataan penyelarasan yang eksplisit. Angka salah tanpa ada
> yang bersuara adalah satu-satunya hasil yang fatal.

### Batas core: uji masuk

Sesuatu boleh masuk core hanya kalau keempatnya "ya":

1. Ada eksekutor yang membacanya (`DESIGN_NOTES.md` §4.3).
2. Deklaratif: nilai dari himpunan tertutup, atau penunjuk ke satu slot. Tanpa
   kondisi, fungsi, atau perulangan.
3. Dibutuhkan minimal dua modul yang ditulis terpisah (§5, eksekutor dulu,
   peran diekstrak).
4. Tidak memilih pemenang di antara dua cara memodelkan yang sama-sama masuk
   akal (§4.4).

Anggaran keras: **core ≤ ±30 deklarasi.** Kebutuhan lain punya tempat yang
boleh tumbuh: eksekutor compiler (daftar tertutup), `@uniti/*`, modul
penyelarasan, dan deklarasi di aplikasi. Batas "standar lawan bahasa
pemrograman": **setiap aturan tetap bisa dianalisis tanpa dijalankan**, karena
hanya dengan itu laporan kecocokan tetap tepat.

## 3. Hipotesis: jenis ketidakcocokan terbatas

Kombinasi modul tak terbatas, tapi jenis ketidakcocokan antar modul terbatas
(riset integrasi database sudah mengklasifikasikannya puluhan tahun). Kalau
setiap jenis punya jalur jawaban, kerumitannya terikat. Tabel ini adalah
**prediksi**; eksperimen membuktikan atau membantah tiap barisnya.

| # | jenis | contoh ERP | prediksi hari ini | jalur jawaban yang diduga |
|---|---|---|---|---|
| T1 | nama | dua modul sama-sama punya `Product` | **diam** (lihat §4) | tolak, atau nama diberi awalan modul |
| T2 | versi | modul A di core v2, B di core v3 | ditolak | – |
| T3 | pengikat ganda | `qty_gross` dan `qty_net` sama-sama mengaku `amount` | ditolak | – |
| T4 | tanda / arah | qty positif + lokasi asal/tujuan (gaya Odoo) lawan qty bertanda (gaya ERPNext) | **diam** | deklarasi arah di core + penolakan compiler |
| T5 | satuan | sak 25 kg lawan kg | **diam** (`convert` ada, penolakan campuran belum) | deklarasi `unit` + compiler menolak campuran |
| T6 | keluasan | `over: Flow` ikut menjumlah arus uang | terlihat (`covers`) | persempit: `where is_a`, peran turunan, atau sebut kelas |
| T7 | pencatatan ganda | penerimaan dicatat di modul pembelian **dan** inventory | **diam** | aplikasi menyatakan sumber resmi + deteksi dari data |
| T8 | identitas | `Supplier` di satu modul = `Partner` di modul lain | tidak ada jalur | modul penyelarasan (dinyatakan orang, tidak disimpulkan; `DESIGN_NOTES.md` §10.6) |
| T9 | struktur | PO dengan header + banyak baris; modul lain datar; "hutang per supplier" lewat PO | kemungkinan tak terungkapkan (compiler belum punya jalur relasi/koleksi) | pertumbuhan compiler, bukan core |
| T10 | pergeseran arti antar versi | v2 mengubah qty dari bruto ke neto dengan `slot_uri` yang sama | **diam** | seal menuntut predikat baru bila arti berubah (sulit dideteksi) |

Prediksi yang paling penting untuk dipatahkan: **T7 dan T6.** Dugaan penulis
dokumen ini adalah aturan "jumlahkan semua `Flow`" terlalu kasar untuk ERP
nyata, sehingga manfaat menulis terhadap peran menyusut menjadi "berguna di
sambungan antar sedikit modul", bukan penjumlahan otomatis atas ekosistem.
Eksperimen harus menjawab ini dengan bukti.

## 4. Yang sudah dibuktikan sebelum eksperimen

**T1 di tingkat LinkML.** Dua modul yang sama-sama mendeklarasikan `Item`, dan
satu aplikasi yang mengimpor keduanya:

```
a.yaml:  Item {a_code, a_weight}     b.yaml:  Item {b_sku}
app.yaml imports [a, b]  ->  Item = {b_sku}, description "B's item"
```

Kelas milik A hilang tanpa suara. `seal.py:350` (`_one_version_per_module`)
hanya menolak **satu modul dalam dua versi**, dan komentarnya sendiri mengakui
LinkML "whichever merged last would win silently". Yang belum dibuktikan:
bahwa ini juga lolos lewat `seal()` Uniti. **Sengaja tidak diperbaiki sebelum
eksperimen**, karena penulis modul yang independen kemungkinan besar akan
menabraknya sendiri, dan itu bukti yang lebih kuat daripada jebakan yang
ditanam.

## 5. Kesiapan sistem

Eksperimen meniru pengguna sungguhan: **modul lewat langkah Studio dan seal,
data lewat pintu formulir yang dipakai layar, satu aksi demi satu aksi.**
Tidak ada YAML yang ditulis tangan, tidak ada `load_facts.py`, tidak ada tulis
langsung ke database.

### Jalur yang dilalui

| siapa | apa | pintu resmi | ada? |
|---|---|---|---|
| penulis modul | membuat draft | `POST /api/studio/step` `{name, step, args}`; `GET /api/studio/draft?name=` (lubang, pilihan, `steps`) | ✓ |
| penulis modul | membekukan | `python -m components.modules seal @scope/name --actor <who>` → `seal()` | ✓ hanya CLI |
| implementer | pin + aturan | Studio `pin`, `aggregate`, `parameter`, `expression` | ⚠ G1 |
| staf | melihat formulir | `GET /api/app/form?name=&version=&class=` | ✓ |
| staf | mengirim | `POST /api/app/state` `{name, version, class, subject, actor, values, valid_from?, note?}` | ✓ |
| staf | mengoreksi / menarik | – | ✗ G2 |
| pengamat | angka, sel, kesehatan, kecocokan | `/api/app/projection`, `/api/app/cell`, `/api/app/health`, `/api/app/fit`, `/api/app/check` | ✓ |

### Celah yang ditutup sebelum eksperimen (langkah 1)

Semuanya perbaikan pintu, bukan mekanisme baru. Masing-masing dengan test lebih
dulu, satu commit per celah, dan **dikonfirmasi ke pemilik proyek di langkah 0**
sebelum dikerjakan.

- **G1. `aggregate` di Studio lebih sempit dari compiler.** `draft.py:993`
  hanya menulis `over`, `sum`, `by`. Compiler sudah menerima
  `where: {slot: {is_a: Kelas}}` dan `convert` (`compile.py:381`, `:425`).
  Tanpa ini T5 dan T6 tidak bisa diungkapkan lewat gerbang. Perbaikan:
  `where` dan `convert` sebagai argumen opsional (`may`) langkah `aggregate`;
  compiler tetap satu-satunya hakim.
- **G2. Koreksi tidak bisa lewat formulir.** `submit()` menerima `revokes`
  (`generate.py:526`), `/api/app/state` tidak meneruskannya (`app.py:340`).
  Perbaikan: teruskan `revokes` (nama medan → id assertion yang ditarik).
- **G3. Pilihan formulir basi sampai compile ulang.** Medan rujukan membaca
  pilihannya dari database operasional bila tabelnya ada (`generate.py:473`),
  dan tabel itu tidak ikut diperbarui oleh submit. Layar memaksa medan rujukan
  dipilih dari daftar (`application.tsx:563`), jadi staf tidak bisa memilih
  supplier yang baru ditambahkan. Rekomendasi: pilihan dibaca dari log pada
  jam yang diminta (cabang cadangannya sudah ada). Alternatif: harness
  menjalankan compile ulang setelah setiap submit, meniru operator.
- **G4. Nilai tidak diperiksa di pintu.** Semua nilai disimpan sebagai teks
  (`generate.py:595`) dan baru di-cast compiler, jadi satu nilai "dua puluh" di
  medan desimal menggagalkan seluruh tabel. Lewat API, rujukan ke URI yang tidak
  dikenal langsung dibuatkan entity baru tanpa suara. Rekomendasi: tolak di
  pintu dengan penolakan terstruktur (`components/refusal`): nilai harus cocok
  tipenya, rujukan harus entity yang ada di kelas range-nya. Tanpa ini, hasil
  eksperimen tercampur antara salah ketik staf dan kegagalan komposisi.

### Dicatat sebagai temuan, tidak diperbaiki dulu

- **G5.** Satu formulir satu subjek: PO lima baris = enam aksi. Mempengaruhi
  kejujuran "satu tindakan = satu intent".
- **G6.** `recorded_at` selalu waktu sekarang (benar: pengguna tidak boleh
  memundurkan jam kernel). Cerita satu bulan tercatat dalam beberapa menit;
  "dicatat terlambat" disimulasikan dengan urutan pemasukan. `as_of` tetap
  bisa diuji dalam skala menit.
- **G7.** Database operasional dipakai bersama per nama tabel; dua aplikasi
  dengan tabel `Item` saling timpa. Eksperimen memakai database sendiri.
- **G8.** Bentrok nama kelas (§4).

## 6. Rancangan

### Lingkungan

- Database `uniti_exp` dan `uniti_exp_ops`. Skema kernel diterapkan ke yang
  pertama. `@uniti/core` v1 dan v2 didaftarkan dengan
  `python -m components.modules register @uniti/core v2 --actor exp`.
- Root store sendiri, misalnya `build/exp/packages`, diikuti `packages` sebagai
  root kedua (`UNITI_PACKAGES="build/exp/packages;packages"`).
- API sendiri di port 8300 dengan tiga variabel itu.
- **Jangan menyentuh `uniti_dev`, `uniti_dev_ops`, atau `build/dev/`.**

### Satu pintu untuk semua subagent

Skrip klien tipis (di luar `components/`, misalnya `scratch/` atau scratchpad
sesi) dengan perintah: `draft`, `step`, `seal`, `catalogue`, `form`, `submit`,
`read`. Aturannya:

- Meniru layar persis: medan rujukan **hanya** diisi dari pilihan yang
  ditawarkan `form`; subjek dan nilai lain diketik bebas.
- Setiap panggilan dicatat ke satu berkas transkrip (waktu, pemeran, perintah,
  argumen, jawaban), sehingga eksperimen bisa diputar ulang dan diaudit.
- `seal` memanggil CLI seal; ini gerbang resmi yang sama dengan `seal()`.

### Pemeran

| subagent | melihat | tidak melihat |
|---|---|---|
| penulis cerita | tidak ada soal Uniti; menulis kejadian satu bulan PT Maju dalam bahasa bisnis | semua sistem |
| penulis `stok-a` (gaya Odoo) ∥ `stok-b` (gaya ERPNext) | deskripsi peran core, daftar langkah Studio, klien | satu sama lain, repo, cerita |
| penulis `pembelian`, `mitra`, `buku-besar` | seperti di atas **+ katalog** modul yang sudah di-seal | repo, cerita |
| implementer `@ptmaju` | katalog, lima pertanyaan bisnis, klien | repo, cerita, angka kebenaran |
| staf gudang, pembelian, keuangan | bagian cerita masing-masing, formulir aplikasi | yang lain |
| sesi pelaksana | semuanya: mengatur, mengamati, membandingkan | – |

Kosakata gaya Odoo/ERPNext dipakai sebagai **bentuk**, dicek ke dokumentasi
publik keduanya saat menulis brief. Datanya karangan; setiap modul menyatakan
`purpose: demonstration`. Kode komponen tetap bebas istilah domain.

**Keterbatasan yang harus dicatat di Hasil:** subagent secara teknis bisa
membaca repo. Kemandirian dijaga dengan instruksi dan satu pintu klien, bukan
sandbox. Setiap subagent melaporkan semua perintah yang dijalankannya, dan
pelaksana memeriksanya.

### Skenario: PT Maju, satu bulan

Distributor bahan kue, dua gudang, membeli dari supplier, menjual ke toko roti.

**Lima pertanyaan aplikasi** (untuk implementer):
1. stok per bahan per gudang
2. nilai stok
3. hutang per supplier
4. PO yang belum diterima
5. selisih antara yang dipesan dan yang diterima

**Jebakan**, masing-masing satu jenis di §3. Sebagian ditanam di cerita,
sebagian dibiarkan muncul sendiri:

| jebakan | jenis | cara muncul |
|---|---|---|
| dua modul menamai kelas sama | T1 | dibiarkan muncul |
| qty positif + arah lawan qty bertanda | T4 | dari gaya `stok-a` / `stok-b` |
| bahan dibeli per sak 25 kg, dipakai per kg | T5 | ditanam di cerita |
| pembayaran kas juga `Flow` | T6 | dari `buku-besar` |
| truk yang sama dicatat staf gudang dan staf pembelian | T7 | dibiarkan muncul (dua formulir tersedia) |
| supplier yang juga pelanggan | T8 | ditanam di cerita |
| PO banyak baris, penerimaan sebagian, retur ke supplier | T9 | ditanam di cerita |
| satu modul di v2 mengubah arti qty | T10 | pelaksana meminta revisi pada satu penulis |
| penerimaan yang baru ketahuan belakangan; satu salah ketik lalu dikoreksi | dua jam, G2 | ditanam di cerita |

### Angka kebenaran

Dihitung dari cerita **sebelum** compiler dijalankan, tanpa Uniti (tangan atau
spreadsheet), untuk lima pertanyaan, per akhir minggu 1–4, dan untuk dua
pasangan jam (sekarang; sebelum penerimaan yang terlambat dicatat). Tanpa
pembanding, angka yang salah tanpa suara tidak akan ketahuan.

## 7. Tahapan

| # | isi | kode berubah? | selesai jika |
|---|---|---|---|
| 0 | Baca dokumen ini. Konfirmasi ke pemilik: G1–G4, kriteria gerbang (§9), tabel prediksi (§3). | tidak | pemilik menyetujui |
| 1 | Tutup G1–G4, test lebih dulu, satu commit per celah. `make test` hijau. | ya, kecil | test baru lulus, semua test lama lulus |
| 2 | Siapkan lingkungan (§6) dan klien. | skrip | core terdaftar di `uniti_exp`, klien bisa `draft`/`step` |
| 3 | Cerita bisnis + angka kebenaran. | tidak | cerita + tabel angka |
| 4 | Gelombang 1: `stok-a` ∥ `stok-b` → seal. Gelombang 2: `pembelian`, `mitra`, `buku-besar` → seal. | tidak | lima modul ter-seal, atau penolakannya tercatat |
| 5 | Implementer menyusun `@ptmaju` → seal. | tidak | aplikasi ter-seal |
| 6 | Staf memasukkan data minggu demi minggu, kronologis. **Setiap akhir minggu:** angka dibandingkan dengan kebenaran, selisih ditelusuri ke aksinya. | tidak | empat titik periksa |
| 7 | Tukar `stok-a` → `stok-b` (aplikasi versi baru), laporan kecocokan dan kesehatan, revisi arti (T10), koreksi (G2). Beri label setiap jebakan. | tidak | tabel hasil §8 terisi |
| 8 | Untuk setiap ✗ dan ☠: perbaikan minimal, tempatnya, dan ongkos core-nya. | tidak | daftar perbaikan |
| ⛩ | Pemilik memutuskan di gerbang (§9). | – | keputusan tercatat |

Langkah 3–8 **tidak mengubah mekanisme.** Sistem diukur apa adanya dulu;
perbaikan dikerjakan setelah gerbang. Pemilik diajak melihat di akhir langkah
0, 1, dan di gerbang.

## 8. Label hasil dan bentuk laporan

✓ benar · ⛔ ditolak dengan jelas · 👁 terlihat di laporan · 🔍 terdeteksi dari
data · ✗ tidak bisa diungkapkan · ☠ **salah tanpa suara**

Satu baris per jebakan:

| jebakan | jenis | prediksi | hasil | bukti (transkrip / intent / sel) | perbaikan minimal | tempatnya (modul · deklarasi core · eksekutor · penyelarasan · aplikasi · di luar mekanisme) | ongkos core |
|---|---|---|---|---|---|---|---|

Ditambah: jumlah deklarasi core yang dibutuhkan, dan daftar temuan yang tidak
diprediksi.

## 9. Kriteria gerbang

- **Lanjut:** tidak ada ☠ tersisa setelah perbaikan yang semuanya deklaratif;
  core bertambah ≤ ±5 deklarasi dan semuanya lolos uji masuk (§2); tidak ada
  aplikasi yang harus menyebut nama privat modul lain kecuali disengaja.
- **Sesuaikan:** sebagian ☠ hanya selesai dengan eksekutor baru. Masih
  diterima bila eksekutornya generik (misalnya *matching* janji ↔ pemenuhan)
  dan lolos uji masuk.
- **Pikir ulang:** ada ☠ yang hanya bisa dicegah dengan logika per kasus, atau
  dengan model kanonik pusat yang memilih pemenang.

Posisi mundur bila "pikir ulang": **komposisi eksplisit.** Peran dipakai untuk
menemukan dan menyambungkan, dan setiap aplikasi wajib menyatakan modul mana
yang resmi untuk setiap hitungan; penjumlahan lintas modul tidak pernah
otomatis. Log, provenance, dan dua jam tidak terpengaruh.

## 10. Aturan kerja

Semua aturan `REFACTOR_P2.md` §4 berlaku: kode bebas istilah domain, test lebih
dulu untuk mekanisme, satu commit per langkah utuh, data karangan menandai
dirinya. Ditambah:

- Tidak ada YAML modul yang ditulis tangan. Tidak ada `load_facts.py`. Tidak ada
  `INSERT` langsung. Semua lewat klien.
- Penolakan yang diterima subagent adalah data eksperimen: dicatat utuh, tidak
  dihindari.
- Jangan memperbaiki mekanisme di tengah langkah 3–8. Kalau sesuatu memblokir
  total, berhenti, catat, dan tanyakan ke pemilik.

---

## Hasil

*Diisi oleh sesi pelaksana. Ringkasannya disalin ke `REFACTOR_P2.md` irisan 2.8.*

### Keputusan langkah 0

Disetujui pemilik, 24 September 2026. Semua rujukan kode di dokumen ini
diperiksa dan cocok (nomor baris bergeser sedikit); 191 test lulus di `f1da813`.

- **G1–G4 dikerjakan** seperti di §5, dengan tiga penegasan:
  - **G3:** pilihan formulir dibaca dari log pada jam yang diminta, bukan
    compile ulang oleh harness. Proyeksi sendiri tidak basi (dihitung langsung
    dari log lewat `preview`); yang basi hanya pilihan.
  - **G4 bukan hakim kedua:** pemeriksaan tipe di pintu memakai peta tipe
    compiler yang sama, sehingga yang diterima pintu tidak bisa ditolak cast.
    Rujukan harus entity yang ada di kelas range-nya (atau turunannya).
  - **G2:** hanya meneruskan `revokes`; id yang ditarik diambil dari `stated`
    jawaban submit atau dari `/api/app/cell`.
- **Kriteria gerbang (§9) dan tabel prediksi (§3) tidak berubah,** dengan satu
  catatan pada T4: deskripsi `amount` di `@uniti/core@v2` sudah berbunyi
  *"In is positive, out is negative"* — core sudah memilih gaya bertanda, tapi
  hanya sebagai prosa tanpa eksekutor. Deskripsinya dibiarkan (ter-seal). Brief
  `stok-a` menegaskan bentuk Odoo (qty selalu positif, arah dari lokasi
  asal/tujuan). Kalau penulisnya tetap menyesuaikan diri ke prosa core, hasil
  T4 dicatat **"✓ hanya karena konvensi prosa"**, bukan ✓.

### Langkah 1: celah ditutup

Empat commit, test lebih dulu di masing-masing; 199 test lulus (191 + 8),
replay identik.

| celah | commit | isi |
|---|---|---|
| G1 | `da8c7ee` | `aggregate` menerima `where` (slot=Kelas) dan `convert_using`/`convert_on`/`convert_factor`, ditulis persis seperti yang dibaca compiler; langkahnya tidak menilai, `convert` separuh jadi lubang `convert_keys` |
| G2 | `845a73f` | `/api/app/state` meneruskan `revokes`; setiap jawaban membawa `stated` (medan → id); penarikan murni tidak menyatakan ulang kelas |
| G3 | `0b174c5` | pilihan formulir dibaca dari log pada jam formulir; generator tidak lagi membuka database operasional sama sekali |
| G4 | `391202c` | tiga penolakan baru: `value_not_of_type` (cast yang sama dengan compiler; `SQL_TYPE` pindah ke generator), `not_among_the_choices` (pembaca yang sama dengan pilihan formulir), `revokes_another_statement` |

Dua hal yang ikut ditemukan:

- **G3 mengakhiri satu prinsip P1:** "formulir membaca database operasional,
  tidak pernah log" (dari `CLAUDE.md` P1 yang sudah tidak ada). Di P2 proyeksi
  sudah dibaca langsung dari log, jadi prinsip itu memang sudah tidak berlaku;
  sekarang pilihan formulir mengikutinya.
- **`revokes_another_statement` melampaui G2 sebagaimana ditulis.** Kernel
  hanya menuntut baris yang ditarik ada; id dari baris yang salah akan menarik
  pernyataan subjek lain tanpa suara. Dimasukkan ke G4 karena alasannya sama.

Dicatat, tidak diperbaiki:

- **Label pilihan adalah identifier** (`ING-COCOA`), bukan nama — sesuai map,
  karena belum ada pengikat `label` (`REFACTOR_P2.md` §8).
- **Subjek yang sudah menjadi kelas lain** (dibaca dari kode, belum diuji):
  formulir kelas B dengan subjek milik kelas A menyatakan ulang `entity_class`,
  dan pernyataan terbaru menang — subjeknya berpindah kelas tanpa suara. Staf
  yang salah memilih subjek akan menabraknya; kalau terjadi, dicatat sebagai
  temuan eksperimen.

### Langkah 2: lingkungan dan klien

- `scratch/exp/env.sh` (tiga variabel + `UNITI_API=http://localhost:8300`),
  `scratch/exp/setup.sh` (membuat `uniti_exp` dan `uniti_exp_ops`, menerapkan
  skema kernel, mendaftarkan `@uniti/core` v1 dan v2). Root store pertama
  `build/exp/packages`; draft modul baru jatuh ke sana.
- API di port 8300 dengan tiga variabel itu; web app ikut tersaji di sana.
- **Klien:** `sh scratch/exp/u.sh --as <siapa> <perintah>`. Perintah: `ops`,
  `step`, `draft`, `seal` (memanggil CLI seal), `catalogue`, `app`, `form`,
  `submit`, `read`, `table`. `submit` meminta formulir pada `valid_from` yang
  sama lebih dulu dan menolak medan rujukan yang tidak ditawarkan ("REFUSED BY
  THE SCREEN"), sebelum API ditanya. Setiap panggilan dicatat ke
  `build/exp/transcript.jsonl` (waktu, pemeran, perintah, argumen, jawaban
  utuh).
- **Uji asap** dengan modul sekali pakai `@smoke/*`, lalu dihapus dan log
  direset: 21 langkah Studio → seal; aplikasi dengan aggregate atas `Flow` →
  seal; submit; penolakan layar (rujukan tak ditawarkan); penolakan pintu
  (`value_not_of_type`); koreksi 50 → 5 lewat `--revoke`; angka 5 di
  proyeksi, 0 baris pada `valid_at` sebelum pergerakan. Transkripnya disimpan
  di `build/exp/smoke-transcript.jsonl`.
- `uniti_dev`, `uniti_dev_ops`, dan `build/dev/` tidak disentuh.

### Tahap pelaksanaan langkah 3–8

Atas permintaan pemilik, langkah 3–8 dipecah menjadi tahap dengan titik
periksa di akhir masing-masing, supaya progres dan arahnya bisa diikuti.
Mekanisme tetap tidak diubah di tahap mana pun (§10).

| tahap | langkah | isi | titik periksa pemilik |
|---|---|---|---|
| A | 3 | cerita PT Maju + angka kebenaran (dihitung dua kali: oleh penulis cerita, dan oleh pelaksana dari tabel kejadian) | cerita, letak jebakan, angka kebenaran |
| B | 4, gelombang 1 | `stok-a` (Odoo) ∥ `stok-b` (ERPNext) → seal | cara dua penulis independen memodelkan stok; nasib T4 |
| C | 4, gelombang 2 | `pembelian`, `mitra`, `buku-besar` → seal | apa yang dipakai ulang dari katalog; T1, T6, T8 |
| D | 5 | implementer menyusun `@ptmaju` → seal | pertanyaan mana yang bisa diungkapkan; T9 |
| E | 6 | staf memasukkan W1–W4; perbandingan tiap akhir minggu | setelah W2 dan setelah W4 |
| F | 7 | tukar `stok-a` → `stok-b`, kecocokan, kesehatan, T10, koreksi | tabel hasil §8 terisi |
| G | 8 + ⛩ | perbaikan minimal per ✗/☠, lalu gerbang | keputusan gerbang |

### Tahap A: cerita dan angka kebenaran

- **Penulis cerita** (subagent tanpa alat, tidak diberi tahu soal sistem apa
  pun) menulis Agustus 2026 PT Maju: 6 bahan, 4 pemasok, 5 pelanggan, 2
  gudang, 60 kejadian bisnis dalam 87 baris. Berkasnya di `build/exp/story/`:
  `story.md` utuh, `profile.md`, dan dua belas bagian `W<n>-<departemen>.md`
  — satu-satunya yang nanti dilihat staf departemen itu.
- **Jebakan yang tertanam di cerita:** satuan beli ≠ satuan stok untuk lima
  bahan (sak 25 kg, karung 50 kg, karton 15 kg, karton 20 bungkus); PO banyak
  baris dengan penerimaan sebagian dan dua baris masih terbuka di akhir bulan;
  retur gula ke pemasok dengan nota kredit; pembayaran tunai dan transfer,
  sebagian-sebagian; **CV Kakao Lestari** pemasok cokelat sekaligus pelanggan
  terigu, dengan nama berbeda di tiap departemen; **setiap truk pemasok
  dicatat dua kali** — Gudang (BPB) dan Pembelian (SJ vs PO); **kiriman
  DP-7731** tiba di GC 7 Agu, baru dicatat 19 Agu; **salah ketik** cokelat
  500 kg (seharusnya 50) pada 12 Agu, dikoreksi 15 Agu; biaya standar terigu
  naik 9.000 → 9.400 per kg mulai 18 Agu.
- **Yang tidak ada di cerita dan memang bukan tugasnya:** T1, T4, dan T10
  datang dari penulis modul dan dari pelaksana.
- **Dua perbedaan dari rencana yang dicatat:** retur berasal dari stok Juli,
  jadi tidak menyentuh baris PO mana pun (T9 tetap diuji lewat PO banyak baris
  dan penerimaan sebagian). Ada piutang (faktur penjualan dan penerimaan dari
  pelanggan) yang tidak ditanyakan lima pertanyaan; dibiarkan sebagai muatan
  bagi `buku-besar`.
- **Angka kebenaran dihitung dua kali, terpisah:** oleh penulis cerita (Part
  3 dari hasilnya), dan oleh pelaksana lewat `build/exp/story/truth.py` dari
  catatan departemen, bukan dari tabel penulis. **Semua angka sama:** stok per
  bahan per gudang, nilai stok, utang per pemasok, baris PO terbuka, dan
  selisih per baris, pada akhir W1–W4 dan pada "31 Agu tanpa kiriman
  terlambat". Keluarannya di `truth.txt`. Angka kunci akhir bulan: nilai stok
  **Rp 152.835.000**, utang **Rp 58.400.000** (S1 25,4 jt · S2 17,4 jt ·
  S3 13,5 jt · S4 2,1 jt), baris terbuka **PO-03 susu (4 sak)** dan **PO-06
  gula (8 karung)**.
- **Pasangan jam yang akan dibandingkan dengan sistem.** `truth.py` juga
  menghitung angka "seperti tercatat pada hari itu":
  - kiriman terlambat: `valid_at` 7 Agu, `as_of` sebelum dicatat → margarin
    GC 60 dan susu GC 50; sesudahnya → 210 dan 150;
  - salah ketik: `valid_at` 14 Agu, `as_of` sebelum koreksi → cokelat GU 580;
    sesudahnya → 130.

  "31 Agu tanpa kiriman terlambat" tidak bisa dibaca lewat `as_of`, karena
  entri berjalan kronologis dan semua yang dicatat sesudah 19 Agu ikut hilang.
  Angka itu disimpan hanya sebagai pembanding hitungan.

### Tahap B: dua modul stok

Brief di `build/exp/briefs/` (`primer.md` bersama, `stok-a.md`, `stok-b.md`).
Bentuk Odoo diperiksa ke dokumentasi publiknya (lokasi dan lokasi virtual; UoM
dan Purchase UoM dengan rasio per kategori). Untuk ERPNext, halaman yang dibuka
tidak menyebut rinciannya; bentuk yang dipakai (buku besar stok, `actual_qty`
bertanda, `conversion_factor` ke satuan stok) berasal dari pengetahuan
pelaksana dan belum dicocokkan dengan dokumentasinya. Kedua penulis bekerja
bersamaan, tanpa melihat satu sama lain, repo, atau cerita.

| | `@alpha/stock@v1` (Odoo) | `@beta/stock@v1` (ERPNext) |
|---|---|---|
| kelas | UomCategory, Uom, Product, Location, Warehouse, StockMove | UOM, Item, UOMConversion, Warehouse, StockEntry, StockEntryDetail, StockLedgerEntry, Bin |
| peran | Product → Resource; StockMove → **Event, bukan Flow**; sisanya Thing | Item → Resource (+Thing); **StockLedgerEntry → Flow** (`actual_qty`/`item`/`posting_date`); StockEntry → Event |
| arah | qty selalu positif, dari `source_location` ke `destination_location` | tanda `actual_qty`; transfer = dua entri |
| satuan | move menyimpan satuannya; `product_qty` = qty × rasio ÷ rasio (expression) | buku besar selalu dalam satuan stok; `transfer_qty` = qty × faktor (expression) di baris dokumen |
| stok di tangan | tidak dihitung modul ("aplikasi harus group by product dan location") | `Bin.qty_on_hand` = aggregate `actual_qty` per item per gudang |
| panggilan / ditolak | 102 / 1 (`not_attached`) | 136 / 1 (`operation_arguments`) |

- **T4: tidak diam.** Penulis Odoo menolak mengisi `Flow` dan menjelaskan
  sebabnya: `amount` harus bertanda, sedangkan satu move Odoo sekaligus "masuk"
  untuk satu lokasi dan "keluar" untuk lokasi lain. Konsekuensinya: aplikasi
  yang ditulis terhadap `Flow` tidak akan melihat satu pun pergerakan
  `@alpha/stock`. Ini diuji di Tahap D/F. **Prosa core bertanda memilih
  pemenang** (§2 butir 4): bentuk Odoo tidak bisa mengisi satu-satunya peran
  yang membuat saldo bisa dijumlahkan.
- **Laporan penulis cocok dengan transkrip** (jumlah panggilan per perintah
  dan penolakannya). Keduanya mengaku melanggar aturan 1 secara kecil: output
  klien dipotong dengan `sed`/`head`/`tail`. Tidak ada berkas yang dibuka.

**Temuan yang tidak diprediksi (belum diperbaiki, sesuai §10):**

- **U1 ☠ — dua modul berbagi predikat tanpa suara.** Kedua penulis memilih
  prefix `stk`, yang di-expand ke namespace berbeda
  (`https://uniti.example/alpha/stock/` dan `.../beta/stock/`). Registry
  kernel menyimpan `slot_uri` sebagai **CURIE mentah**, jadi `stk:uom` dan
  `stk:warehouse_name` milik `@beta/stock` jatuh ke entity predikat yang sudah
  didaftarkan `@alpha/stock`. Seal hanya melaporkan "25 URIs minted" untuk 27
  slot. `uom` di alpha berarti "satuan stok sebuah Product"; di beta, "satuan
  sebuah baris atau konversi". Keduanya sekarang satu predikat di log. Ini
  lebih dalam dari T1: bukan nama kelas di LinkML, tetapi identitas predikat
  di kernel, padahal prinsipnya "identitas predikat adalah `slot_uri`".
- **U2 — nama kelas telanjang di `entity_class`** (item terbuka lama, sekarang
  konkret). Kedua modul punya kelas `Warehouse`, dan fakta kelas disimpan
  sebagai nama, bukan URI. Ditambah U1 (`stk:warehouse_name` bersama),
  gudang yang dicatat lewat alpha akan terbaca sebagai `Warehouse` beta
  setelah penukaran di Tahap F. Hasilnya mungkin terlihat "berhasil", padahal
  kebetulan.
- **U3 ☠ — aturan di kelas entity tidak pernah dijalankan.** `plan_entities`
  memperlakukan setiap kolom sebagai kolom "stated", jadi `parameter` dan
  `expression` di kelas tanpa aggregate selalu NULL. Kolomnya malah muncul
  sebagai medan formulir yang bisa diketik orang. Seal, check, dan lubang
  Studio tidak bersuara. Kedua modul kena: `product_qty` (alpha, justru kolom
  yang menurut penulisnya harus dijumlahkan) dan `transfer_qty` (beta).
- **U4 — sintaks ekspresi tidak pernah diajarkan dan tidak diperiksa di
  gerbang.** Kedua penulis menulis `qty * conversion_factor` tanpa `{kolom}`.
  Compiler akan menolaknya (`expression_not_arithmetic`), tetapi hanya saat
  memancarkan SQL tabel ber-aggregate. Karena U3, penolakan itu tidak pernah
  terjadi. Deskripsi langkah `expression` tidak menyebut kurung kurawal, dan
  primer eksperimen juga tidak.
- **U5 👁 — aggregate mengubah bentuk kelas.** Penulis ERPNext menaruh
  aggregate di `Item`, dan `Item` berubah dari daftar entity menjadi tabel
  ber-group ("A class the map gives an aggregate is a grouping"). Ini terlihat
  di draft ("Item (grouped)"). Penulisnya menyadarinya dan menariknya kembali.

### Tahap C: mitra, pembelian, buku besar

**Urutan diubah sedikit dari §7:** `mitra` di-seal lebih dulu, lalu
`pembelian` ∥ `buku-besar`. Dengan begitu dua penulis terakhir melihat katalog
yang sudah berisi modul kontak, dan T8 bisa diamati sebagai pilihan nyata
(pakai ulang `Partner` orang lain, atau buat sendiri). Brief di
`build/exp/briefs/` (`mitra.md`, `pembelian.md`, `buku-besar.md`, ditambah
`catalogue.md` untuk cara membaca katalog dan `pin`). Primer tidak diubah
supaya kondisinya sama dengan Tahap B; U4 sengaja tidak "diajarkan". Bentuk
Odoo (kontak, akuntansi) dan ERPNext (pembelian) berasal dari pengetahuan
pelaksana, belum dicocokkan dengan dokumentasi publik.

**Gangguan lingkungan:** container Postgres berhenti di tengah tahap (exit
255, kemungkinan Docker di-restart), sehingga tiga seal pertama `mitra` gagal
dengan `ConnectionTimeout`. Container dinyalakan lagi tanpa mengubah isinya
(log tetap 4 intent), API dinyalakan ulang dengan `.venv`, dan penulisnya
diminta menjalankan seal sekali lagi. Bukan penolakan; tidak dihitung.

| | `@gamma/partner@v1` (Odoo) | `@delta/purchase@v1` (ERPNext) | `@epsilon/accounting@v1` (Odoo) |
|---|---|---|---|
| kelas | Partner, PartnerCategory, PartnerTag, Country | Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptItem, PurchaseOrderItemBalance (grouped) | Account, Journal, JournalEntry, JournalItem, Payment, Reconciliation |
| pin | – | **`@beta/stock@v1`** (Item, UOM, Warehouse, `item`/`uom`/`conversion_factor`/`warehouse` dipakai langsung) | **`@gamma/partner@v1`** (Partner) |
| peran | semua Thing saja | PurchaseReceipt → Event; **sengaja tidak Flow** ("penerimaan akan terhitung dua kali dengan buku besar stok") | Account → **Resource**; **JournalItem → Flow** (`balance`/`account`/`item_date`); JournalEntry, Payment → Event |
| arah | – | tanda di baris penerimaan (retur negatif) | debit/kredit ≥ 0, `balance` = debit − kredit bertanda; `payment_amount` positif, arah dari `payment_type` |
| satuan | – | qty dalam satuan beli + faktor + qty satuan stok (expression) | satu mata uang |
| panggilan / ditolak | 75 / 0 (3 seal gagal karena database) | 146 / 2 (`name_taken`, `operation_arguments`) + 1 lubang `not_a_class` | 141 / 2 (`not_attached`, `operation_arguments`) + 1 lubang `not_a_class` |

Laporan ketiga penulis cocok dengan transkrip. Prefix ketiganya berbeda
(`prt`, `pur`, `acc`), jumlah URI yang di-mint sama dengan jumlah slot: U1
tidak terulang, tapi hanya karena kebetulan.

**Jebakan tahap ini:**

- **Pakai ulang dari katalog: terjadi, tapi terbelah.** `buku-besar` memakai
  `Partner` milik `mitra`; `pembelian` menolaknya ("`supplier_rank` harus naik
  setiap pembelian dan modul ini tidak akan menaikkannya; memaksa modul kontak
  ke setiap pemakai") dan membuat `Supplier` sendiri. `pembelian` memakai
  `@beta/stock` langsung sampai ke slot-slotnya. Tidak ada yang memakai
  `@alpha/stock`.
- **T8 — terjadi persis seperti prediksi: tidak ada jalur.** Pemasok yang sama
  sekarang punya dua identitas di dua modul: `Supplier` (`@delta/purchase`)
  dan `Partner` (`@gamma/partner`, lewat `@epsilon/accounting`). Tidak ada
  yang menghubungkan keduanya; "utang per pemasok" (dari jurnal) dan "PO
  terbuka per pemasok" (dari pembelian) memakai dua daftar pemasok yang
  berbeda. Di sisi lain, kasus Kakao Lestari (pemasok sekaligus pelanggan)
  ditangani wajar oleh `Partner` (satu entity, dua peringkat).
- **T1 — ditolak di dalam satu draft, masih diam antar modul.** `pembelian`
  mencoba `add_slot item` dan ditolak `name_taken` karena `@beta/stock` yang
  di-pin sudah memilikinya (⛔, jelas). Tapi karena `@delta/purchase` mem-pin
  `@beta/stock`, aplikasi yang memakai `@alpha/stock` dan `@delta/purchase`
  bersama akan membawa **dua kelas `Warehouse`**. Diuji di Tahap D.
- **T6 — dua hal sekaligus.** Pengisi `Flow` sekarang `StockLedgerEntry` (kg,
  bungkus) dan `JournalItem` (rupiah); pengisi `Resource` sekarang `Product`,
  `Item`, dan **`Account`**. Aplikasi yang menjumlahkan `Flow` per `affects`
  akan ikut menjumlahkan saldo rekening, dan satuan jumlahnya campur (T5 dan
  T6 bertemu). Apakah laporan `covers` memperlihatkannya diuji di Tahap D.
- **T7 — penulis pembelian melihatnya dan menghindar.** Ia sengaja tidak
  mengisi `Flow` supaya penerimaan tidak terhitung dua kali, dan menulis di
  deskripsi bahwa aplikasi harus memposting satu `StockLedgerEntry` per baris
  penerimaan. Pencatatan ganda tetap ada di data (formulir penerimaan dan
  formulir stok); tinggal dilihat di Tahap E apakah angkanya diam-diam dobel.

**Temuan yang tidak diprediksi (belum diperbaiki, sesuai §10):**

- **U3 ☠ — sekarang mengenai pengikat peran.** Diperiksa dengan `plan_for`
  compiler (tanpa menulis data): di `@epsilon/accounting`, `balance`
  (expression, pengikat **`amount`** Flow) dan `item_date` (parameter,
  pengikat **`moment`** Flow) berstatus `stated`. Jadi setiap aplikasi yang
  menjumlahkan `Flow` membaca `balance` kosong untuk semua baris jurnal,
  kecuali ada staf yang mengetik saldo sendiri di formulir, karena kolom itu
  muncul sebagai medan isian. Hal yang sama untuk `stock_qty`,
  `ordered_stock_qty`, dan `line_amount` di `@delta/purchase`; akibatnya
  `PurchaseOrderItemBalance.received_stock_qty` menjumlahkan kolom yang hanya
  terisi kalau staf mengetiknya. Penulis `buku-besar` juga menaruh
  `parent_state` dan `item_account_type` sebagai parameter, dan menyuruh
  aplikasi memfilter pada keduanya.
- **U4 — sekarang ⛔, tapi setelah seal.** `PurchaseOrderItemBalance` ditolak
  compiler: `pending_stock_qty` ditulis `line_ordered_stock_qty -
  received_stock_qty` tanpa `{…}` (`expected arithmetic over {columns}`). Modul
  sudah ter-seal dan tercantum di katalog, tapi tabel ini tidak akan pernah
  bisa dihitung. Seal tidak menjalankan pemeriksaan yang sama dengan compiler.
- **U6 👁 — satu aturan per slot, ditimpa tanpa penolakan.** Aturan turunan
  menempel di slot, bukan di pasangan kelas–slot. `pembelian` memakai
  `stock_qty` di baris PO dan baris penerimaan: aturan penerimaan menimpa
  aturan PO. Kemudian `parameter` menimpa `expression` pada
  `ordered_stock_qty`. Kedua kejadian hanya terlihat dengan membaca `draft`
  teliti; langkahnya diterima tanpa kata.
- **U7 ✗ — `where` hanya bisa menyaring kelas, bukan nilai.** Dua penulis
  terpisah butuh filter status ("posted" di jurnal, "Submitted" di
  penerimaan) dan sama-sama ditolak `not_a_class`. Keduanya mundur ke
  konvensi prosa: "jumlahkan hanya item yang posted" (buku besar) dan "catat
  penerimaan hanya setelah barang masuk; koreksi dengan baris balik"
  (pembelian). Ini kebutuhan nyata dari dua modul independen (§2 butir 3).
- **U8 — tanda `required` tidak tampak di draft.** `mitra` mengira
  `set_slot … required=true` tidak tersimpan karena `draft` tidak
  menunjukkannya; di YAML hasil seal kelima-limanya ada. Kecil, soal
  keterlihatan.
- **Utang bertanda negatif (catatan, bukan temuan mekanisme).** Di
  `@epsilon/accounting` utang ke pemasok adalah saldo negatif pada rekening
  utang. Kebenaran menanyakan utang sebagai angka positif; aplikasi harus
  membalik tandanya. Deskripsinya jelas, jadi yang diuji di Tahap D adalah
  apakah implementer membacanya.

### Tahap D: aplikasi `@ptmaju/app`

Brief di `build/exp/briefs/implementer.md` + `implementer-tools.md` (primer
dan `catalogue.md` yang sama, aturan 3–4 diganti). Implementer melihat
katalog, lima pertanyaan dalam bahasa bisnis, gambaran tiga departemen, dan
klien; tidak melihat cerita atau angka kebenaran. Satu kendala diberikan:
**tim gudang sudah memilih `@alpha/stock@v1`**, supaya penukaran di Tahap F
tetap stok-a → stok-b. Implementer juga diberi `app/check`, `app/roles`,
`app/health`, dan `table` (tanpa `submit`), karena di UI laporan itu memang
miliknya.

**Hasil: `@ptmaju/app@v5`**, 610 panggilan, lima seal. v1–v4 dibuang oleh
implementer sendiri setelah membaca laporan dan `table`.

| | pilihan implementer | alasannya |
|---|---|---|
| `@alpha/stock@v1` | pin (diwajibkan) | Product, Uom, Location, Warehouse, StockMove; aturan turunannya tidak dipakai karena "tidak ada yang membacanya" (U3) |
| `@gamma/partner@v1` | pin | satu Partner untuk pemasok dan pelanggan |
| `@delta/purchase@v1` | **tidak** | membawa Item/Warehouse `@beta/stock` di samping `@alpha/stock` (T1), Supplier sendiri (T8), dan tabel saldonya tidak punya baris untuk baris PO yang belum menerima apa pun |
| `@epsilon/accounting@v1` | **tidak** | setiap faktur/pembayaran harus jadi jurnal dua sisi yang ditulis tangan; `Payment` sendiri tidak mengubah saldo, "jebakan bagi staf" |
| `@beta/stock@v1` | tidak | gudang memilih alpha |

Yang dibuat sendiri di aplikasi: Ingredient (turunan Product, membawa
`std_cost`), PurchaseOrder/Line, DeliveryCheck/Line, SupplierDocument +
PayableKind (tanda dan faktor per jenis dokumen), CustomerInvoice/Payment.
Tiga tabel jawaban: `StockOnHand` (Q1, Q2), `SupplierBalance` (Q3),
`OrderLineStatus` (Q4, Q5).

**Peran tidak dipakai sama sekali untuk menjawab.** Tidak ada kelas yang
mengisi `Flow` di aplikasi ini; setiap aggregate menyebut kelasnya
(`over: StockMove`, `over: SupplierDocument`, `over: DeliveryCheckLine`). Tanpa
diminta, implementer jatuh ke posisi mundur §9, "komposisi eksplisit". Ini
bukan pilihan gaya: `@alpha/stock` tidak mengisi Flow (T4), dan Flow yang ada
(`JournalItem`) terkena U3.

**Jebakan tahap ini:**

- **T4 — ✓, tapi dengan menyebut kelas, bukan lewat peran.** Stok dihitung
  `qty_in` (aggregate per `destination_location`) − `qty_out` (per
  `source_location`) atas `StockMove`. Arah gaya Odoo bisa diungkapkan; peran
  `Flow` tidak ikut.
- **T6, T7, T8 — tidak terjadi di aplikasi ini, karena dihindari.** Flow tidak
  dipakai (T6), hanya satu formulir penerimaan per departemen yang dihitung
  (T7: gudang di StockMove, pembelian di DeliveryCheckLine; keduanya ada tapi
  menjawab pertanyaan berbeda), dan hanya satu daftar mitra (T8). Harga
  penghindarannya: dua modul dari katalog tidak terpakai.
- **T9 — sebagian ✗.** Header + baris PO bisa diungkapkan dengan kelas
  aplikasi sendiri. Tapi "total per gudang" di atas `StockOnHand` ditolak
  (`no_type_slot`: aggregate hanya bisa di atas kelas tercatat, bukan tabel
  hitungan), sehingga jawaban per gudang bergantung pada satu lokasi stok per
  gudang. Q4 tidak bisa disaring di tabel (U7); pembaca yang menyaring
  `ols_open_stock_qty > 0`.
- **T1 — nama slot bertabrakan, diam di seal.** `@alpha/stock` dan
  `@gamma/partner` sama-sama punya slot `category_name`. Di aplikasi yang
  mem-pin keduanya, `UomCategory.category_name` tercatat di bawah predikat
  **`prt:category_name`** milik modul kontak; `stk:category_name` hilang dari
  aplikasi. Seal dan `app/check` diam. Terlihat hanya di tabel `terms`
  `app/health` (satu URI di `PartnerCategory` dan `UomCategory`) dan di
  deskripsi formulir yang salah. Dalam aplikasi ini angkanya tidak salah;
  aplikasi lain yang membaca `UomCategory` alpha dengan predikatnya sendiri
  tidak akan melihat nama-nama ini.

**Temuan yang tidak diprediksi:**

- **U3 — terbaca dari `app/health`, tapi tanpa diagnosis.** `empty_column`
  melaporkan 0. Implementer menyimpulkannya sendiri dari `terms` (`read_by`
  kosong untuk `move_uom_ratio`) dan dari formulir yang menawarkan kolom
  hitungan sebagai isian. Label tetap ☠ untuk penulis modul; untuk pembaca
  laporan yang teliti, 👁.
- **U9 — `app/check` bilang "holds", compiler menolak.** Di v2 `check`
  menyatakan `StockOnHand`, `WarehouseStock`, `OrderLineStatus`,
  `SupplierBalance` semuanya `holds: true`; `table` menolak keempatnya
  (`expression_not_arithmetic` ×3, `no_type_slot`). Laporan yang disebut
  "pembaca yang sama dengan compiler" tidak membaca ekspresi dan tidak
  memeriksa `over` ke tabel hitungan. Implementer: "satu-satunya uji formula
  yang sungguhan adalah menjalankan `table`."
- **U10 ☠ (prediksi, sebelum data) — rujukan dicocokkan dengan identifier.**
  Dalam SQL yang dipancarkan, nilai medan rujukan adalah **URI** entity yang
  dirujuk, sedangkan identifier adalah **teks** terpisah. Tiga aturan v5
  mencocokkan keduanya:
  - `convert.on: uom_name = move_uom` (dan `pol_uom`, `dcl_uom`): `move_uom`
    merujuk Uom, `uom_name` adalah teks namanya.
  - `convert.on: pk_code = sd_kind`: `sd_kind` merujuk PayableKind.
  - `OrderLineStatus` dikelompokkan `pol_id` (teks) di sisi pesanan dan
    `dcl_order_line` (rujukan) di sisi penerimaan.

  Kalau tidak cocok, compiler memakai **`coalesce(factor, 1)`**: konversi
  gagal tanpa suara. Akibat yang diramalkan bila staf memberi subjek bergaya
  `prefix:nama` seperti petunjuk layar: satu sak dihitung 1 kg; pembayaran
  dan nota kredit **ditambahkan** ke utang (tanda +1, bukan −1); baris PO
  terbelah dua baris (dipesan di satu, diterima di yang lain), dan pada
  baris sisi-terima `ols_received_qty` membagi dengan 0, sehingga tabel itu
  gagal keras begitu penerimaan pertama dicatat. Hanya benar bila staf
  kebetulan memberi subjek persis sama dengan identifier-nya. Cara yang benar
  (mencocokkan dengan identitas entity itu sendiri) **tidak bisa diungkapkan**:
  `convert.on` dan `by` hanya menerima slot. Diuji di Tahap E.
- **`coalesce` ditolak di ekspresi** (bahasa ekspresi hanya `+ − * / ( )`),
  tapi aggregate sendiri sudah `coalesce(…, 0)`, jadi sisi kosong pengurangan
  tidak menjadi NULL. Kekhawatiran implementer soal ini tidak terjadi.
- **Pelanggaran aturan kecil:** dua keluaran `read app/health` terlalu panjang
  dan disimpan harness ke berkas; implementer membukanya dengan Read. Isinya
  hanya keluaran klien. Satu perintah membawa `2>&1 | head -0`.

### Tahap E: staf memasukkan data (W1–W2)

**Cara kerja.** Tiga staf (gudang, pembelian, keuangan), masing-masing satu
subagent sepanjang bulan yang dilanjutkan tiap minggu, seperti karyawan yang
sama. Masing-masing hanya menerima catatan departemennya (bahasa Indonesia,
dari `build/exp/story/W<n>-<dept>.md`), `staff-primer.md` (cara memakai layar
lewat klien; petunjuk subjek `prefix:name` seperti di layar web), dan panduan
implementer `staff-guide.md` apa adanya. Tidak menerima profil perusahaan,
jadi nama Kakao Lestari yang berbeda di tiap departemen tetap jebakan. Keuangan
diberi satu kalimat tambahan: satuan beli per bahan (pengetahuan yang wajar
dimiliki keuangan dan dibutuhkan formulir Ingredient). Pertanyaan staf ke
implementer dicatat, tidak dijawab.

**Urutan.** W1: gudang menyiapkan satuan/gudang/lokasi → pembelian memasukkan
pemasok → keuangan seluruh W1 (bahan, biaya standar, jenis dokumen, pelanggan,
saldo awal, dokumen) → gudang ∥ pembelian W1. W2: pembelian (membuat Kakao
Lestari) → gudang ∥ keuangan. Jam dinding ditandai di
`build/exp/clock-marks.txt` (akhir W2: `2026-09-26T08:29:55+00:00`), karena
`recorded_at` adalah jam sungguhan.

**Pembanding.** `scratch/exp/compare.py` membaca tiga tabel jawaban lewat API
yang sama (tercatat sebagai `executor`) dan membandingkannya dengan `truth.py`
*seperti tercatat* pada akhir minggu (entri kronologis, jadi "sekarang" di log
= akhir minggu itu).

| | W1 (7 Agu) | W2 (14 Agu) |
|---|---|---|
| 1. stok per bahan per gudang | 12/12 cocok | 12/12 cocok (termasuk cokelat GU 580 dari salah ketik) |
| 2. nilai stok | 118.030.000 = kebenaran | 159.180.000 = kebenaran |
| 3. utang per pemasok | **salah**: Manis Jaya 30,3 jt (benar 20,3) | **salah** 3 dari 4: Sumber Terigu 62 jt (22), Manis Jaya 37,55 jt (27,55), Dairy Prima 25,45 jt (9,45); Kakao 4,1 jt benar |
| 4/5. baris PO | **gagal**: 500, `DivisionByZero` | **gagal**, sama |

**U10 terbukti, di ketiga tabel, dengan tiga nasib berbeda:**

- **Stok: angka benar karena staf mengakali.** Staf gudang memberi subjek
  satuan `maju:kg`, `maju:sack-25kg`, …, sedangkan `uom_name`-nya "kg",
  "sack 25 kg". Konversi tidak pernah cocok dan faktornya jadi 1. Staf gudang
  **menyadarinya sendiri** dari `StockOnHand` ("terigu MAIN 2.080 kg, bukan
  4.000"), lalu mengoreksi sembilan baris ke kg/bungkus dengan `--revoke` dan
  sejak itu selalu mencatat dalam satuan stok, berlawanan dengan panduan
  ("sacks are fine"). Sistem tidak bersuara; manusia yang menyelamatkan.
- **Utang: angka salah, disadari staf, tetap salah.** Semua kolom
  `SupplierBalance` bernilai sama (jumlah semua dokumen, pembayaran ikut
  ditambahkan). Staf keuangan melaporkannya dua minggu berturut-turut sebagai
  pertanyaan ke implementer, lengkap dengan angka yang benar. Tidak ada cara
  mengakali dari formulir. Label: ☠ bagi sistem, 👁 hanya karena staf
  keuangan kebetulan menghitung sendiri.
- **Baris PO: gagal keras.** Kunci pesanan (`pol_id`, teks) dan kunci
  penerimaan (`dcl_order_line`, URI) tidak pernah bertemu, baris sisi-terima
  membagi dengan 0, dan API mengembalikan **500 tanpa penolakan terstruktur**
  (`psycopg.errors.DivisionByZero` di log API). Staf pembelian tidak bisa
  memeriksa baris terbuka sama sekali. Label: ⛔ tapi tanpa penjelasan.

**Jebakan lain yang muncul:**

- **T7 — pencatatan ganda yang berbeda isi, diam.** Truk KL-221 dicatat gudang
  500 kg (salah ketik yang ditanam) dan pembelian 50 kg. Tidak ada apa pun di
  sistem yang membandingkan dua catatan satu truk. Keuangan juga menangkap
  kiriman DP-7731 (faktur datang, penerimaan belum ada) — oleh manusia,
  dari catatan, bukan dari sistem.
- **T8 — ditangani staf dengan benar.** Faktur penjualan ke "CV. Kakao Lestari
  Bogor" dicatat keuangan pada Partner pemasok `maju:sup-kakao-lestari` yang
  dibuat pembelian, karena panduan berkata satu catatan per perusahaan. Staf
  keuangan tetap bertanya apakah keduanya perusahaan yang sama. Formulir
  pemasok/pelanggan mencampur keduanya di daftar pilihan (dicatat staf).
- **Kiriman terlambat DP-7731 belum dicatat** (sesuai cerita, dicatat 19 Agu).
  Stok W1–W2 sama dengan kebenaran seperti tercatat; pasangan jam dibaca
  setelah W3.

**Temuan kecil dari staf:** setiap submit melaporkan N pernyataan tapi hanya
N−1 id (pernyataan `uniti:uri` untuk subjek baru tidak ditampilkan); formulir
tidak punya tempat untuk hal yang ada di kertas (nomor SJ pada StockMove,
tujuan gudang pada PO, harga jual, jatuh tempo), sehingga masuk ke `--note`.

Panggilan staf sampai akhir W2: gudang 72, pembelian 44, keuangan 58. Tidak
ada penolakan formulir; satu-satunya kegagalan adalah lima kali 500 dari
`OrderLineStatus`.

### Tahap E: W3 dan dua pasangan jam

Pemilik menyetujui lanjut tanpa menjawab pertanyaan staf, dengan pesan: semua
temuan dicatat supaya evaluasi setelah eksperimen akurat dan rinci. W3 dijalankan
ketiga departemen bersamaan (data induk sudah lengkap). Akhir W3:
`2026-09-26T08:35:01+00:00` (`clock-marks.txt`).

| | W3 (21 Agu) |
|---|---|
| 1. stok per bahan per gudang | 12/12 cocok (cokelat GU 130 setelah koreksi, margarin/susu GC 210/150 setelah kiriman terlambat) |
| 2. nilai stok | 145.030.000 = kebenaran (biaya terigu 9.400 mulai 18 Agu terbaca benar) |
| 3. utang per pemasok | **salah** 3 dari 4: Manis Jaya **59,3 jt (benar 5,8)**, Sumber Terigu 80,4 jt (40,4), Dairy Prima 25,45 jt (9,45); Kakao 4,1 jt benar |
| 4/5. baris PO | **gagal**, 500 |

**Dua pasangan jam — ✓ tepat.** Dibaca lewat API dengan `as_of` = akhir W2
(`2026-09-26T08:29:55+00:00`) dan `as_of` = sekarang:

| `valid_at` | yang dibaca | `as_of` akhir W2 | kebenaran | `as_of` sekarang | kebenaran |
|---|---|---|---|---|---|
| 7 Agu | margarin GC | 60 | 60 | 210 | 210 |
| 7 Agu | susu GC | 50 | 50 | 150 | 150 |
| 14 Agu | cokelat GU | 580 | 580 | 130 | 130 |

Kiriman DP-7731 dicatat staf gudang **dan** staf pembelian dengan
`valid_from` 7 Agu pada 19 Agu (jam sungguhan: W3); salah ketik dikoreksi
staf gudang dengan `--revoke` pada catatan 12 Agu, bukan dengan pergerakan
penyesuaian. Staf gudang menjelaskan alasannya: penyesuaian akan mencatat
450 kg cokelat seolah hilang. Kernel dua jam dan G2 (revoke lewat formulir)
bekerja persis seperti dirancang; ini satu-satunya bagian yang benar tanpa
bantuan manusia di atas cacat aplikasi.

**Keputusan staf yang layak dicatat:**

- Pembelian dan gudang **sama-sama** memilih tanggal barang tiba (7 Agu)
  sebagai `valid_from` DP-7731, masing-masing menjelaskan bahwa 19 Agu hanya
  tanggal pencatatan. Pembelian bahkan menulis: "siapa pun yang membaca tabel
  7–18 Agu sebelum hari ini akan melihat angka berbeda sekarang" — pemahaman
  dua jam tanpa diajarkan.
- Staf gudang menandai bahwa nilai stok memakai 9.400 untuk semua terigu,
  termasuk stok sebelum 18 Agu. Itu sesuai kebijakan cerita (biaya standar
  yang berlaku pada tanggal itu), tapi pertanyaannya wajar.
- Keuangan tidak bisa menautkan nota kredit ke faktur tertentu (cerita tidak
  menyebutnya) dan mencatat tagihan ST-8870 sebelum pembelian mencatat
  penerimaannya — keduanya dicatat di `--note`.

### Tahap E: W4 dan ringkasan satu bulan

W4 dijalankan ketiga departemen bersamaan. Akhir W4:
`2026-09-26T08:37:13+00:00`. Perbandingan akhir memakai kebenaran lengkap
(`compare.py --final`: semua yang tercatat sampai sekarang, termasuk yang
dicatat terlambat).

| pertanyaan | W1 | W2 | W3 | W4 (31 Agu) | label |
|---|---|---|---|---|---|
| 1. stok per bahan per gudang | 12/12 | 12/12 | 12/12 | 12/12 | ✓ **karena staf gudang mengakali U10** |
| 2. nilai stok | 127.730.000 ✓ | 130.630.000 ✓ | 145.030.000 ✓ | 152.835.000 ✓ | ✓ (sama persis dengan angka penulis cerita) |
| 3. utang per pemasok | 1 salah / 3 | 3 salah / 4 | 3 salah / 4 | **4 salah / 4** | ☠ bagi sistem; staf keuangan menghitung benar dengan tangan |
| 4. baris PO terbuka | gagal | gagal | gagal | gagal | ⛔ (500 tanpa penjelasan); staf pembelian menghitung dengan tangan |
| 5. selisih pesan–terima | gagal | gagal | gagal | gagal | sama |
| pasangan jam (3 bacaan) | | | ✓ 3/3 | | ✓ |

Angka akhir bulan: sistem menyatakan utang **Rp 201.900.000** (Sumber Terigu
95,4 jt · Manis Jaya 70,9 jt · Dairy Prima 29,5 jt · Kakao 6,1 jt); kebenaran
**Rp 58.400.000** (25,4 · 17,4 · 13,5 · 2,1). Staf keuangan menulis angka
kebenaran itu persis di laporannya, dihitung sendiri dari dokumen, dengan
peringatan "harus diperbaiki sebelum laporan akhir bulan dipakai". Staf
pembelian menghitung baris terbuka akhir bulan dengan tangan dari
`PurchaseOrderLine` dan `DeliveryCheckLine`: susu PO-2608-03 sisa 4 sak dan
gula PO-2608-06 sisa 8 karung — **sama dengan kebenaran**.

**Kesimpulan Tahap E.** Dari lima pertanyaan, sistem sendiri menjawab benar
dua (stok, nilai stok), dan yang pertama pun hanya karena satu staf mengakali
cacat konversi berlawanan dengan panduan. Satu pertanyaan salah tanpa suara
sistem (utang); dua tidak pernah terjawab (tabel gagal). Setiap angka yang
benar di akhir bulan — termasuk yang diambil alih dengan hitung tangan —
benar karena manusia teliti, bukan karena mekanisme. Bagian yang bekerja
tanpa bantuan: kernel dua jam (pasangan jam tepat), koreksi lewat `revokes`,
penolakan layar dan pintu (tidak satu pun terpicu, karena staf selalu memilih
dari daftar), dan biaya standar yang berubah di tengah bulan.

**Akar dari semua kegagalan angka adalah U10** (rujukan dicocokkan dengan
teks identifier; `coalesce(factor, 1)` menelan ketidakcocokan). Bukan T4, T5,
T6, atau T8 seperti yang diprediksi §3 — jebakan-jebakan itu dihindari
implementer atau ditangani staf. Ini temuan paling penting eksperimen
sejauh ini, dan tidak ada di tabel prediksi.

**Pertanyaan staf ke implementer yang tidak pernah dijawab** (dikumpulkan
untuk evaluasi; masing-masing menunjuk celah formulir atau aplikasi):

| dari | pertanyaan | menunjuk ke |
|---|---|---|
| gudang | kolom "Derived" (`product_qty`, …) tidak pernah terisi; `StockOnHand` menjumlah angka mentah — tetap catat dalam kg? | U3, U10 |
| gudang | `StockOnHand` juga menampilkan baris Vendors/Customers/Opening yang negatif | U7 (tidak bisa menyaring baris) |
| gudang | tidak ada tempat nomor SJ, nama mitra, atau tautan retur ke pemasok/PO di StockMove | T7 (dua catatan satu truk tak tersambung) |
| gudang | koreksi salah ketik: ubah catatan asli atau penyesuaian stok? kiriman terlambat: tanggal tiba atau tanggal tulis? | dua jam; panduan tidak membahas |
| pembelian | `OrderLineStatus` gagal sepanjang bulan | U10 |
| pembelian | format kode pemasok, `supplier_rank`, status `closed`, gudang tujuan, janji kirim | medan yang tidak ada / tidak dijelaskan |
| pembelian | "5 statements" tapi hanya 4 id | pernyataan `uniti:uri` tidak ditampilkan |
| keuangan | `SupplierBalance` menjumlah semua dokumen tanpa melihat jenisnya | U10 |
| keuangan | sisa per faktur (pembayaran sebagian) tidak terlihat di mana pun | aplikasi (T9: relasi dokumen) |
| keuangan | apakah "CV. Kakao Lestari Bogor" = pemasok CV Kakao Lestari? pelanggan dan pemasok bercampur di daftar pilihan | T8 |
| keuangan | harga jual, jatuh tempo, nomor dokumen internal tidak punya tempat | aplikasi |

**Angka Tahap E:** 238 panggilan staf (gudang 91, pembelian 67, keuangan
80), 154 submit, 0 penolakan formulir atau pintu, 7 kali 500 dari
`OrderLineStatus`, 9 submit koreksi dengan `--revoke` (17 pernyataan ditarik).
Log akhir: 166 intent, 1.413 pernyataan.

### Tahap F: tukar `@alpha/stock` → `@beta/stock`

**Permintaan ke implementer** (subagent yang sama, dilanjutkan): tim gudang
pindah ke `@beta/stock@v1` mulai September; aplikasi tidak boleh mem-pin
keduanya; lima pertanyaan tetap harus terjawab untuk September **dan** untuk
tanggal mana pun di Agustus; cakupannya hanya penukaran stok, cacat lain
dilaporkan, tidak diperbaiki. Implementer diminta membaca `app/fit` (v5
lawan versi baru), `app/check`, `app/health`, dan `table` dengan `valid_at`
Agustus. Tetap tanpa `submit`.

**Hasil: `@ptmaju/app@v6`**, 103 panggilan, satu seal. Yang diubah (semua
dipaksa oleh penukaran): `Ingredient is_a Item` (bukan `Product`); lima medan
rujukan diarahkan ke `Item`/`UOM` beta; `StockOnHand` dibangun ulang per item
per gudang atas `StockEntryDetail` (bukan `StockLedgerEntry`: "tidak ada yang
menulis ledger otomatis, staf harus mengetik setiap pergerakan dua kali",
jadi `Bin` milik beta tetap kosong); `OrderLineStatus` menghitung terima dalam
satuan baris PO. Pembelian dan keuangan tidak disentuh.

**Yang terjadi di jalan (diperiksa ke transkrip dan log API):**

- **U11 ☠→⛔-tanpa-penjelasan — `app/fit` crash tepat di pasangan yang
  menjadi alasannya ada.** `fit v5 against v6` dan `v6 against v5`: 500,
  tiga kali. Log API: `ValueError: No such class: "Product"` (dan `"Item"`
  untuk arah sebaliknya) di `roles.fit → _rules → compile.tables →
  class_induced_slots`. Laporan membangun aturan versi lama di atas pin versi
  baru (`_map_with_the_pins_of`); kelas aplikasi yang **mewarisi** kelas modul
  yang ditukar (`Ingredient is_a Product`) membuat LinkML melempar
  `ValueError`, bukan `Refusal`. Pasangan lain (v4→v5, v2→v3, v6→v6) jalan.
  Jadi laporan kecocokan hanya bekerja untuk penukaran yang tidak perlu
  laporan.
- **U12 — `unpin` merusak draft alih-alih ditolak.** Langkah pertama
  (`revise`) ditolak `draft_open` dengan jelas (draft v5 masih terbuka, 522
  langkah). Lalu `unpin @alpha/stock@v1` pada draft itu menghasilkan 500
  (`No such class: "Product"` di `studio/read.state → role_refusals`), dan
  setiap `step`/`draft` sesudahnya 500 sampai implementer `discard`.
  Penolakan yang seharusnya — "`Ingredient` masih mewarisi `Product` dari
  modul yang mau dilepas" — tidak ada. Implementer menemukan urutan yang aman
  sendiri: pin modul baru dulu, pindahkan semua ketergantungan, baru `unpin`.
- **U10 dalam satu pengamatan penting: di stok, v6 tidak lagi kena.**
  `UOMConversion` beta dikunci dengan dua **rujukan** (`item`, `uom`), jadi
  `convert.on: {item: item, uom: uom}` mencocokkan URI dengan URI dan
  berhasil. Di v5, rasio ada **pada entity `Uom` itu sendiri** (bentuk Odoo),
  dan cara yang benar — mencocokkan dengan identitas entity — tidak bisa
  ditulis, sehingga implementer jatuh ke `uom_name` (teks). Jadi U10 di stok
  bukan salah implementer; bentuk Odoo tidak bisa dikonversi dengan benar
  lewat `convert`. `coalesce(factor, 1)` tetap ada: implementer menulis di
  panduan gudang "**baris konversi yang hilang membuat 1 sak dihitung 1 kg
  tanpa peringatan**" — sebuah peringatan yang harus ditulis manusia di
  panduan karena sistem tidak mengatakannya.

**Agustus lewat v6 (dibaca pelaksana, `valid_at` 31 Agu):**

| pertanyaan | v5 | v6 | label |
|---|---|---|---|
| 1. stok | 12/12 benar | **0 baris** | 👁 — `app/health` v6 `orphaned_fact`: "stk:quantity holds 50 statements no module here declares; @alpha/stock does…", 20 predikat |
| 2. nilai stok | 152.835.000 | 0 baris | 👁 sama |
| 3. utang | salah (U10) | salah, identik | ☠ tetap |
| 4. baris PO terbuka | 500 | **terjawab benar dalam satuan beli**: susu PO-2608-03-2 sisa 4 sak, gula PO-2608-06-1 sisa 8 karung | ✓ (kebetulan dari penukaran) |
| 5. selisih pesan–terima | 500 | benar dalam satuan beli; **satuan stok salah tanpa suara** (`ols_ordered_stock_qty` = 100 untuk 100 sak, `ols_received_stock_qty` = 0) | ☠ |

- **Fakta tidak hilang, dan itu terlihat.** Ini klaim "fakta di bawah skema"
  yang diuji: 41 pergerakan Agustus tetap di log, tidak dihapus dan tidak
  dimigrasi; `app/health` menyebutkan semuanya satu per satu dengan modul
  pemiliknya. Tapi **tidak ada jalan membacanya lewat v6**: implementer
  menulis dua pilihan untuk manusia — masukkan ulang 41 baris Agustus sebagai
  Stock Entry bertanggal asli, atau satu saldo pembuka 1 September (Agustus
  hanya terbaca lewat v5). "Jangan dua-duanya, atau stok terhitung dua kali."
  Tidak ada modul penyelarasan atau pernyataan "predikat alpha X = predikat
  beta Y" yang bisa dipakai; itu jalur T8/§10.6 yang belum ada.
- **Baris PO masih terbelah dua** (9 baris per entity + 9 baris per teks
  `PO-…`): kunci `pol_id` tetap teks di sisi pesanan. Kolom satuan stok
  sisi-teks berisi jumlah sak mentah: tidak ada `UOMConversion` untuk satuan
  Agustus (`maju:sack-25kg` adalah entity `Uom` alpha), jadi faktor = 1.
- **Rujukan ke entity kelas lama tetap tampil tanpa keluhan.** `pol_uom` di v6
  ber-range `UOM` beta, tetapi nilainya masih `maju:sack-25kg` (entity kelas
  `Uom` alpha); tabel `UOM` v6 kosong. Tidak ada diagnosis "rujukan ke entity
  di luar range".

**U1 dan U2 terbukti di data, dua nasib:**

- **Terbawa kebetulan (U2 + U1):** dua gudang yang dicatat lewat alpha muncul
  sebagai `Warehouse` beta di v6, lengkap dengan nama "Gudang Utama" /
  "Gudang Cabang": kelasnya disimpan sebagai nama telanjang `Warehouse`, dan
  `stk:warehouse_name` adalah satu predikat untuk dua modul. Hasilnya tampak
  "berhasil", padahal tidak ada yang menyatakannya.
- **Laporan kesehatan salah menghitung:** `app/health` v6 menyatakan
  `stk:uom` milik `@beta/stock`, `held: 6`, dibaca `StockOnHand.qty_in/out`.
  Enam pernyataan itu adalah satuan stok **Product alpha** pada entity bahan,
  bukan baris stok beta; tidak masuk `orphaned_fact`. Hal sama untuk
  `stk:warehouse_name` (`held: 2`). Laporan yang dirancang untuk menjawab
  "apa yang terjadi pada fakta" menghitung fakta modul lain sebagai milik
  modul baru. Hari ini tidak ada angka yang salah karenanya (bahan bukan
  baris stok), tapi aturan yang membaca `stk:uom` per entity akan salah diam.

**Laporan lain di tahap ini (dibaca pelaksana):**

- **`app/health` v5 dengan data sebulan** tidak mendeteksi satu pun cacat
  angka: 36 `dead_term` (termasuk semua tanggal dokumen, karena tidak ada
  aturan yang membaca `moment`), 3 `empty_class`, `unfilled_role: Flow`,
  `empty_column` 0. Tidak ada diagnosis untuk U10 (konversi yang tak pernah
  cocok), T7 (truk KL-221: 500 kg gudang, 50 kg pembelian), atau kolom
  konstan (`SupplierBalance` berisi angka sama di lima kolom). Semua itu
  terdeteksi manusia, bukan data.
- **G2 — koreksi ✓, jejak sel sebagian.** `app/cell` `StockOnHand.qty_in`
  cokelat / lokasi stok utama, `valid_at` 14 Agu: dengan `as_of` akhir W2
  sel berdiri di atas pernyataan `stk:quantity = 500`
  (`71fcb7a8…`, dicatat 08:27:41); dengan `as_of` sekarang, di atas
  `= 50` (`b1e6bc44…`, 08:33:14), dari submit staf gudang dengan
  `--revoke quantity=71fcb7a8…` dan catatan alasannya. Dua kekurangan
  keterlihatan: sel "sekarang" tidak menyebut bahwa pernyataannya
  **menggantikan** yang ditarik (harus dicari di intent), dan `reads` kosong —
  pernyataan satuan dan faktor konversi yang ikut menentukan angka tidak
  ditampilkan, jadi U10 tidak terlihat dari jejak sel.

**Pelanggaran aturan kecil implementer:** tiga kali memotong keluaran klien
(`| head -5`, `| tail -c` ×2) dan membuka keluaran `app/health` yang disimpan
harness dengan Read. Isinya hanya keluaran klien.

### Tahap F: revisi arti (T10)

**Permintaan ke penulis `stok-b`** (subagent yang sama, dilanjutkan), dikutip
dari pesan pelaksana sebagai permintaan staf gudang pemakai modulnya: "Kami
ingin kuantitas di baris stock entry selalu dalam satuan stok item (100 kg,
40 pack) … Satuan di kertas boleh tetap ada di baris sebagai referensi, tapi
kuantitasnya harus kuantitas satuan stok." Tidak disebut bagaimana
memodelkannya, dan tidak disebut `slot_uri`.

**Hasil: `@beta/stock@v2`** (19 panggilan, satu penolakan `draft_open`).
Penulisnya **sengaja menghindari T10 untuk arti baru**: ia membuat medan baru
`stock_qty` (`stk:stock_qty`, wajib) dan menulis alasannya persis seperti
prinsip Uniti: "kalau `qty` sekarang berarti kg, fakta lama '4 sak' akan
terbaca 4 kg — angka salah yang tampak benar". Tapi **arti medan lama tetap
bergeser dengan `slot_uri` yang sama**: `qty` (`stk:qty`) berubah dari "the
quantity" (wajib) menjadi "Qty on paper — reference only … never used to move
stock" (opsional); `uom` dan `conversion_factor` di baris juga jadi
"reference only". Judul "Qty in stock UOM" pindah dari `transfer_qty` ke
`stock_qty`.

**Implementer diminta menaikkan pin dalam dua langkah** (seperti orang
biasanya: pindahkan pin dulu, baca laporan, baru baca deskripsi modul).

| | apa yang dikatakan sistem tentang v6 → v7 (hanya pin pindah) |
|---|---|
| `app/health` v6 | `lagging_pin`: "@beta/stock is pinned at v1; the store has sealed up to v2" — mengajak naik, tanpa isi perubahannya |
| `app/fit` v6 → v7 (diperiksa pelaksana) | pin v1 → v2; semua peran `unchanged`; `StockOnHand.qty_in` `reads_before` = `reads_after` = `[stk:item, stk:qty, stk:target_warehouse]`, `"status": "unchanged"`; `dark: []`, `orphaned: []`, **`"clean": true`** |
| `app/check` v7 | semua `holds: true`, `clean: true` |
| `app/health` v7 | tidak menyebut apa pun soal penukaran |
| formulir `StockEntryDetail` v7 | **satu-satunya tempat**: deskripsi `qty` "Never used to move stock", `stock_qty` "decimal required" |

**T10 ☠.** Di v7 `StockOnHand` tetap menjumlahkan `qty` × faktor, sedangkan
formulir yang sama menyuruh staf mengisi `stock_qty` dan menyebut `qty`
opsional dan tidak dipakai. Akibat yang dijabarkan implementer, konkret:
penerimaan 100 sak terigu diisi `stock_qty = 2500` saja → stok gudang utama
kurang 2.500 kg (Rp 23.500.000 pada 9.400/kg); stok opname (tidak punya
kuantitas kertas) tidak pernah terhitung; memasukkan ulang saldo pembuka
Agustus dengan `stock_qty` saja membuat Agustus kosong lagi. Tidak ada
laporan yang bersuara; `fit` bahkan menyatakan bersih. Yang ada hanya prosa
deskripsi medan.

**Implementer lalu memperbaikinya di v8** (`qty_in`/`qty_out` menjumlahkan
`stock_qty` tanpa konversi; sekaligus menghilangkan risiko "faktor 1" di
stok). Yang tidak bisa diungkapkan: "hitung baris lama dengan `qty` × faktor
bila `stock_qty` kosong" — `where` hanya menyaring kelas (U7), ekspresi tidak
punya `coalesce`. Tidak dibutuhkan hari ini karena belum ada baris beta di
log. Saran penulis modul ("pakai `stock_qty`, jatuh ke `transfer_qty` untuk
baris lama") **tidak mungkin di platform ini**: `transfer_qty` adalah
`expression` di kelas entity, jadi tidak pernah dihitung (U3).

**Dua keterbatasan `app/fit` yang terlihat di sini:**

- **Ia membaca aturan versi lama di atas pin versi baru** ("aturan saya,
  modul mereka", `roles.py:_map_with_the_pins_of`). Jadi `fit v6 → v8` masih
  menampilkan `reads_after: stk:qty` walaupun v8 membaca `stk:stock_qty`
  (dicek implementer lewat `catalogue q=stock_qty`: "read by … @ptmaju/app v8
  StockOnHand.qty_in"). Laporan menjawab "apakah aturan lama masih
  ter-resolve", bukan "apakah artinya masih sama", dan tidak menunjukkan
  perbaikannya.
- **U14 — `reads` tidak memuat medan konversi.** `qty_in` membaca `stk:uom` dan
  `stk:conversion_factor` lewat `convert`, tapi `reads` hanya berisi `item`,
  `qty`, gudang. Penukaran yang hanya merusak konversi akan tampil
  `unchanged` (dicatat implementer pada v4 → v5, dicek pelaksana pada
  v6 → v7).

**Dua anggapan penulis modul yang tidak berlaku di platform:**

- **U13 — `required` tidak ditegakkan.** Penulis berharap "pemeriksaan
  formulir akan menandai atau menolak baris v1 sampai `stock_qty` diisi".
  `required` hanya ditampilkan (`generate.py:253`, klien, layar); `submit`
  tidak menolaknya, dan tidak ada pemeriksaan atas baris yang sudah ada. Dan
  `required` menempel di slot, bukan di pasangan kelas–slot (seperti U6):
  melepas `required` pada `uom`/`conversion_factor` untuk baris stock entry
  juga melepasnya di `UOMConversion`, tempat keduanya justru wajib. Penulis
  menyadarinya dan menulisnya di deskripsi.
- `transfer_qty` "tetap menurunkan kuantitas satuan stok baris v1" — tidak,
  karena U3.

**Angka Tahap F:** implementer 128 panggilan (v6: 103, v7–v8: 25), penulis
`stok-b` 19, pelaksana 14. Tiga versi aplikasi (v6, v7, v8) dan satu versi
modul (`@beta/stock@v2`). 8 kali 500 (`fit` ×4, `studio step/draft` ×4 akibat
U12, `OrderLineStatus` v5 ×1 dihitung di sini juga), penolakan terstruktur:
`draft_open` ×3, `no_such_version` ×1, `not_a_pin` ×1. Log tidak bertambah
(Tahap F tidak menulis data).

### Tabel hasil

Label §8. Kolom perbaikan, tempat, dan ongkos core diisi di Tahap G.

| jebakan | jenis | prediksi | hasil | bukti | perbaikan minimal | tempat | ongkos core |
|---|---|---|---|---|---|---|---|
| dua modul menamai sama | T1 | diam | **☠** antar modul (slot `category_name` alpha ↔ gamma jadi satu predikat `prt:`, seal dan check diam; 👁 hanya di `terms` `app/health`) · ⛔ di dalam satu draft (`name_taken`) · bentrok kelas `Warehouse` tidak teruji (implementer menolak mem-pin `@delta/purchase`) | Tahap C, D; v5 `app/health` terms | | | |
| versi core berbeda | T2 | ditolak | **tidak muncul**: semua penulis memakai core v2 | katalog | | | |
| pengikat ganda | T3 | ditolak | **tidak muncul** | transkrip Tahap B–C | | | |
| tanda / arah | T4 | diam | **tidak diam, tapi peran kalah**: penulis Odoo menolak mengisi `Flow` karena `amount` bertanda; aplikasi menghitung arah gaya Odoo dengan **menyebut kelas** (✓). Prosa core bertanda memilih pemenang (§2 butir 4) | Tahap B, D | | | |
| satuan | T5 | diam | **☠**: `convert` gagal cocok → `coalesce(factor, 1)`; stok benar hanya karena staf gudang mengakali (v5), kolom satuan stok `OrderLineStatus` salah diam (v6); di beta, konversi rujukan↔rujukan bekerja | Tahap E W1, Tahap F | | | |
| keluasan | T6 | terlihat (`covers`) | **tidak teruji**: pengisi `Flow` campur (kg + rupiah) dan `Resource` ikut `Account`, tapi aplikasi tidak memakai peran sama sekali, jadi `covers` tidak pernah diuji terhadap data | Tahap C, D | | | |
| pencatatan ganda | T7 | diam | **☠ untuk isi yang berbeda**: truk KL-221 500 kg (gudang) vs 50 kg (pembelian), tidak ada yang membandingkan; **angka tidak dobel** karena implementer memilih satu sumber per pertanyaan | Tahap E W2 | | | |
| identitas | T8 | tidak ada jalur | **✗ terbukti**: `Supplier` (`@delta`) ≠ `Partner` (`@gamma`) tanpa jalan menyatukan; dihindari dengan tidak mem-pin `@delta`; Kakao Lestari ditangani staf ✓. Penukaran stok menunjukkan kasus yang sama untuk predikat: tidak ada cara menyatakan "`stk:quantity` alpha = `stk:qty` beta", data Agustus harus dimasukkan ulang | Tahap C, E, F | | | |
| struktur | T9 | mungkin tak terungkapkan | **✗ sebagian**: header+baris ✓ dengan kelas aplikasi; aggregate di atas tabel hitungan ⛔ `no_type_slot`; saring nilai ✗ (U7); sisa per faktur ✗; kunci baris PO terbelah (U10) | Tahap D, E | | | |
| pergeseran arti | T10 | diam | **☠**: penulis menghindari untuk arti baru (predikat baru), tapi `stk:qty` berganti peran dengan `slot_uri` sama; `fit` `clean: true`, `check` dan `health` diam; hanya prosa formulir | Tahap F | | | |
| terlambat dicatat | dua jam | – | **✓**: tiga bacaan pasangan jam tepat | Tahap E W3 | | | |
| salah ketik lalu koreksi | G2 | – | **✓**: `--revoke` lewat formulir, sel `as_of` akhir W2 = 500, sekarang = 50; jejak sel tidak menyebut penggantian | Tahap E W3, Tahap F | | | |

### Temuan yang tidak diprediksi

| # | temuan | label | pertama | ditangkap oleh |
|---|---|---|---|---|
| U1 | dua modul berbagi predikat lewat CURIE mentah (`stk:` → dua namespace, satu entity predikat); `app/health` menghitung fakta alpha sebagai milik beta | ☠ | B | pelaksana |
| U2 | kelas disimpan sebagai nama telanjang; gudang alpha "terbawa" jadi `Warehouse` beta | ☠ (kebetulan benar) | B, F | pelaksana, implementer |
| U3 | `parameter`/`expression` di kelas entity tidak pernah dihitung, muncul sebagai medan isian; termasuk pengikat peran | ☠ | B, C | pelaksana, implementer, staf gudang |
| U4 | sintaks ekspresi tak diajarkan, tak diperiksa saat seal | ⛔ setelah seal | B, C | compiler |
| U5 | aggregate mengubah kelas jadi tabel ber-group | 👁 | B | penulis |
| U6 | satu aturan per slot, ditimpa tanpa penolakan | 👁 | C | pelaksana |
| U7 | `where` hanya menyaring kelas, bukan nilai | ✗ | C, D, F | tiga penulis + implementer |
| U8 | `required` tidak tampak di draft | 👁 kecil | C | penulis |
| U9 | `app/check` "holds" sementara compiler menolak | ☠ di laporan | D | implementer |
| U10 | rujukan dicocokkan dengan teks identifier; `coalesce(factor, 1)` menelan | **☠ akar semua angka salah** | D (prediksi), E | implementer (prediksi), staf, pelaksana |
| U11 | `app/fit` crash (`ValueError`) bila kelas aplikasi mewarisi kelas modul yang ditukar | ⛔ tanpa penjelasan (500) | F | implementer |
| U12 | `unpin` modul yang masih diwarisi merusak draft, tidak ditolak | ⛔ tanpa penjelasan (500) | F | implementer |
| U13 | `required` tidak ditegakkan di pintu mana pun, dan menempel per slot | ☠ potensial | F | pelaksana |
| U14 | `reads` di `app/fit` tidak memuat medan konversi | 👁 berkurang | F | implementer, pelaksana |
| U15 | pembagian dengan 0 di SQL hasil compiler → 500 mentah, bukan penolakan | ⛔ tanpa penjelasan | E | staf pembelian, pelaksana |
| U16 | `app/health` dengan data sebulan tidak mendiagnosis satu pun cacat angka (kolom konstan, konversi tak cocok, dua catatan satu truk berbeda); jejak `app/cell` tidak memuat bacaan konversi dan tidak menyebut pernyataan yang digantikan | keterlihatan | F | pelaksana |

**Pola dari semua baris di atas.** Jebakan yang diprediksi (T1–T10) sebagian
besar **dihindari manusia** — penulis modul menolak mengisi peran (T4, T7),
implementer menolak mem-pin modul (T1, T8), penulis v2 memilih predikat baru
(T10) — dan yang tetap lolos, lolos tanpa suara (T1, T5, T7, T10). Kerusakan
angka yang sungguh terjadi datang dari temuan yang tidak diprediksi (U3, U10)
di lapisan eksekutor, bukan di core. Laporan (`check`, `fit`, `health`) tidak
menangkap satu pun ☠ sebelum manusia menangkapnya; dua di antaranya gagal
keras tepat saat dibutuhkan (U11, U15).

### Keputusan di gerbang
