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

### Tabel hasil

*(bentuk §8)*

### Temuan yang tidak diprediksi

### Keputusan di gerbang
