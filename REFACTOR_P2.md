# Refactoring P2 — dokumen kerja sementara

> Dokumen ini hidup selama proses refactoring saja, lalu dihapus. Isinya **bukan**
> konteks permanen dan bukan catatan keputusan jangka panjang. Hanya arah, urutan
> kerja, dan hal yang masih harus diputuskan.
>
> Dokumen tetangganya, **`DESIGN_NOTES.md`**, berumur lebih panjang: isinya bentuk
> sistemnya — core, peran, Studio — dan juga bukan aturan, hanya referensi supaya
> diskusi yang sama tidak diulang. Yang di sini adalah *urutan kerja*; yang di sana
> adalah *kenapa*.

---

## 1. Posisi P1 dan P2

**P1 sudah membuktikan konsepnya bekerja**, secara hampir end-to-end. Tujuannya
demonstrasi dan pemahaman, jadi banyak jalan pintas:

- graph ditulis tangan dan dibentuk agar cocok dengan compiler dan generator
- data simulasi, dashboard demonstrasi, UI yang dirakit untuk presentasi

**P2 menaikkan standar komponennya.** P2 bukan produksi. Tujuannya menambah
mekanisme dan kompleksitas untuk melihat sejauh mana sistem ini mampu.

Tujuan P2:

1. **Studio sebagai pintu masuk pembuatan graph.** Ini menggantikan stage 1 P1
   (graph tulisan tangan).
2. **Graph yang modular.** Proyek ini akan open source: orang memuat graph untuk
   kasus penggunaan mereka sendiri, dan graph menjadi dasar sistem yang modular,
   bisa tumbuh, dan kolaboratif.
3. **Menemukan standar universal dan graph inti sebagai bibit.** Ini ditemukan
   lewat bukti, bukan ditetapkan di awal.
4. **Generator dan compiler yang tumbuh** untuk menampung kompleksitas, tipe data,
   dan skema apa pun. Arahnya dibalik dari P1: di P2 compiler yang mengejar graph,
   bukan graph yang disesuaikan untuk compiler.

---

## 2. Yang dipertahankan dari P1: mekanismenya saja

Semua yang dipertahankan adalah **mekanisme**. UI, data simulasi, map bisnis, dan
script demo tidak ikut.

| Mekanisme | Isinya | Status di P2 |
|---|---|---|
| Kernel (`001_schema.sql`, `perform`, `resolve`) | 3 tabel append-only, dua jam, `revokes`, satu intent per aksi | Dipertahankan apa adanya |
| Ontology (`resolve_version`) | versi map yang berlaku pada (valid_at, as_of) | Dipertahankan, diperluas per modul |
| Seal (`seal`, `register`) | satu-satunya gerbang dari draft ke versi; transcript dan `valid_from` wajib; registry `uniti:uri` | Dipertahankan; menjadi **satu-satunya validator** |
| Generator | kolom dan form dari map; `submit` sebagai pintu tulis | Dipertahankan, lalu diperluas |
| Compiler | aggregate, parameter, expression, where, convert → SQL | Dipertahankan, lalu diperluas |
| Provenance | siapa menyatakan apa, kapan, apa yang ditarik | Dipertahankan |

Prinsip mekanisme yang ikut terbawa. Semuanya sudah terbukti di P1:

- **Tiga lapisan:** graph (makna dan aturan), kernel (apa yang dinyatakan), dan
  operational DB (turunan; boleh dibuang dan dibangun ulang).
- **Satu write gate:** setiap pintu menghasilkan satu `intent` dan N `assertion`.
- **Penilaian hanya di tepi.** Agent dan manusia boleh menilai; `seal` adalah batasnya.
- **Identitas predikat adalah `slot_uri`.**
- **Versi yang sudah di-seal tidak pernah diedit.** Koreksi adalah versi baru.
- **Tidak ada konstruksi di map sebelum ada yang mengeksekusinya.**

---

## 3. Yang ditinggalkan

**UI P1** dirombak total: `serve.py`, `render.py`, `diagram.py`, dan presentasi.

**Data dan demo P1:** `business/*`, `scripts/seed_demo.py`, `check_profile.py`,
`render_map.py`, `owl_domains.py`, dan dashboard.

**Seluruh lapisan authoring P2 yang gagal:**
`components/studio/*`, `web/studio_handler.py`, `linter/*`,
`scripts/bootstrap_p2_kernel.py`, dan `tests/p2/*`.

**Disimpan sebagai referensi, tidak dijalankan dan tidak dites** (dihapus dan diganti di irisan 4.2): `components/agent/*`
(MCP baca P1 dan server Studio P2), sebagai inspirasi untuk irisan 4.
`studio_server.py` di dalamnya mengimpor modul yang sudah dihapus.

**Pelajaran yang diambil dari kegagalan itu:**

| Kegagalan | Pelajaran |
|---|---|
| `seal_package` menulis ulang seal (seal di tempat, tanpa transcript, `valid_from` otomatis) | Perluas gerbang yang ada, jangan buat gerbang kedua |
| Linter paralel: PASS, tapi compiler gagal | Satu hakim saja, yaitu validasi di `seal` |
| Import meresolusi file hidup, indeks paket beku, substring match | Import harus menunjuk versi sealed yang dipin |
| Agent menulis YAML langsung; riwayat membuang tool call; tidak bisa hapus; tidak streaming | Agent bekerja pada draft lewat operasi deterministik, dan setiap langkahnya terlihat |
| Katalog URI ditulis tangan dan menebak diam-diam | Katalog adalah registry kernel (`uniti:uri`), bukan daftar di kode |
| Invariant, lifecycle, dan archetype tanpa eksekutor | Sebuah konstruksi masuk map bersamaan dengan eksekutornya |
| Satu server dengan flag mode P1/P2 | Satu aplikasi, satu model |

---

## 4. Cara kerja selama refactoring

- **Irisan vertikal.** Setiap irisan menghasilkan mekanisme **dan** tampilan yang
  bisa dilihat dan dipakai. UI adalah alat untuk memahami apa yang bekerja dan
  bagaimana ia bekerja di belakang layar, sehingga arahan dan keputusan bisa akurat.
- **Test lebih dulu untuk mekanismenya,** tapi irisan belum selesai sebelum ada
  yang bisa dilihat di layar.
- **Tidak ada file konteks yang mengikat** (`CLAUDE.md`, `DECISIONS.md`, log).
  Dokumen kerja ini satu-satunya, dan dihapus di akhir. Sejak 18 September 2026
  ada satu pengecualian yang disengaja: `DESIGN_NOTES.md`, catatan referensi yang
  **tidak mengikat apa pun** — ia ada supaya diskusi panjang tidak perlu diulang,
  bukan supaya ada yang harus dipatuhi. Kalau kode membuktikan sebaliknya, kode
  yang benar. Sejak 24 September 2026 ada satu dokumen kerja lagi,
  `COMPOSITION_EXPERIMENT.md`: rencana irisan 2.8, dihapus bersama dokumen ini.
- **Kode domain-agnostic.** Tidak ada istilah dari data uji di kode. Semua isi
  domain hidup di `tests/modules/fixtures/` — modul `@demo/*` dan `demo_data.yaml` —
  dan setiap modul di sana menyatakan `purpose: demonstration`, yang terbawa sampai
  ke `reason_code` di kernel. Jadi data uji menandai dirinya sendiri, di graph
  maupun di log, tanpa ada satu kata domain pun di komponen.
- **Satu commit per langkah yang utuh.** Irisan ditutup setelah Anda melihatnya.

---

## 5. Branch dan cara kembali

| Penanda | Menunjuk | Isinya |
|---|---|---|
| tag `p1-final` | `5e4f935` | P1 utuh, sebelum pekerjaan P2 |
| tag `p2-attempt-1` | `f32623e` | percobaan P2 pertama (Studio, linter, agent) yang ditinggalkan |
| branch `p2/domain-blind-and-kernel-invariants` | `f32623e` | branch percobaan pertama, dibiarkan apa adanya |
| branch `p2/refactor` | dimulai dari `f32623e` | **tempat refactoring berjalan** |

Nama `p2` saja tidak bisa dipakai karena git tidak mengizinkan branch `p2` di
samping branch `p2/...`.

File yang tidak dipakai lagi **dihapus** di `p2/refactor`, tidak dipindah ke folder
arsip. Salinan lengkapnya tetap ada di tag.

Cara kembali:

```
git switch --detach p2-attempt-1          # lihat atau jalankan keadaan sebelum refactor
git switch --detach p1-final              # lihat atau jalankan P1
git checkout p2-attempt-1 -- <path>       # ambil satu file lama ke branch sekarang
git switch p2/refactor                    # kembali bekerja
```

---

## 6. Urutan irisan

Setiap irisan menjawab dua pertanyaan: *mekanisme apa yang terbukti* dan *apa yang
Anda lihat*.

### Irisan 0: Kerangka baru dan kernel yang terlihat

**0a. Bersih-bersih**

- Hapus UI P1, data dan demo P1, dan lapisan authoring P2 (daftar di bab 3).
- Pindahkan `business/trial/v1.yaml` ke `tests/trial/fixtures/`, karena test probe
  LinkML membacanya.
- Lepaskan seal dan generator dari `components.linter`: heuristik
  `"@" in content` diganti `SchemaView` biasa. Pemuatan modul dibangun dengan
  benar di irisan 1.
- Netralkan istilah domain di test dan fixture fondasi (sekitar 250 kemunculan)
  dan di docstring `generate.py` / `seal.py`. Maknanya dipertahankan, hanya
  namanya yang netral.
- Tulis ulang `Makefile` dan `README.md` seperlunya untuk struktur baru.
- **Yang tetap:** komponen fondasi dan test-nya, `scripts/seed_200.py` +
  `scripts/project.py` (bukti replay kernel), `docker-compose.yml`, dan
  `packages/@uniti/core`.
- **Selesai jika:** semua test fondasi tetap lulus.

**0b. Kerangka aplikasi dan penjelajah kernel**

- **Mekanisme:** API JSON baca atas kernel (intent, entity, assertion, registry
  URI) dengan parameter `valid_at` dan `as_of`.
- **Yang dilihat:** aplikasi web baru dengan penjelajah kernel dan dua jam yang
  bisa digeser.
- **Selesai jika:** Anda bisa menelusuri isi kernel dan melihat efek pergeseran
  `valid_at` dan `as_of`.

### Irisan 1: Modul sebagai paket berversi

- **Mekanisme:**
  - Paket berbentuk direktori versi sealed (`vN.yaml` + `vN.txt`).
  - Import memakai `nama@versi`.
  - Loader meresolusi versi yang dipin.
  - `resolve_version` berlaku per paket.
  - Seal memvalidasi import.
- **Yang dilihat:** penjelajah modul berisi daftar modul, versi, dan graph import
  antar modul; beda (diff) antar versi; dan URI yang didaftarkan tiap versi ke kernel.
- **Selesai jika:** modul B yang mengimpor A@v1 tidak berubah maknanya saat A@v2
  di-seal, dan itu terlihat di layar.

### Irisan 2: Komposisi dan kompilasi

- **Mekanisme:** sebuah *aplikasi* adalah sekumpulan modul yang dipin. Compiler dan
  generator membacanya sebagai satu map, lalu membangun satu operational DB.
  Aplikasi **bukan** jenis baru di store: ia satu versi sealed yang memin modul lain
  dan mendeklarasikan tabel yang ingin dilihat seseorang. `read_map(path, store)`
  meresolusi pin lewat store; tanpa store, map yang memin ditolak karena ia hanya
  utuh di dalam store.
- **Yang dilihat:**
  - graph kelas gabungan, dengan warna per modul dan empat jenis sambungan
    (`is_a`, `reference`, `aggregate`, `parameter`)
  - tabel proyeksi, dengan "bagaimana angka ini dihitung": aturan per kolom,
    modul pemilik slot, dan SQL yang dipancarkan
  - **klik satu sel → pernyataan yang menopangnya**, tiap baris menunjuk ke
    entity dan ke aksi yang menulisnya di penjelajah kernel
  - **form yang menulis ke kernel**, medannya dibaca dari map, pilihan untuk
    medan bertipe kelas dibaca dari operational store, satu submit = satu intent
- **Selesai jika:** proyeksi di satu modul menghitung dari event modul lain lewat
  `slot_uri` bersama, dan angkanya bisa ditelusuri.

### Irisan 2.5: Core sebagai standar

Standar hanya bermakna kalau ada yang menegakkan atau menjalankannya, jadi core
didesain setelah generator dan compiler membaca modul (irisan 2), dan sebelum
Studio (irisan 3) yang harus dipandu olehnya.

> Arah, alasan, dan detail teknisnya ada di **`DESIGN_NOTES.md`** — catatan
> referensi, bukan aturan. Yang di bawah ini hanya ruang lingkup irisannya.

Tiga pertanyaan yang dibuka irisan ini sudah punya jawaban usulan di sana:
kategori core adalah **peran** (kelas abstrak yang menyatakan kewajiban, bukan isi
dunia); peran diisi lewat **`mixins:`**, bukan `is_a` — jadi keputusan P1 "hanya
`is_a`" memang ditinjau ulang, dan mixin terbukti bekerja dengan penelusuran
turunan yang sudah ada; dan **ya, core menyediakan kelas akar** yang membawa
`entity_class`, karena kelas akar adalah tempat kewajiban menempel.

- **Mekanisme:**
  - core v2: `Thing`, `Resource`, `Event`, `Flow`; slot abstrak `amount`,
    `moment`, `affects`. Setiap baris menyebut eksekutornya.
  - resolusi slot abstrak ke slot konkret di `named_slot`
  - slot abstrak dilewati sebagai kolom (kalau tidak, muncul kolom hantu)
  - seal menolak kelas yang mengaku peran tapi tidak memenuhinya
- **Yang dilihat:** panel peran, laporan kecocokan, dan `@rival/*` — modul kedua
  dengan nama-nama berbeda, ditulis tanpa melihat nama modul pertama.
- **Selesai jika:** aplikasi memindahkan pin-nya dari satu modul inventory ke
  modul saingan **tanpa diubah**, dan angkanya identik.

### Irisan 2.6: Penolakan yang bisa ditindaklanjuti

- **Mekanisme:** penolakan membawa struktur (`code`, `where`, `expected`, `got`,
  `repairs`), bukan cuma prosa. Satu sumber, tiga pembaca: kalimat untuk manusia,
  tombol perbaiki untuk Studio, hasil tool untuk agent.
  - satu tipe dasar di `components/refusal/`, empat gerbang yang menyebut
    dirinya: store, seal, generator, compiler
  - kalimatnya **diturunkan** dari strukturnya, bukan ditulis di sampingnya
  - `code` adalah daftar tertutup; konstruktor menolak kode yang tidak terdaftar
  - `repairs[].options` dihitung dari graph: himpunan berhingga jawaban yang sah
  - `check()` menjalankan pembaca yang sama dan **mengumpulkan** penolakannya,
    karena gerbang berhenti di yang pertama dan halaman tidak boleh
- **Yang dilihat:** kartu penolakan yang sama di mana pun sistem menolak, dan
  laporan kecocokan yang menyebut apa yang harus ditambahkan.
- **Selesai jika:** setiap penolakan di layar datang bersama perbaikannya.

### Irisan 2.7: Katalog dan kesehatan graph

- **Mekanisme:** katalog yang dihitung dari isi ter-seal (peran, modul, kelas,
  siapa mengisi apa) — bisa dikueri, bukan dokumen. Enam diagnosa: istilah mati,
  kolom hampa, kelas kosong, peran tak terisi, pin tertinggal, fakta yatim.
  - `catalogue()` + `find()` di `components/modules/catalogue.py`: dari versi
    terbaru tiap modul; "dibaca oleh" dari semua versi ter-seal
  - `health()` di `components/modules/health.py`: enam diagnosa terhadap satu
    aplikasi dan log-nya, dengan kalimat yang diturunkan dari datanya seperti
    penolakan; tanpa log, tiga yang butuh hitungan dilaporkan "tidak dihitung",
    bukan kosong
  - `python -m components.modules find|health`, `/api/catalogue`,
    `/api/app/health`
- **Yang dilihat:** area **Catalogue** di aplikasi web: pencarian dengan saringan
  jenis dan "fills", lalu laporan kesehatan untuk satu versi yang dipilih, plus
  tabel semua predikat, berapa kali dinyatakan, dan siapa pembacanya.
- **Selesai jika:** `inv:movement_happened_on` muncul sebagai istilah mati — 245
  pernyataan, nol pembaca — tanpa ada yang menuliskannya. *(Di P2 angkanya 24:
  245 adalah data P1.)*

**2.6 dan 2.7 mendahului Studio.** Permukaan jelajah Studio adalah katalog, dan
penyuntingnya digerakkan penolakan.

### Irisan 2.8: Uji komposisi — apakah peran bertahan di pemakaian nyata

Disisipkan sesudah 3.1 dan **sebelum 3.2**, pada 24 September 2026. Rencana
lengkapnya di **`COMPOSITION_EXPERIMENT.md`**; yang di bawah ini hanya
kesimpulannya.

- **Kenapa:** peran sederhana di depan, tetapi kemungkinannya meledak di
  belakang. Ini bukan masalah skala, tetapi klaim utama sistem modular, dan P1
  tidak pernah mengujinya karena seluruh graph-nya ditulis satu penulis. Kalau
  klaim ini tidak masuk akal di pemakaian nyata, Studio dan agent dibangun di
  atas sesuatu yang tidak bekerja.
- **Tujuan yang diuji:** bukan "tidak ada konflik" (tidak ada standar yang bisa
  menjanjikannya), melainkan **tidak ada konflik yang diam**: setiap
  ketidakcocokan antar modul ditolak, terlihat, terdeteksi dari data, atau
  diselesaikan dengan penyelarasan eksplisit. Core tetap kecil (≤ ±30
  deklarasi, hanya yang deklaratif dan dibaca eksekutor) dan tidak menjadi
  bahasa pemrograman.
- **Hipotesis:** kombinasi modul tak terbatas, tetapi jenis ketidakcocokannya
  terbatas (sepuluh jenis: nama, versi, pengikat, tanda, satuan, keluasan,
  pencatatan ganda, identitas, struktur, pergeseran arti). Satu sudah terbukti
  diam sebelum eksperimen: dua modul yang menamai kelas sama, yang satu hilang
  tanpa suara.
- **Cara:** skenario distributor fiktif selama satu bulan. Modul bergaya
  Odoo dan ERPNext ditulis oleh subagent yang tidak melihat sistem maupun satu
  sama lain; aplikasi disusun oleh subagent implementer; data dimasukkan oleh
  subagent staf **lewat langkah Studio, seal, dan pintu formulir yang sudah
  ada, satu aksi demi satu aksi**, bukan lewat YAML atau database. Angka
  dibandingkan dengan angka kebenaran setiap akhir minggu.
- **Sebelum mulai:** empat celah pintu ditutup — `aggregate` di Studio belum
  menerima `where`/`convert`, formulir belum bisa mengoreksi, pilihan formulir
  basi sampai compile ulang, dan nilai tidak diperiksa di pintu.
- **Gerbang:** lanjut, sesuaikan, atau pikir ulang, dengan kriteria yang
  disetujui di awal. Posisi mundurnya adalah komposisi eksplisit.
- **Dijalankan di sesi terpisah.**

**Hasil putaran 1 (26 September 2026):** pertanyaan utama **tidak teruji**.
Aplikasi tidak menghitung lewat peran sama sekali, karena rancangan tesnya
membuat peran opsional dan mewajibkan modul stok yang diarahkan untuk tidak
mengisi peran. Temuan sampingan dicatat di `COMPOSITION_EXPERIMENT.md`: modul
bisa bentrok nama tanpa suara, definisi `Flow` hanya menampung jumlah
bertanda, dan penulis modul menghindari peran karena takut hitungan ganda.

**Putaran 2:** lingkup penuh yang sama, peran wajib dipakai penulis modul dan
implementer, semua modul terpasang bersamaan, penukaran modul tanpa mengubah
aturan aplikasi. Rencananya di `COMPOSITION_EXPERIMENT.md` bagian "Putaran 2".

**Hasil putaran 2 (dihentikan 29 September 2026 atas keputusan pemilik):**
berjalan sampai kelima modul selesai ditulis dengan peran wajib, sebelum
aplikasi dan pengisian data. Itu sudah cukup menjawab pertanyaan utamanya:

- Keempat modul yang mengisi `Flow` mengisinya dengan cara berbeda: jumlah
  tak bertanda lawan bertanda, sak lawan kg, barang lawan uang. Setiap penulis
  melaporkan kompromi.
- Penerimaan barang tercatat di modul stok **dan** modul pembelian, keduanya
  mengisi `Flow`. Menjumlah `Flow` menghitung barang dua kali, dan peran tidak
  punya cara menyatakan "kejadian ini juga tercatat di tempat lain".
  Penulisnya sendiri yang menyadarinya.
- Peran tidak bisa menyatakan tempat, arah, satuan, pihak, atau kejadian yang
  sama. Kalau semua itu dimasukkan ke core, core menjadi model data kanonik,
  yaitu hal yang sejak awal ditolak.
- Bentrok nama antar modul terulang: dua penulis memilih prefix yang sama dan
  dua predikat berbeda arti menjadi satu, tanpa suara.

**Kesimpulan irisan 2.8:** peran **tidak** dipakai sebagai penjumlah otomatis
lintas modul. Peran adalah kosakata bersama untuk menemukan dan menyambungkan
modul; aplikasi selalu menyebut jelas apa yang dihitung dari modul mana
(komposisi eksplisit). Kerumitan di belakang dipikul agent dan penjaga sistem,
bukan user. Perbaikan F1–F4 dari putaran 2 tetap di kode (217 test). Arah
sesudahnya: bagian **"Arah sesudah 2.8"** di bawah.

### Irisan 3: Studio manual (tanpa LLM)

Dipecah dua karena keduanya utuh sendiri-sendiri: yang pertama membuat versinya,
yang kedua memperlihatkan akibatnya dan menutupnya.

**3.1 Draft, operasi, dan lubang**

- **Mekanisme:**
  - Draft adalah `draft.yaml` di direktori modulnya sendiri — satu-satunya
    berkas di store yang boleh disunting.
  - Operasi deterministik dari **daftar tertutup** (24 di `OPERATIONS`): tambah,
    ubah, hapus, rename kelas, slot, dan aturan; klaim peran; isi pengikat; pin.
    Tidak ada yang menulis YAML — sebuah langkah dipilih dari himpunan yang
    dienumerasi dan sistem yang menulis berkasnya.
  - Validasi yang sama persis dengan `seal`: `uri_refusals` dan `role_refusals`
    jadi generator, sehingga gerbang berhenti di yang pertama dan halaman
    mengumpulkan semuanya. Tidak ada hakim kedua.
  - Lubang = penolakan yang belum dipicu, ditambah lima *open question* yang
    tidak ditolak siapa pun (kelas kosong, slot lepas, kelas tanpa baris,
    deskripsi yang belum ditulis).
  - `draft.txt` mencatat tiap langkah dan menjadi transkrip seal.
  - `python -m components.studio`, `/api/studio/*`.
- **Yang dilihat:** area **Studio** sebagai **peta**. Sebuah modul adalah graph,
  jadi halamannya graph: node adalah jenis hal, garis adalah isian yang menunjuk
  jenis hal lain, yang dipijak digambar samar di atas yang dibangun. Klik node
  untuk panel yang mengatakan semua tentangnya; tarik titik di bawah node ke
  node lain untuk membuat relasi. Kata-katanya kata orang yang tahu subjeknya,
  bukan kata kompiler — dan di mana kata awam akan jadi tebakan tentang subjek
  seseorang, halaman memakai tulisan modulnya sendiri (deskripsi sebuah pengikat
  yang mengubah `moment` jadi pertanyaan yang bisa dijawab). Seluruh kosakata
  mesin tetap ada, di balik satu tutup **Behind the scenes**.
- **Selesai jika:** modul lengkap — termasuk aplikasi dengan aggregate,
  parameter dan expression — dibangun dari nol tanpa satu baris YAML, dan
  `seal` menerimanya.

  Tiga kolom yang pertama kali dibangun memenuhi syarat itu dan tetap tidak
  bisa dipakai: mekanismenya benar, layarnya memamerkan bagian dalam mesin.
  Peta di atas adalah pembangunan ulangnya, dan syarat "selesai" untuk sebuah
  irisan UI sekarang ditambah satu: **seorang yang tahu bisnisnya, bukan
  kompilernya, bisa membacanya tanpa kamus.**

### Arah sesudah 2.8: Studio dengan agent sebagai penulis utama

Disepakati pemilik 29 September 2026. Rencana irisan 3.2, 4, dan 5 yang lama
(angka langsung dan seal; agent tipis di samping editor; uji integrasi lewat
chat) **diganti** oleh bagian ini. Detail stack dan implementasi agent
dibahas terpisah, belum diputuskan.

**Gambaran pemilik.** Studio adalah tempat graph ditulis, dan di sanalah
kualitas sistem ditentukan: graph yang cacat tidak bisa diselamatkan compiler
dan generator sebagus apa pun. Tokoh utamanya **agent AI** yang memegang
seluruh sumber dan panduan tentang cara graph, modul, dan aturannya bekerja,
dan yang menerjemahkan kebutuhan user menjadi graph yang bisa dijalankan:
membuat modul, mengkurasi graph, membuat aplikasi, mengganti modul. Pendampingnya
**interface** yang membuat user memahami graph dan bisa melakukan semua yang
dilakukan agent secara manual. Studio yang sekarang adalah tampilan mekanisme,
bukan dibangun dari kebutuhan user, dan akan diganti. Compiler dan generator
masih dasar dan **tidak boleh membatasi desain graph**: selama masuk akal dan
bisa dijalankan secara deterministik, keduanya diubah mengikuti graph.

**Bukti dari 2.8.** Para penulis modul, implementer, dan staf di eksperimen
adalah agent yang bekerja lewat langkah Studio. Mereka bisa menulis modul utuh,
membaca penolakan dan memperbaiki diri, dan memahami arti (hitungan ganda,
arah). Mereka gagal di hal yang tidak diajarkan (sintaks rumus), di hal yang
tidak terlihat dari posisinya (dua penulis memilih prefix yang sama), dan
graph yang salah baru ketahuan saat angkanya dibandingkan dengan angka
kebenaran. Satu modul butuh 100–200 langkah, satu aplikasi hampir 700.

**Tiga prinsip yang disepakati:**

1. **Agent mengusulkan, sistem menjamin, user menyetujui.** Kebenaran graph
   tidak bergantung pada kepintaran agent. Semua yang bisa diperiksa mesin
   diperiksa penjaga sebelum seal; agent boleh mencoba bebas karena
   kesalahannya pasti ditangkap, dan ia menjelaskan penolakan ke user.
2. **Contoh bisnis adalah kontrak.** User dan agent menyepakati contoh dalam
   bahasa bisnis ("terima 10 sak terigu, jual 3, stok 7 sak = 175 kg"); agent
   menulisnya sebagai uji; sistem menjalankannya setiap graph berubah, dan
   seal menuntut semuanya lulus. User mempercayai graph lewat contohnya, bukan
   dengan membaca graph.
3. **Tetap LinkML untuk bentuk data, ditambah kosakata aturan Uniti sendiri,
   tanpa stack baru untuk sekarang.** Sebagian besar keterbatasan yang
   dirasakan di 2.8 adalah fitur LinkML yang belum dibuka Studio (daftar nilai
   tertutup/`enum`, `required` per kelas lewat `slot_usage`, `multivalued`).
   Dua keterbatasan LinkML yang nyata: nama kelas dan slot berlaku global
   dalam satu closure (Uniti harus menolak bentrok), dan LinkML bukan bahasa
   hitung (karena itu kosakata aturan Uniti ada di atasnya). Kosakata aturan
   itu dirapikan menjadi bahasa kecil yang tertutup dan terdokumentasi, yang
   dipelajari agent. Stack lain (SHACL, Datalog, SQL langsung) hanya
   dipertimbangkan bila sebuah kebutuhan terbukti tidak bisa ditulis
   deterministik di kosakata sendiri.

**Empat lapis Studio:**

| lapis | isinya |
|---|---|
| penjaga | semua yang bisa diperiksa mesin ditolak sebelum seal |
| pengetahuan agent | satu panduan yang **dihasilkan dari sistem itu sendiri** (operasi, aturan, penolakan, peran, contoh) sehingga tidak basi, ditambah katalog |
| contoh bisnis | kontrak user–graph, dijalankan setiap graph berubah |
| interface | dibangun dari tugas user: percakapan dengan agent, peta graph yang ramah, contoh dan angka yang hidup, usulan perubahan dalam bahasa bisnis sebelum disetujui; semua yang bisa dilakukan agent bisa dilakukan manual, dan sebaliknya |

**Syarat pertumbuhan compiler dan generator:** setiap kemampuan baru bersifat
umum (bukan untuk satu kasus) dan tetap bisa dianalisis tanpa dijalankan,
supaya penjaga dan agent bisa meramal akibatnya.

### Irisan 3.2: Penjaga dasar

- Bentrok nama kelas atau slot di dalam satu closure ditolak saat seal dan di
  draft.
- Predikat disimpan dengan URI penuh, bukan CURIE mentah, sehingga dua modul
  dengan prefix sama tidak lagi berbagi predikat; nama kelas di log
  ber-modul. Keduanya butuh migrasi registry.
- Studio membuka fitur LinkML yang belum ada: daftar nilai tertutup,
  `required` per kelas, slot bernilai banyak.
- Sintaks rumus diajarkan di deskripsi langkah dan di pesan penolakannya.

**Hasil (29 September 2026).** Keempat butir selesai, 226 test lulus, replay
identik dua kali.

- **Bentrok nama.** Dua modul dalam satu closure yang mendeklarasikan kelas,
  slot, atau enum bernama sama ditolak saat seal (`name_clash`) dan muncul
  sebagai lubang di draft. Bila salah satunya draft sendiri, langkah
  jawabannya `rename_class`/`rename_slot`; bila keduanya modul yang di-pin,
  pilihannya pin mana.
- **Identitas lengkap.** Predikat didaftarkan di log dengan URI penuh, dibentuk
  dari prefix modul yang menulisnya sendiri, bukan dari tabel prefix gabungan
  LinkML (yang diam-diam menimpa prefix yang sama dari modul lain). Fakta kelas
  mencatat URI kelas penuh, bukan nama kelas saja. Seal, generator, compiler,
  health, katalog, laporan swap, API, dan pemuat data memakai satu aturan
  (`seal.predicate`, `seal.class_uri`, `seal.written_uri`). Terbukti: dua modul
  dengan prefix `stock:` menjadi dua predikat, dan dua kelas `Warehouse` dari
  dua modul menjadi dua tabel.
- **Migrasi.** Tidak ditulis kode migrasi: semua log yang ada adalah demo atau
  eksperimen. `uniti_dev` dibangun ulang dengan `make dev-db`. Log eksperimen
  `uniti_exp` memakai pendaftaran lama dan tidak lagi terbaca oleh kode baru;
  hasilnya sudah dicatat di `COMPOSITION_EXPERIMENT.md`. Log sungguhan pertama
  akan membutuhkan migrasi yang sebenarnya.
- **Fitur LinkML di Studio.** Langkah baru `add_enum`, `set_enum`,
  `remove_enum` (daftar nilai tertutup), `set_usage` (`required` untuk satu
  kelas saja), dan medan `multivalued` di `set_slot`. Semuanya ditegakkan, tidak
  hanya ditulis: form menawarkan nilai enum dari map dan menolak nilai di luar
  daftar; entity baru ditolak bila medan yang diwajibkan kelasnya kosong
  (`required_missing`), sedangkan koreksi atas entity yang sudah ada tidak
  wajib mengulang semuanya; slot bernilai banyak ditolak compiler
  (`multivalued_not_read`) sampai tabel bisa membaca himpunan (irisan 5).
- **Penjaga tambahan.** Slot yang range-nya menunjuk sesuatu yang tidak
  terlihat (misalnya kelas yang sudah dihapus) ditolak (`range_unknown`),
  dengan langkah `set_slot range` dan pilihannya.
- **Sintaks rumus.** Langkah `expression` menjelaskan kurung kurawal dengan
  contoh. Penolakan `expression_not_arithmetic` menyodorkan rumus yang sudah
  diperbaiki bila nama kolom ditulis tanpa kurung kurawal; penolakan
  `expression_names_unknown` menjelaskan bahwa nilai dari tabel lain dibawa
  masuk dulu lewat `aggregate` atau `parameter`.
- **Perubahan perilaku yang perlu diketahui:** kolom kelas di tabel dan form
  sekarang berisi URI kelas penuh, dan form menolak entity baru tanpa medan
  wajib. Beberapa test lama menulis entity setengah jadi dan disesuaikan.

### Irisan 3.3: Contoh bisnis sebagai kontrak

- Sebuah modul atau aplikasi membawa contoh: data kecil dan angka yang
  diharapkan, ditulis dalam bahasa bisnis.
- Draft menjalankannya setiap berubah; seal menolak bila ada yang gagal.
- Mengambil alih tujuan 3.2 lama: angka hidup dari draft yang belum di-seal.

**Hasil (29 September 2026).** Ketiga butir selesai, 239 test lulus, replay
identik dua kali.

- **Bentuk contoh.** Satu contoh berisi kalimat bisnisnya (`says`), beberapa
  catatan (bahan, pergerakan, dan sebagainya, masing-masing dengan kelasnya,
  faktanya, dan tanggal berlakunya), dan angka yang diharapkan (tabel, baris,
  kolom, angka, dan boleh juga pada tanggal berapa dibaca). Catatan yang
  disebut lagi dengan tanggal lebih baru berarti catatan itu berubah; itu cara
  contoh mengatakan "batas pesan ulang dinaikkan 1 Juli". Sel yang diharapkan
  kosong berbeda dari nol. Berkasnya ada di samping draft
  (`draft.examples.yaml`) dan ikut di-seal di samping versinya
  (`vN.examples.yaml`), tidak pernah diubah lagi.
- **Log sendiri untuk setiap contoh.** Setiap contoh dijalankan di log sementara
  yang hanya ada selama contoh itu berjalan, lalu dibuang. Catatannya masuk lewat
  pintu form yang sama, jadi nilai yang ditolak form juga ditolak di contoh
  dengan kata-kata form. Angkanya dihitung compiler yang sama. Terbukti: log
  pengembangan berisi seluruh data demo, dan contoh tetap hanya melihat satu
  karung terigu miliknya sendiri; tidak ada satu baris pun yang tertinggal di
  log.
- **Seal menuntut semuanya lulus.** Angka yang berbeda menolak seal
  (`example_failed`) sebelum apa pun ditulis. Penolakannya menyebut contoh,
  tabel, baris, kolom, dan tanggalnya, mengutip kalimat bisnisnya, dan
  menawarkan dua jalan: memperbaiki aturan, atau membicarakan ulang contohnya
  dengan orang yang memberinya. Mengubah angka contoh supaya cocok dengan graph
  tidak membuktikan apa-apa.
- **Studio menjalankannya setiap kali draft dibaca.** Tujuh langkah baru:
  `add_example`, `set_example`, `remove_example`, `record`, `unrecord`,
  `expect`, `unexpect`. Contoh yang gagal menjadi lubang yang memblokir. Draft
  tanpa contoh, atau contoh tanpa angka, menjadi pertanyaan terbuka yang tidak
  memblokir. Revisi mulai dari contoh versi sebelumnya, jadi kontraknya ikut ke
  versi berikut. Mengganti nama kelas atau slot ikut mengganti namanya di
  contoh.
- **Angka hidup.** Setiap contoh mengembalikan tabel yang dihasilkannya,
  termasuk ketika semua angkanya benar. Hasil ini tersedia lewat API Studio,
  `python -m components.studio show`, dan
  `python -m components.modules examples @scope/name vN --tables` untuk versi
  yang sudah di-seal. Tampilannya di layar Studio menunggu interface baru di
  irisan 4.
- **Aplikasi demo membawa contoh.** `@demo/stock@v2` membawa dua contoh:
  terigu (36 kg, batas 20 lalu 30, sisa di atas batas 16 lalu 6) dan garam
  (tanpa batas, jadi sisanya kosong, bukan nol). Keduanya lulus saat seal.
- **Keputusan kecil yang saya ambil, silakan dibalik.** Seal tidak mewajibkan
  adanya contoh; ketiadaannya hanya pertanyaan terbuka. Alasannya: modul
  kosakata murni seperti `@uniti/core` tidak punya angka untuk dicontohkan.
  Kalau Anda ingin modul yang punya aturan hitung wajib punya contoh, itu satu
  penjaga tambahan.

### Irisan 4: Agent dan interface Studio baru

Dikerjakan bersama, karena interface dirancang di sekitar agent sejak awal.

- Agent: panduan yang dihasilkan dari sistem, katalog, operasi Studio sebagai
  tool (ditambah operasi yang lebih besar dari langkah satuan), usulan yang
  wajib disetujui user.
- Interface: dibangun ulang dari tugas user (lapis keempat di atas); seal
  dari layar dengan konfirmasi.
- **Selesai jika:** cerita PT Maju dari 2.8 dipakai ulang. Pemilik memberi
  permintaan dalam bahasa bisnis, agent membangun modul dan aplikasinya lewat
  Studio, dan angkanya sama dengan angka kebenaran yang sudah ada
  (`build/exp/story/truth.txt`).

**Rancangan yang disetujui (30 September 2026).**

- **Akurasi ditanggung sistem, bukan kepintaran model.** Kesalahan bentuk
  ditangkap penjaga; kesalahan arti (tanda, satuan, hitungan ganda, waktu)
  hanya bisa ditangkap contoh bisnis. Jadi mutu contoh dan asal angkanya yang
  menentukan:
  - Kontrak dulu, graph kemudian: agent tidak membangun aturan hitung sebelum
    ada contoh yang angkanya disepakati.
  - Angka yang diharapkan dihitung oleh **akuntan**: konteks model terpisah
    yang hanya membaca cerita bisnis dan jawaban user, tidak pernah melihat
    graph, dan menuliskan cara hitungnya dalam bahasa bisnis. User
    mengonfirmasi.
  - Angka yang sudah dikonfirmasi user dikunci sistem. Agent boleh mengubah
    aturan; mengubah angka itu hanya lewat usulan yang disetujui user.
  - Penjaga baru: modul yang punya aturan hitung wajib punya contoh, dan setiap
    kolom hitungan harus diperiksa minimal satu angka contoh. Ini membalik
    keputusan kecil di 3.3; modul kosakata murni tetap tidak wajib.
  - "Selesai" dihitung sistem, dan ringkasan yang disetujui user dirender
    sistem dari keadaan draft, bukan dikarang agent.
- **Satu agent pembangun ditambah akuntan**, bukan tim agent. Alurnya enam
  tahap: pahami → sepakati contoh → cari di katalog → bangun → periksa →
  usulkan. Tiga titik persetujuan user: ringkasan kebutuhan, angka contoh, dan
  seal.
- **Sekitar delapan alat, bukan 31:** lihat keadaan, lihat pilihan langkah,
  jalankan sekelompok langkah (berhenti di penolakan pertama dan mengembalikan
  keadaan baru), cari katalog, baca panduan per topik, tanya user, usulkan
  contoh, usulkan seal. **Agent tidak punya alat seal**; seal hanya terjadi
  lewat tombol user.
- **Ingatan agent adalah sistem:** draft, transkrip, dan contoh. Transkrip
  mencatat siapa yang melakukan setiap langkah (agent atau orang); percakapan
  disimpan di samping draft dan boleh diringkas tanpa kehilangan keadaan.
- **Batas biaya per permintaan:** bila tercapai, agent berhenti dan melapor.
- **Uji agent (eval):** PT Maju sebagai kasus utama ditambah 10–20 tugas
  kecil dari kegagalan 2.8, dinilai kode terhadap angka kebenaran, setiap
  tugas dijalankan tiga kali dan harus benar ketiganya. Diulang setiap panduan,
  instruksi, atau model berubah; langkah, penolakan, token, dan waktu dicatat.

**Stack dan model (30 September 2026).**

- **Pydantic AI** (sudah terpasang) di atas Starlette yang ada, streaming ke
  frontend React yang ada. Tidak ada server, database, atau layanan baru.
  Tidak memakai Claude Agent SDK (membawa alat baca-tulis berkas dan
  terminal), LangGraph (tempat keadaan kedua), atau database vektor (katalog
  dan panduan kecil dan terstruktur; pencarian tepat lebih akurat).
- **Terbuka untuk banyak penyedia dan model self-hosted**, walaupun belum
  dikerjakan sekarang. Aturannya:
  - Model dipilih lewat konfigurasi per peran (pembangun, akuntan). Tidak ada
    kode yang menyebut nama penyedia.
  - Kebenaran tidak bergantung pada fitur khusus satu penyedia. Fitur seperti
    cache atau tingkat berpikir hanya pengaturan opsional di satu tempat.
  - Skema alat sederhana dan datar supaya model kecil dan server yang
    kompatibel OpenAI (Ollama, vLLM, llama.cpp, LM Studio) sanggup memakainya;
    pemeriksaan isian terjadi di sistem, dengan pesan penolakan yang mengajari.
  - Sebuah model dinyatakan didukung untuk satu peran bila lulus eval peran
    itu. Eval adalah tiket masuk, bukan klaim penyedia.
- **Model sekarang: Gemini lewat Vertex AI**, satu-satunya akses pemilik.
  Diuji 30 September 2026 lewat Pydantic AI dengan pemanggilan alat:
  `gemini-3.8-flash`, `gemini-3.5-flash`, dan `gemini-3.1-pro-preview`
  berjalan; varian Pro yang lain belum tersedia di proyek. Titik awal:
  pembangun `gemini-3.8-flash`, akuntan dibandingkan antara
  `gemini-3.8-flash` (berpikir tinggi) dan `gemini-3.1-pro-preview`. Eval
  pertama menentukan pembagiannya.

**Dipecah lima tahap (30 September 2026)**, masing-masing dengan titik periksa
pemilik. Urutannya dari yang dijamin sistem ke yang dikerjakan model, supaya
setiap model yang dicoba sudah berdiri di atas penjaga yang lengkap:

| tahap | isi | yang dilihat pemilik |
|---|---|---|
| 4.1 | Penjaga kontrak, tanpa LLM: transkrip mencatat pelaku setiap langkah; contoh yang diusulkan agent belum disetujui sampai orang menyetujuinya, dan yang sudah disetujui tidak bisa diubah agent; modul beraturan hitung wajib punya contoh dan setiap kolom hitungan diperiksa contoh | penolakan-penolakan itu di Studio dan saat seal |
| 4.2 | Alat agent dan panduan yang dihasilkan sistem, tanpa LLM: sekitar delapan alat, tampilan keadaan yang hemat token, panduan per topik yang dites mencakup setiap langkah dan penolakan | agent tiruan (tanpa model) membangun modul demo lewat alat-alat itu |
| 4.3 | Agent sungguhan, akuntan, dan eval: model per peran lewat konfigurasi, batas biaya, percakapan disimpan, eval tugas kecil dijalankan tiga kali di Gemini | angka baseline Gemini: berapa tugas lulus, langkah, biaya, waktu |
| 4.4 | Interface Studio baru di sekitar agent: percakapan yang streaming, peta, contoh dan angkanya, kartu usulan dengan tombol setuju dan seal | Studio baru dipakai langsung |
| 4.5 | Bukti akhir: PT Maju dibangun ulang lewat agent dari permintaan bisnis | angka sama dengan angka kebenaran |

**Hasil 4.1 (30 September 2026).** Keempat penjaga selesai, 242 test lulus,
replay identik dua kali.

- **Pelaku setiap langkah.** Setiap langkah Studio dilakukan oleh orang atau
  agent, dan transkrip mencatatnya baris per baris (`... person add_class`,
  `... agent expect`). API dan layar selalu orang; alat agent di 4.2 akan
  selalu agent. Di terminal: `do ... --by agent`.
- **Contoh dari agent adalah usulan.** Contoh yang ditulis agent membawa
  `agreed: false`. Ia tetap dijalankan dan angkanya terlihat, karena orang
  menyetujui angka yang bisa ia lihat, tetapi menjadi lubang yang memblokir
  ("apakah contoh ini yang dilakukan bisnis, dan angkanya benar?") dan seal
  menolaknya. Hanya orang yang bisa menyetujui (langkah baru
  `agree_example`); agent yang mencoba ditolak.
- **Contoh yang disetujui milik orang.** Agent ditolak bila mengubah,
  menambah catatan, mengganti angka, atau menghapus contoh yang sudah
  disetujui. Penolakannya menyuruh agent menjelaskan ke orang apa yang harus
  berubah dan kenapa, atau mengusulkan contoh baru. Ganti nama kelas atau
  kolom tetap ikut ke contoh, karena itu bukan perubahan kata bisnis.
- **Setiap kolom hitungan wajib diperiksa contoh.** Kolom yang dihitung aturan
  (aggregate, parameter, expression) di kelas milik draft sendiri harus punya
  minimal satu angka di salah satu contoh. Kalau belum, satu lubang
  memblokir per kolom ("berapa angka yang harus keluar di kolom ini?") dan seal
  menolak sebelum menulis apa pun. Yang menentukan kolom mana yang dihitung
  adalah compiler, bukan aturan kedua. Modul tanpa aturan hitung tetap tidak
  wajib punya contoh. Keputusan kecil di 3.3 dengan ini dibalik.
- **Satu hakim.** Seal dan Studio membaca penjaga yang sama
  (`contract_refusals`); seal berhenti di yang pertama, Studio menampilkan
  semuanya.
- **Yang ikut berubah:** modul demo stok v1 dan v3 sekarang membawa contoh
  seperti v2, dan dua draft uji yang punya aturan hitung diberi contoh. Log
  pengembangan dibangun ulang.

**Hasil 4.2 (30 September 2026).** Alat, panduan, dan agent tiruan selesai,
252 test lulus, replay identik dua kali. `components/agent` lama (MCP P1 dan
server Studio percobaan pertama) dihapus dan diganti; salinannya tetap di tag.

- **Lima alat, tanpa seal dan tanpa setuju:** `look` (draft, sekitarnya,
  contoh lengkap, atau riwayat langkah), `options` (langkah dan jawaban yang
  cocok sekarang), `do` (sekelompok langkah; berhenti di penolakan pertama,
  lalu membalas dengan keadaan draft), `catalogue`, `guide`. Pelakunya selalu
  agent, jadi semua penjaga 4.1 berlaku lewat alat ini juga. Alatnya fungsi
  Python biasa, tidak terikat framework maupun penyedia; nanti bisa juga dibuka
  lewat MCP.
- **Tiga cara mengakhiri giliran:** `Reply` (bicara ke orang), `Question`
  (bertanya, dengan pilihan jawaban), `Proposal` (contoh yang minta disetujui,
  dan apakah siap seal). Usulan diperiksa sistem sebelum sampai ke orang: contoh
  yang disebut harus ada, masih usulan, dan lulus; "siap seal" hanya boleh bila
  yang kurang tinggal persetujuan orang. Usulan yang berlebihan dikembalikan ke
  agent dengan keadaan draft yang sebenarnya. Yang dilihat orang (`put_before`)
  dibaca sistem dari draft, bukan ringkasan agent.
- **Panduan dihasilkan dari sistem:** tujuh topik (alur kerja, langkah, aturan,
  contoh, lubang, penolakan, peran). Langkah, penolakan per gerbang, lubang,
  dan peran dibaca dari kode dan store setiap kali diminta; yang ditulis tangan
  hanya alur kerja dan arti aturan, tanpa istilah domain. Test memastikan
  panduan menyebut setiap langkah, setiap penolakan, setiap lubang terbuka, dan
  sintaks rumus. Instruksi awal agent hanya alur kerja ditambah daftar topik
  (sekitar 3.400 token bersama skema alat).
- **Teks hemat:** membaca draft aplikasi kecil di bawah 2.500 karakter; daftar
  pilihan dipotong di 40 dengan saran mempersempit lewat katalog.
- **Skema datar untuk model apa pun:** argumen langkah berupa daftar pasangan
  nama/nilai, tanpa union dan tanpa map berkunci bebas; nama langkah berupa
  daftar tertutup. Test memeriksa setiap alat dan setiap cara mengakhiri
  giliran. Diuji sekali ke Gemini 3.8 Flash lewat Vertex: semua skema
  diterima, dua alat dipanggil sekaligus, jawaban benar.
- **Agent tiruan** (`python -m components.agent rehearse SCRIPT`): naskah
  langkah diputar lewat agent yang sama dengan yang akan dipakai model, di
  salinan store. Naskah demo (`tests/agent/fixtures/rehearsal.yaml`) membangun
  aplikasi stok: salah menulis rumus tanpa kurung kurawal, dan bacaan
  berikutnya menyodorkan rumus yang benar; mengusulkan contoh yang lulus;
  mengusulkan seal terlalu dini dan dikembalikan; lalu mengusulkan dengan
  benar. Di test, orang menyetujui contohnya dan seal berhasil.

**Hasil 4.3 (30 September 2026).** Agent sungguhan berjalan di Gemini, dengan
akuntan, batas biaya, percakapan yang disimpan, dan setiap panggilan model
tercatat. Baseline penuh (10 tugas × 3) belum dijalankan atas keputusan
pemilik; yang ada adalah uji kecil yang diawasi panggilan demi panggilan.

- **Model per peran lewat `config/agent.yaml`**, satu-satunya tempat nama
  penyedia ditulis: pembangun `gemini-3.8-flash` berpikir sedang (`medium`),
  akuntan model yang sama berpikir tinggi. Batas per permintaan 25 panggilan,
  600.000 token, $0,20; satu panggilan paling lama 60 detik. Harga ditulis per
  model, termasuk harga masukan yang diambil dari cache penyedia (sekitar
  sepersepuluh).
- **Akuntan** konteks terpisah: hanya membaca kata-kata orang dan situasi yang
  diceritakan pembangun, tidak pernah graph. Usulan yang angkanya tidak
  dihitung akuntan dikembalikan ke pembangun sebelum sampai ke orang.
- **Percakapan disimpan di samping draft** (`draft.chat.yaml`): kata orang,
  cara giliran berakhir, biaya, hitungan akuntan, dan seluruh panggilan tiap
  giliran. Giliran berikutnya menerima giliran sebelumnya utuh, sehingga yang
  sudah dibaca tidak dibaca lagi (pilihan pemilik "b"); giliran yang berhenti
  di tengah diserahkan berakhir pada apa yang dikatakan ke orang, tidak pada
  panggilan yang tak berjawab.
- **Setiap panggilan diawasi** (`components/agent/watch.py`): tiap panggilan
  model ditulis utuh ke `build/calls/*.jsonl` — waktu, token masuk, keluar,
  berpikir dan dari cache, apa yang dikirim, apa yang dijawab termasuk
  pikirannya, dan setiap permintaan HTTP dengan statusnya.
  `python -m components.agent watch FILE` membacakannya.
- **Gangguan sesaat dari penyedia diulang** paling banyak dua kali
  (`steady.py`); bila tetap gagal, permintaan berhenti dengan rapi dan
  menyebut sebabnya.
- **Eval** (`components/agent/evals.py`, `make eval`): sepuluh tugas dari
  kegagalan 2.8 dengan kebenaran tersembunyi, dinilai kode, lulus hanya bila
  ketiga putarannya lulus. Putaran berjalan satu per satu, satu baris per
  putaran dicetak saat selesai, eval punya batas biaya sendiri
  (`--dollars`), dan setiap panggilannya tercatat.
- **Jalur ke Google diperbaiki.** Pydantic AI memakai kunci API (*Express
  Mode*) setiap kali kunci ada di lingkungan, walaupun proyek dan lokasi
  disebut. Sekarang lewat login proyek (ADC) dengan proyek tagihan
  (`GOOGLE_CLOUD_QUOTA_PROJECT`) di wilayah `us`; tanpa perubahan kode. Galat
  504 "Deadline expired" ternyata batas waktu kita sendiri yang dikirim ke
  Google (`X-Server-Timeout`): panggilan itu mengantre lebih dari semenit di
  jalur lama. Di `us` tidak ada antrean seperti itu.
- **Yang dipelajari dari uji tugas `on_hand`** (satu putaran tiap setelan):
  berpikir `low` memberi nol token pikiran, agent bekerja refleks satu bacaan
  per panggilan dan dua kali habis batas; `medium` lulus (27 panggilan, $0,18,
  4 menit); `high` habis batas tepat sebelum selesai (berpikir hampir dua kali
  lipat, $0,20). Biaya terbesar adalah percakapan yang dikirim ulang di setiap
  panggilan, bukan jawaban model. Akuntan: 28 dari 30 hitungan benar pada eval
  pertama, dua sisanya waktu habis di jalur lama.
- **Terbuka:** baseline penuh 10 × 3; perbandingan akuntan dengan
  `gemini-3.1-pro-preview`; agent masih cenderung satu alat per panggilan.

**Hasil 4.4, versi pertama (30 September 2026).** Studio dibangun ulang di
sekitar agent; belum dicoba pemilik dengan model sungguhan. 274 test lulus,
replay identik dua kali.

- **Percakapan di kiri, yang dibangun di kanan.** Orang menulis kebutuhan
  dalam bahasa bisnis ("Build with the agent": nama modul dan kebutuhannya,
  modul baru atau yang sudah dibekukan). Selama agent bekerja, setiap
  panggilan muncul saat terjadi: apa yang dibaca, langkah apa yang diambil,
  kapan bertanya ke akuntan, berapa detik dan token, dan pikirannya bila model
  memperlihatkannya. Peta diperbarui setiap kali draft berubah.
- **Empat cara giliran berakhir:** jawaban; pertanyaan dengan pilihan yang
  bisa diklik; usulan; atau berhenti (batas biaya, model, atau penyedia).
  Setiap giliran menyebut biayanya.
- **Kartu usulan** menampilkan yang dibaca sistem dari draft, bukan ringkasan
  agent; setiap contoh dengan angka yang diharapkan dan yang dihasilkan draft,
  dan cara akuntan menghitungnya. Dua tombol hanya milik orang: setujui angka
  contoh, dan bekukan (seal) dengan konfirmasi nama. Seal memakai gerbang yang
  sama dan menolak bila masih ada yang kurang.
- **Sesudah seal** draft ditutup; percakapan yang membangunnya disimpan di
  samping versinya sebagai `vN.chat.yaml`, bersama transkrip dan contohnya.
- **Tab kanan:** Peta (dengan panel dan kontrol tangan yang lama), Contoh
  (semua contoh, status setuju, angka, tabel yang dihasilkan, hitungan
  akuntan), dan *Behind the scenes*.
- **API:** `POST /api/studio/ask` mengalir satu objek JSON per baris saat agent
  bekerja, `GET /api/studio/chat`, `POST /api/studio/seal`. Satu permintaan
  per modul pada satu waktu. Setiap permintaan dari halaman juga menulis
  berkas pengawasan di `build/calls`.

**4.4 diperbaiki (30 September 2026).** Pemilik mencoba versi pertama: graph
kurang interaktif, dan Studio harus benar-benar mudah dipakai dan dipahami, di
layar 4K maupun layar lain. Setelah dilihat langsung di browser: seluruh
aplikasi dibatasi selebar 1.320 titik sehingga peta hanya mendapat sekitar
15% layar; modul yang sudah dibekukan tidak bisa dibuka dari Studio; asal
angka tidak terlihat di peta; nama masih nama mesin; contoh terpisah dari
peta. Disepakati tiga bagian, masing-masing diperiksa pemilik:

| bagian | isi | status |
|---|---|---|
| 1 | Tata letak layar penuh dan peta baru (React Flow), buka modul yang ada, nama yang terbaca | selesai |
| 2 | Lapis "bagaimana angka dihitung", angka contoh dan tanda periksa di peta | selesai |
| 3 | Peta hidup bersama agent, percakapan ↔ peta, kartu usulan dengan peta perubahan | selesai |

**Hasil bagian 1.** Diperiksa sendiri di Chrome, di layar lebar dan dalam
bingkai laptop (1280), tablet (820) dan ponsel (390).

- **Studio memakai seluruh layar** (area lain tetap selebar bacaan). Tiga
  ukuran menurut lebar: lebar (≥1440) percakapan | peta | panel berdampingan;
  sedang (1024–1439) percakapan | peta dan panel meluncur di atas peta;
  sempit (<1024) satu per satu lewat pilihan Percakapan / Peta / Detail. Di
  layar ≥1920 dan ≥2560 huruf sedikit membesar. Percakapan dan panel bisa
  dilipat.
- **Peta baru di atas React Flow** (`web/src/graph.tsx`), susunan bertingkat
  otomatis dengan dagre (`web/src/studioMap.ts`): yang dirujuk di atas, yang
  dibangun di bawah, selalu bentuk yang sama untuk modul yang sama. Zoom,
  peta kecil, "Show all", "Tidy up", pencarian kotak atau isian, panduan "How
  to read this". Klik kotak: garisnya menyala, yang tidak terhubung meredup,
  panel detail terbuka. Tarik titik di atas kotak ke kotak lain untuk
  membuat relasi (langkah `add_slot` + `attach` yang sama). Posisi kotak yang
  digeser diingat browser ini per modul, tidak pernah ditulis ke modul.
- **Nama sebagai kata:** `quantity_on_hand` jadi "Quantity on hand",
  `IngredientStock` jadi "Ingredient stock"; judul isian yang ditulis
  penulisnya didahulukan; nama kelas di depan nama isian dibuang
  (`ingredient_code` di Ingredient jadi "Code"). Nama mesin tetap tertulis
  kecil di panel. Semuanya mekanis, tanpa kamus bisnis mana pun.
- **Isian hitungan diberi tanda** sum / formula / looked up, dan panel
  menjelaskannya dalam kalimat ("Worked out by the formula: On hand -
  Reorder level").
- **Halaman awal Studio:** "Build with the agent" (dengan daftar modul yang
  ada, dan keterangan apakah nama itu modul baru atau perubahan), "Open a
  module" (draft yang sedang dikerjakan, dan setiap modul beku dengan tombol
  "Change it" yang membuka draft perubahannya), dan mulai dengan tangan.
- **Bar atas ringkas:** judul, nama modul, satu kalimat keterangan (sisanya
  di balik "more"), status ("Ready to freeze as v4" atau jumlah pertanyaan),
  tombol bekukan dengan konfirmasi nama langsung dari bar, lipat panel, buang
  draft.
- **Contoh** memakai nama yang sama dengan peta.
- **Test tampilan pertama:** 11 test (vitest) untuk nama, isi peta, dan
  susunan kotak (tetap, tidak bertumpuk, yang digeser tetap di tempatnya);
  `make web-test`, dan `make web` menjalankannya sebelum build. 274 test
  Python tetap lulus, replay identik dua kali.

**Hasil bagian 2 (2 Oktober 2026).** Tanpa satu pun panggilan model.
Diperiksa sendiri di Chrome di layar 4K dan dalam bingkai 1280, 820 dan 390.

- **Peta punya dua cara pandang, satu tombol:** "What's in it" (jenis hal
  dan relasinya, seperti bagian 1) dan "How the numbers are worked out".
  Pilihan diingat browser.
- **Asal angka sekarang kelihatan.** Server menambahkan bacaan compiler
  atas setiap aturan ke keadaan draft (`workings` di
  `components/studio/read.py`): jumlah `over: Flow` di Stock sebenarnya
  menjumlahkan `qty_delta` setiap Movement (modul `@rival/stock-moves`,
  yang mengisi peran Flow), dikelompokkan menurut `item`. Movement
  sebelumnya tidak ada di peta karena tidak ada yang menunjuk ke sana;
  sekarang ia digambar (`read_from`) dengan garis titik-titik "adds up".
- **Lapis angka:** setiap isian hitungan berada di dalam kotak jenisnya,
  dengan panah dari yang dicatat (kiri), lewat aturan, ke hasilnya (kanan):
  dijumlahkan, dicari, atau rumus, masing-masing dengan kalimatnya.
- **Ikuti satu contoh:** pilih contoh dan saatnya ("flour, on 30 Jun
  2026"), lalu angkanya tertulis di peta: catatan yang masuk ke jumlah
  (+25, +25, −14 dengan tanggalnya), nilai yang dicari pada saat itu (20,
  "from the start"; 30 "since 1 Jul 2026"), rumus dengan angkanya (36 − 20),
  dan hasilnya di samping yang dikatakan contoh ("16 ✓ as the example
  says", atau merah "✗ the example says 6"). Yang memang harus kosong
  tertulis "none ✓". Contoh kini membawa catatannya sendiri (`recorded`).
- **Klik satu isian:** semua yang menjadi asalnya dan semua yang memakainya
  menyala, sisanya meredup.
- **Tanda periksa di kedua cara pandang dan di panel:** ✓ diperiksa contoh
  dan benar, ✗ contoh berkata lain, ? belum ada contoh yang memeriksanya,
  … contoh belum dijalankan. Panel detail menjelaskan aturan dengan bacaan
  compiler ("Added up: the qty delta of every movement whose item is this
  row's ingredient").
- **Test:** 27 test tampilan (dari 11), satu test Python baru untuk
  `workings`, `read_from` dan `recorded`. 275 test Python lulus, replay
  identik dua kali.

**Hasil bagian 3 (2 Oktober 2026).** Tanpa satu pun panggilan model: agent
dimainkan dari naskah gladi, langsung dari halaman.

- **Apa yang berubah, dibaca dari draft.** `components/studio/changes.py`
  membandingkan dua kali lihat atas draft (dokumen dan contohnya, tanpa
  compiler): satu baris per jenis hal, isian (`Kind.field`), contoh, modul
  yang dipakai, atau keterangan modul — baru, berubah, atau hilang. Dipakai
  tiga kali: keadaan draft membawa `changes` (semua yang akan dibawa seal
  dibanding versi yang direvisi), setiap giliran menyimpan `touched` (yang
  diubah permintaan itu, ikut tersimpan di `draft.chat.yaml`), dan setiap
  panggilan yang mengubah draft membawa `now` dan `touched` di stream.
- **Peta hidup selama agent bekerja.** Kotak dan isian yang baru diberi
  tanda hijau "new", yang berubah kuning "changed", yang baru saja berubah
  berkedip sekali; di pojok kiri atas peta tertulis "The agent is working
  — 1 new kind, 4 new fields … so far". Sesudahnya "What the agent just
  changed", dengan tombol berhenti menampilkan. Berlaku di kedua cara
  pandang.
- **Percakapan → peta.** Setiap langkah yang mengubah draft dan setiap
  jawaban agent menyebut apa yang diubahnya ("+ Level", "~ Ingredient
  stock", "+ example flour"); klik nama jenis hal membawa peta ke kotaknya
  dan membuka panelnya; "show on the map" menandai perubahan jawaban itu di
  peta.
- **Peta → percakapan.** Panel jenis hal menulis "How it came about":
  permintaan mana yang membuat atau mengubahnya; klik membawa percakapan ke
  permintaan itu dan menyalakannya sebentar.
- **Kartu usulan dengan peta perubahan:** "What freezing it as v1 brings
  in" — satu kotak kecil per jenis hal dengan isian yang baru/berubah/hilang
  dan tanda periksanya, contoh dan modul yang dipakai, dan "See it on the
  map". Dibaca sistem dari draft saat itu, bukan ringkasan agent.
- **Modul yang belum ada** tidak lagi tampil sebagai penolakan merah: selama
  agent memulainya peta menulis "The agent is starting …", sebelum itu
  halaman "belum ada draft" yang biasa.
- **Diperiksa di Chrome** di layar 4K dan dalam bingkai 1280, 820 dan 390:
  baris perubahan tidak pernah menutupi kotak (peta disesuaikan dari letak
  dan tinggi kotak, bukan dari fit React Flow), tidak ada yang melebar ke
  samping; di layar sempit klik dari percakapan pindah ke tab Peta.
- **Gladi dari halaman.** `make app` kini memainkan permintaan pada
  `@rehearsal/levels` dari naskah `tests/agent/fixtures/rehearsal.yaml`,
  satu langkah tiap 1,5 detik, lewat alat dan draft yang sama; modul lain
  tetap ke model. Cara melihat agent membangun di peta tanpa biaya.
- **Test:** 2 test Python baru (perubahan draft terhadap versinya, modul
  baru), test stream agent diperluas (setiap langkah dan giliran menyebut
  perubahannya), 4 test tampilan baru (31).

**Evaluasi dan penyetelan agent (mulai 2 Oktober 2026).** Atas permintaan
pemilik, sebelum 4.5: mengukur kerja agent sungguhan dan menyetel instruksi,
alat, dan sistemnya. Rencana yang disetujui, setiap langkah diumumkan dengan
batas panggilan, biaya dan waktu sebelum dijalankan:

1. satu tugas (`on_hand`) sekali, dibaca per panggilan;
2. kesepuluh tugas masing-masing sekali (paling banyak $2,50);
3. penyetelan per pola kesalahan, bukan per tugas, dan setiap uji ulang hanya
   pada tugas yang terkena;
4. ujian akhir 10 × 3 dan perbandingan akuntan Flash dengan Pro.

Total perkiraan sekitar $12.

- **Langkah 1** (`build/calls/20261002-215110-eval-builder.jsonl`):
  - Lulus dengan 25 panggilan, $0,159, 283 detik. Pembandingnya 30 September:
    27 panggilan, $0,179, 243 detik.
  - Lulusnya tepat di panggilan terakhir yang diizinkan batas, padahal jalan
    yang efisien sekitar 10 panggilan.
  - Panggilan terbuang:
    - 5 untuk catatan contoh tanpa isian wajib yang baru ditolak saat
      dijalankan. Mencatatnya ulang malah menambah catatan kedua, sehingga
      semuanya harus dihapus dan diulang.
    - 5 untuk membaca ulang modul, dan membaca lagi langkah yang sudah ada di
      instruksi.
    - 1 builder dan 1 akuntan (50 detik) untuk hitungan contoh yang kemudian
      tidak dipakai.
    - Dua pesan sistem menyesatkan: modul yang belum ada terdengar seperti
      galat konfigurasi, dan draft kosong disebut "could be sealed now".
- **Perbaikan sesudah langkah 1**, tanpa panggilan model:
  - **Langkah `record`:**
    - Menolak catatan baru yang tidak membawa isian wajib kelasnya, saat itu
      juga, dengan daftar isian yang kurang. Pemeriksanya sama dengan form.
    - Mencatat ulang catatan yang sama pada hari yang sama berarti
      membetulkan pernyataan itu; kelas dan isian yang tidak disebut tetap
      dari yang lama. Aturan ini disetujui pemilik.
  - **Katalog** menyebut isian yang wajib diberikan untuk setiap kelas yang
    bisa dicatat ("a new one must be given …").
  - **Pesan untuk agent:**
    - `look` pada modul yang belum ada menjawab "There is no module … yet",
      ditambah petunjuk `start`.
    - Draft kosong tidak lagi disebut siap diusulkan.
  - **Instruksi:**
    - jangan membaca ulang yang sudah dibaca, termasuk langkah yang sudah
      dijelaskan;
    - `options` hanya untuk pilihan yang cocok saat itu;
    - beberapa modul dibaca dalam satu panggilan katalog;
    - contoh ditentukan utuh dulu, lalu dihitung akuntan sekali.
- **Uji ulang `on_hand`** (`build/calls/20261002-221546-eval-builder.jsonl`):
  - Lulus dengan 15 panggilan (dari 25) dan 171 ribu token (dari 364 ribu).
    Biaya $0,142 (dari $0,159); biaya turun lebih sedikit dari token karena
    cache penyedia jarang kena kali ini.
  - Contoh benar sejak percobaan pertama, dan akuntan hanya dipanggil sekali.
  - Waktu 333 detik, dengan penyebab dari penyedia:
    - Google lambat saat itu. Percobaan pertama gagal tiga kali karena batas
      60 detik, lalu diulang otomatis.
    - Beberapa panggilan memakan 38–67 detik.
  - Sisa pemborosan:
    - Membaca modul masih satu per panggilan.
    - Satu pertanyaan ke orang tentang arah angka, padahal deskripsi modulnya
      sudah menjawab.
    - Satu `look` tepat setelah `start`.
- **Langkah 2, sepuluh tugas sekali**
  (`build/calls/20261002-223322-eval-builder.jsonl`, laporan
  `build/evals/20261002T171141-builder.yaml`):
  - Menurut eval, 9 dari 10 lulus dengan biaya $1,69. Pembacaan jejak
    mengoreksi kedua angka itu:
    - **Biaya sebenarnya $2,14.** Eval tidak menghitung $0,45 yang dipakai
      tiga putaran sebelum jaringan memutusnya.
    - **Yang lulus sebenarnya 8.** `per_supplier` (tidak bisa dibangun)
      dinilai lulus padahal agent tidak pernah memberi tahu orang. Ia
      mencoba berbagai jalan memutar (termasuk faktor konversi yang tidak
      ada hubungannya), membuang draft, mulai lagi, lalu habis batas $0,20.
  - **`revise_existing` gagal**, habis 25 panggilan dalam satu giliran:
    - enam `options` berturut-turut untuk langkah yang sudah ada di
      instruksi;
    - akuntan dipanggil empat kali;
    - salinan store eval ikut membawa draft `@demo/stock` milik pemilik, jadi
      tugasnya tidak mulai seperti yang ditulis.
  - **`received_only` lulus dengan 32 panggilan dan $0,33.** Pada giliran
    kedua agent sudah benar menjawab "tidak bisa". Pemeran orang di eval
    lalu menjawab "put it before me when it is ready", dan agent mencoba
    membangun lagi selama 17 panggilan.
  - **Jaringan:** 19 panggilan habis batas 60 detik (504), dan tiga putaran
    diulang. Akuntan berpikir `high` kadang memakan 45–165 detik.
  - **Pola yang masih ada:**
    - membaca katalog satu per satu;
    - memanggil `options` untuk langkah yang sudah dijelaskan;
    - membaca topik panduan yang sudah ada di instruksi;
    - bertanya tentang arah angka yang sudah ditulis di deskripsi modul.
- **Perbaikan sesudah langkah 2**, tanpa panggilan model:
  - **Eval jujur:**
    - biaya putaran yang diputus jaringan dihitung ke total dan ke batas,
      dan disebut di laporan;
    - tugas yang tidak bisa dibangun lulus hanya bila agent memberi tahu
      orang (giliran berakhir dengan jawaban, bukan habis batas);
    - jawaban ke orang mengakhiri percakapan, karena orang tidak punya yang
      perlu ditambahkan;
    - salinan store eval hanya membawa versi yang sudah di-seal, tanpa draft
      yang sedang dibuka.
  - **Sistem menolak dua hal yang belum bisa dilakukannya dengan kode baru
    `not_possible_yet`.** Pesannya menyuruh agent memberi tahu orang,
    bukan mencari ejaan lain:
    - menjumlahkan hanya baris yang nilainya memenuhi syarat (`where` dengan
      perbandingan);
    - mengelompokkan menurut fakta yang dicapai lewat catatan lain (`by`
      dengan titik).
  - **Instruksi:**
    - daftar "What the system cannot do yet", dengan perintah memberi tahu
      orang dalam satu jawaban;
    - bertanya hanya hal yang belum dijawab kata-kata orang atau deskripsi
      modulnya;
    - `options` menerima beberapa langkah sekaligus.
  - **Pesan:** draft yang tidak terhalang seal kini berbunyi "Nothing blocks
    a seal. Propose it once it does what the person asked."
- **Keraguan pemilik (3 Oktober 2026):** eval memakai naskah sebagai
  "orang".
  - Naskah itu menjawab setiap pertanyaan dengan kalimat yang sama ("putuskan
    sendiri, taruh di depan saya kalau siap") dan menyetujui setiap contoh
    tanpa membacanya.
  - Permintaannya menyebut nama tabel dan kolom teknis.
  - Akibatnya, eval mendorong agent menyelesaikan semuanya dalam satu
    permintaan. Di semua jejak, tiga titik persetujuan (ringkasan kebutuhan,
    angka contoh, seal) menyusut jadi satu kartu di akhir, dan contoh dibuat
    sesudah rumus.
  - Disepakati:
    - satu sesi realistis dulu dengan agent yang sekarang, Claude berperan
      sebagai pengguna lewat jalur yang sama dengan Studio;
    - sesudahnya agent dibuat bertahap secara terstruktur;
    - eval naskah tetap dipakai sebagai uji mesin.
- **Sesi realistis 1 (3 Oktober 2026), stok sederhana, `@toko/stok-bahan`:**
  - **Pengguna:** pemilik toko roti yang tidak tahu istilah teknis dan
    menulis dalam bahasa Indonesia. Fakta tersembunyinya: catatan toko adalah
    `@demo/inventory`, dan tim gudang mencatat kejadian yang sama di
    `@rival/stock-moves`.
  - **Lima giliran, 40 panggilan, $0,36, sekitar 8,5 menit kerja agent:**
    - 2 pertanyaan;
    - 1 giliran berhenti karena batas $0,20;
    - 1 usulan contoh;
    - 1 usulan seal.
  - **Hasil benar:** kebenaran tersembunyi `on_hand` (tepung 20, gula 10)
    lulus di salinan. Seal sengaja tidak ditekan.
  - **Yang baik:**
    - kedua pertanyaannya masuk akal;
    - contoh diusulkan terpisah dari seal;
    - contohnya sendiri memuat catatan gudang yang sama untuk membuktikan
      tidak ada hitung ganda;
    - semua jawaban dalam bahasa Indonesia.
  - **Yang kurang:**
    - tidak ada ringkasan rencana untuk disetujui; agent langsung membangun;
    - rumus dibuat sebelum contoh;
    - istilah teknis bocor ke pengguna (`@demo/inventory`, "modul",
      `StockMovement`);
    - pesan berhenti karena batas biaya tetap berbahasa Inggris;
    - giliran 3 boros: tiga topik panduan dibaca, katalog dibaca satu per
      satu, modul lain dibuka, akuntan dipanggil dua kali, dan satu panggilan
      berpikir 5.000 token;
    - percakapan yang dikirim ulang membuat satu panggilan berisi 20–33 ribu
      token.
  - **Lingkungan:** Docker mati sejak malam sebelumnya, sehingga giliran 3–4
    berjalan tanpa database dan contoh tidak bisa dijalankan. Sistem tetap
    menerima usulan contoh yang belum dijalankan. Itu celah penjaga: usulan
    hanya boleh memuat contoh yang lulus. Database dinyalakan lagi sebelum
    contoh disetujui, dan contohnya lulus.

**Rencana implementasi penyetelan agent (disetujui pemilik 3 Oktober
2026).** Disusun dari sesi realistis 1 dan analisis tiga hal yang diminta
pemilik:
- riwayat percakapan tetap utuh, mengikuti praktik umum sistem agent;
- bahasa ke pengguna luwes mengikuti bahasa dan tingkat pemahaman orangnya;
- bahasa pencatatan baku dan prosedurnya sama untuk setiap agent, karena
  tanpa itu modularitas gagal.

Keputusan pemilik:
- semua rekomendasi diterima;
- bahasa Inggris menjadi bahasa baku pencatatan, dengan label dalam bahasa
  pengguna untuk ditampilkan;
- pelanggaran standar yang bisa dicek mesin menghalangi seal.

Empat tahap, berurutan, masing-masing dengan titik periksa pemilik, lalu 4.5.
Tahap 1–3 adalah pekerjaan kode tanpa panggilan model, kecuali satu uji kecil
di tahap 2 yang diumumkan dulu.

Prinsip pembagiannya: ke pengguna agent luwes, ke catatan agent seragam.
Keseragaman itu dijaga sistem, bukan bergantung pada disiplin masing-masing
model, sehingga model atau penyedia apa pun menghasilkan catatan yang sama
bentuknya.

*Tahap penyetelan 1 — standar pencatatan.* Masalahnya terlihat di sesi 1:
agent mencatat modul dalam bahasa Indonesia (`StokBahan`, `bahan`,
`sisa_stok`), padahal semua modul lain berbahasa Inggris
(`IngredientStock`, `movement_quantity`), dan saat ini tidak ada aturan
pencatatan sama sekali. Akibatnya modul tidak saling menemukan di katalog,
konsep dibuat ulang, nama bertabrakan antarmodul (`item` milik
`@rival/stock-moves`), dan makna yang tidak tertulis (satuan, arah angka,
arti tanggal) menjadi sumber kegagalan 2.8: hitung ganda dan tanda terbalik.

- **Bahasa baku: Inggris.** Berlaku untuk nama modul, jenis, kolom dan enum,
  serta `title` dan `description`-nya, dan untuk `says` pada contoh.
- **Label dalam bahasa pengguna** disimpan di samping yang baku, per bahasa,
  memakai tempat yang sudah disediakan LinkML (label dengan `in_language`).
  Bentuk pastinya ditetapkan saat implementasi, mengikuti apa yang dibaca
  generator.
  - Studio dan alat agent menampilkan label dalam bahasa orangnya bila ada,
    dan yang baku bila tidak.
  - Kata-kata orang pada contoh tetap disimpan sebagai labelnya.
- **Pola nama**, dicek mesin:
  - Jenis: kata benda tunggal bahasa Inggris, huruf besar di awal setiap kata
    (`StockMovement`), hanya ASCII.
  - Kolom: huruf kecil dengan garis bawah, dengan awalan yang sama untuk
    semua kolom milik satu jenis (`movement_quantity`, `movement_happened_on`).
  - Modul: `@scope/nama-dengan-tanda-hubung`.
- **Makna wajib:**
  - Setiap jenis dan kolom punya deskripsi. Pertanyaan terbuka
    `nothing_said_about_it` menjadi penghalang.
  - Setiap kolom angka punya satuan (LinkML `unit`), termasuk kolom hitungan.
  - Setiap jumlah menyebut arahnya: apa yang positif.
  - Setiap tanggal menyebut artinya: kapan terjadi atau kapan dicatat.

  Arah dan arti tanggal ditulis sebagai isian terstruktur dari daftar
  tertutup, bukan hanya prosa. Ini sekaligus menjawab sebagian pertanyaan
  terbuka nomor 6 (satuan, dan waktu dengan dua sumber).
- **Bahasa Inggris pada deskripsi** diperiksa dengan pendeteksi bahasa yang
  ringan. Teks yang jelas bukan bahasa Inggris menghalangi seal; yang
  meragukan hanya menjadi pertanyaan terbuka.
- **Prosedur yang sama untuk setiap agent:**
  1. cari di katalog;
  2. pakai ulang dan pin yang sudah ada;
  3. isi peran bersama;
  4. buat hanya yang belum ada;
  5. contoh;
  6. rumus.

  Prosedur dan standar ditulis satu kali, di sistem. Pemeriksaan seal dan
  panduan agent dibaca dari sumber yang sama, sehingga apa yang diajarkan
  tidak bisa berbeda dari apa yang ditegakkan.
- **Penegakan:**
  - Setiap pelanggaran yang bisa dicek mesin menjadi lubang penghalang di
    Studio dan penolakan di seal, dengan langkah perbaikannya.
  - Bila perlu, langkah Studio baru untuk mengisi satuan, arah, arti tanggal
    dan label.
  - Panduan agent mendapat bagian "standar pencatatan" yang dihasilkan dari
    pemeriksaan itu.
- **Modul demo** (`@demo/*`, `@rival/stock-moves`) dibawa ke standar lewat
  versi baru dengan prosedur yang sama: satuan, arah, arti tanggal, label
  Indonesia. Versi lama tetap utuh, karena versi yang sudah di-seal tidak
  pernah diubah.
- **Eval "standar pencatatan":** tugas eval mesin juga memeriksa bahwa modul
  yang dibangun agent memenuhi standar. Sebuah model baru dianggap layak
  bila lulus.
- **Titik periksa pemilik:** penolakan standar di Studio, modul demo versi
  baru dengan labelnya, dan modul `@toko/stok-bahan` dari sesi 1 yang kini
  ditolak beserta cara memperbaikinya.

*Tahap penyetelan 2 — riwayat utuh yang murah.* Riwayat tetap dikirim utuh:
kata orang, setiap pemanggilan alat beserta hasilnya, dan setiap jawaban
agent. Pilihan "b" dari 4.3 dipertahankan. Yang dibenahi adalah biayanya dan
pengulangannya.

- **Instruksi tetap, keadaan di pesan.**
  - Kalimat keadaan modul ("belum ada", "draft-nya terbuka") sekarang ada di
    instruksi dan berubah setiap kali keadaan berubah. Akibatnya potongan
    cache penyedia (sekitar 90%) tidak berlaku: di jejak, "0 cached" muncul
    tepat setelah `start` dan di awal setiap giliran.
  - Instruksi dibuat tetap. Keadaan disampaikan di pesan giliran dan di
    jawaban alat, sesuai praktik umum: bagian tetap di depan, bagian berubah
    di belakang.
  - Dibuktikan dengan satu uji kecil yang diumumkan dulu, dengan
    membandingkan token yang kena cache di awal giliran dan sesudah `start`.
- **Alat yang tahu pengulangan.** Bacaan yang sama dengan hasil yang sama
  dijawab "sama dengan bacaan ke-N di atas, tidak berubah". Ini berlaku untuk
  `look`, `catalogue`, `options` dan `guide`. Agent tahu ia sudah memegang
  isinya, dan isi yang sama tidak dibayar dua kali.
- **Pemendekan bacaan usang**, hanya bila percakapan sangat panjang (ambang
  awal sekitar 100 ribu token, disetel dari pengukuran). Teknik ini disebut
  "tool result clearing".
  - Hasil bacaan yang sudah tergantikan oleh bacaan baru diganti catatan satu
    baris. Contohnya isi draft yang sudah dibaca ulang.
  - Pemanggilannya tetap tercatat.
  - Kata orang, jawaban agent, dan langkah `do` beserta hasilnya tidak pernah
    dipendekkan.
- **Berhenti dengan sopan.** Satu panggilan terakhir disisakan dari batas
  per permintaan, supaya agent sendiri yang menjelaskan apa yang sudah dan
  belum dikerjakan, dalam bahasa orangnya. Pesan sistem yang tetap hanya
  dipakai bila panggilan itu pun gagal.
- **Titik periksa pemilik:** angka cache dan token per panggilan sebelum dan
  sesudahnya, dari uji kecil tadi.

*Tahap penyetelan 3 — agent bertahap, bahasa yang luwes.*

- **Kartu Rencana.** Agent mendapat cara keempat untuk mengakhiri giliran,
  `Plan`: apa yang akan dibangun dalam bahasa bisnis, dari catatan mana,
  angka apa yang dihasilkan, dan apa yang belum bisa dilakukan sistem. Studio
  menampilkannya dengan tombol "Setuju, lanjut" dan "Ubah". Persetujuannya
  adalah langkah orang, seperti `agree_example`, dicatat di samping draft dan
  tidak bisa dilakukan agent.
- **Urutan dijaga sistem.** Rumus (`aggregate`, `parameter`, `expression`)
  ditolak sebelum ada rencana yang disetujui, dan sebelum ada contoh yang
  disetujui orang untuk tabel itu. Jenis dan kolom tanpa rumus boleh dibuat
  lebih dulu, karena contoh membutuhkannya. Urutannya menjadi:
  1. pahami;
  2. rencana disetujui;
  3. contoh disetujui;
  4. rumus sampai contohnya cocok;
  5. seal.

  Setiap tahap adalah satu permintaan dengan batasnya sendiri.
- **Bahasa yang luwes**, diajarkan sebagai prinsip, bukan daftar larangan:
  - ikuti bahasa dan gaya orangnya;
  - baca tingkat pemahamannya dari cara ia menulis;
  - pakai istilah teknis hanya bila ia sendiri memakainya;
  - tanyakan bila ragu seberapa rinci penjelasan yang diinginkan.

  Alat menampilkan label dalam bahasa orangnya lebih dulu (dari tahap 1),
  supaya agent punya kata-kata bisnis untuk dipakai.
- **Celah yang ditutup:** contoh hanya boleh diusulkan untuk disetujui bila
  sudah dijalankan dan lulus.
- **Eval mesin disesuaikan.** Pemeran orang menyetujui rencana dan contoh,
  dan tidak lagi menyuruh agent menyelesaikan semuanya sendiri. Eval ini
  tetap dijalankan setelah setiap perubahan untuk memastikan alat dan sistem
  tidak rusak.
- **Titik periksa pemilik:** Kartu Rencana dan urutan yang dijaga, dicoba di
  Studio dengan gladi tanpa model.

*Tahap penyetelan 4 — sesi realistis diulang.*

- Claude kembali berperan sebagai pengguna lewat jalur yang sama dengan
  Studio. Ada tiga skenario:
  - stok sederhana, diulang untuk dibandingkan dengan sesi 1;
  - dua sistem yang mencatat kejadian yang sama;
  - permintaan yang belum bisa dibangun (per pemasok).
- Setiap sesi diumumkan dengan batasnya (sekitar $1). Database diperiksa
  dulu sebelum mulai.
- Penilaian:
  - angka akhir terhadap kebenaran tersembunyi;
  - berhenti di tiga titik persetujuan;
  - bahasa sesuai orangnya;
  - catatan memenuhi standar;
  - biaya dan waktu per giliran.
- Sesudahnya:
  - ujian akhir eval mesin 10 × 3;
  - perbandingan akuntan Flash dan Pro;
  - 4.5 (PT Maju dibangun ulang lewat agent).

**Hasil tahap penyetelan 1 (3 Oktober 2026).** Standar pencatatan terpasang
sebagai komponen sendiri, `components/standard`. Komponen ini menjadi satu
sumber untuk tiga pembaca: seal menolak, Studio menunjukkan lubang beserta
langkah perbaikannya, dan panduan agent mengajarkannya (bagian "Recording
standard" dihasilkan dari daftar yang sama). Tidak ada panggilan model.

- **Yang diperiksa mesin**, masing-masing dengan kode penolakan sendiri:
  - bentuk nama: jenis dan enum `PascalCase`, kolom `snake_case` minimal dua
    kata dengan kata depan yang sama per jenis, nilai enum `snake_case`;
  - deskripsi wajib untuk jenis dan kolom;
  - bahasa Inggris pada nama, judul, deskripsi, dan `says` contoh;
  - satuan untuk setiap angka;
  - arah setiap angka dari daftar tertutup: `increase`, `decrease`,
    `magnitude`, `level`;
  - arti setiap tanggal dari daftar tertutup: `happened`, `recorded`,
    `takes_effect`, `expected`.

  Pertanyaan terbuka `nothing_said_about_it` kini menjadi penghalang
  (`description_missing`). Kolom pengenal tidak diminta satuan atau arah.
- **Pendeteksi bahasa** ringan dan tanpa pustaka baru. Ia membaca kata umum
  bahasa Inggris dan beberapa bahasa lain berhuruf Latin, serta aksara
  tulisan.
  - Teks yang jelas bukan bahasa Inggris menghalangi seal.
  - Teks yang tidak bisa ditentukan menjadi pertanyaan terbuka
    (`maybe_not_english`).
  - Batasnya: nama dari kata yang tidak dikenalnya lolos, dan deskripsi di
    sampingnya yang membawa pemeriksaan.
- **Label** memakai tempat LinkML: `structured_aliases` dengan `in_language`.
  - Langkah Studio baru `label` mengisinya untuk modul, jenis, kolom, enum,
    nilai enum, dan contoh. Pada contoh, kata-kata orang disimpan sebagai
    `labels`.
  - `add_slot` dan `set_slot` menerima `unit`, `direction` dan
    `time_meaning`, sehingga satu langkah bisa memenuhi standar.
  - Katalog mencari juga lewat label, jadi orang bisa mencari dengan kata-kata
    sendiri.
  - Alat agent menampilkan label, satuan, arah dan arti tanggal.
  - Studio menggambar peta dan panel dengan kata orang. Bahasanya mengikuti
    browser, atau dipilih lewat "Words in" yang muncul bila modul menyimpan
    label.
- **Batas berlakunya.** Standar berlaku untuk draft yang di-seal ke modul di
  penyimpanan, karena di sanalah modul saling menemukan. Nama modul diperiksa
  saat `start`, sebab modul tidak bisa diganti namanya. Versi yang di-seal
  sebelum standar ada tidak diubah: `dev_modules` memutar ulang sepuluh versi
  sejarah tanpa standar.
- **Modul demo versi baru** dengan standar dan label Indonesia:
  `@demo/catalog@v4`, `@demo/inventory@v4`, `@rival/stock-moves@v2`, dan
  `@demo/stock@v4`.
  - Rival mengganti nama kolomnya ke awalan `move_`; predikatnya tetap,
    sehingga data lama tetap miliknya.
  - Aplikasi mengganti nama kolomnya ke awalan `stock_`. Aturannya tidak
    berubah sama sekali walau rival berganti nama, karena aturan itu menunjuk
    peran inti.
- **Eval**:
  - tugas dan bangunan rujukannya dipindah ke versi baru;
  - eval kini menyebut terpisah bila draft yang disebut siap melanggar
    standar ("not to the recording standard").
- **Uji**: 301 test Python lulus (18 di antaranya baru, untuk standar) dan 34 test
  tampilan.
- **Penyimpanan pengembangan** ditambah tanpa dikosongkan
  (`dev_modules.py --extend`): catalog v4, inventory v4 dan rival v2 masuk.
  `@demo/stock@v4` belum, karena ada draft `@demo/stock` yang terbuka; isinya
  hanya langkah `revise` dari v3.
- **Draft `@toko/stok-bahan` dari sesi 1** sekarang punya 13 pertanyaan
  penghalang di Studio: nama dan teks berbahasa Indonesia, nama kolom
  `bahan`, serta satuan dan arah `sisa_stok`. Setiap pertanyaan membawa
  langkah perbaikannya.

**Hasil tahap penyetelan 2 (3 Oktober 2026).** Riwayat tetap dikirim utuh;
yang berubah adalah bagaimana ia dikirim.

- **Instruksi tetap.** Keterangan modul mana yang dibuka dan keadaannya tidak
  lagi di instruksi, tetapi di awal pesan orang, sebagai catatan sistem yang
  dibaca dari penyimpanan saat permintaan dimulai. Percakapan tetap menyimpan
  kata-kata orang apa adanya.
- **Bacaan yang sama dijawab satu baris** (`[unchanged]`) untuk `look`,
  `options`, `catalogue` dan `guide`, bila isinya sama dengan bacaan terakhir
  hal yang sama di percakapan itu. Sebagai ganti nomor bacaan, baris itu
  menyebut panggilannya sendiri.
- **Bacaan usang dipendekkan** (`[cleared]`) bila panggilan terakhir sudah
  `clear_above` token (100.000, di `config/agent.yaml`). Semua bacaan usang
  dipendekkan sekaligus, supaya cache hanya terganggu sekali. Pemanggilannya
  tetap tercatat; kata orang, jawaban agent, dan langkah `do` tidak pernah
  dipendekkan.
- **Berhenti dengan sopan.** Panggilan terakhir yang muat di batas disisakan:
  agent diberi catatan sistem dan hanya boleh membalas, dan balasannya menjadi
  pesan berhenti. Pesan tetap sistem hanya dipakai bila model tetap memanggil
  alat. Perkiraan biaya panggilan berikutnya memakai harga penuh, karena
  panggilan pamit jarang kena cache (lihat di bawah).
- **Cacat yang ditemukan dan diperbaiki:** percakapan tidak disimpan sebelum
  modul di-`start`. Di sesi realistis 1, tiga giliran pertama berjalan tanpa
  ingatan akan pertanyaan agent sendiri. Kini percakapan disimpan sejak pesan
  pertama, di tempat draft nanti berada; tempat itu belum menjadi modul karena
  belum punya manifest.
- **Uji**: 308 test Python lulus (7 baru, `tests/agent/test_conversation.py`).
- **Uji kecil dengan model** (disetujui pemilik): dua permintaan bahasa
  Indonesia untuk modul stok harian di salinan penyimpanan pengembangan,
  Gemini 3.8 Flash, batas 10 panggilan dan $0,08 per permintaan. Hasilnya 18
  panggilan builder dan 1 akuntan, $0,149, sekitar 3 menit.

  | Ukuran | Sesi 1 (sebelum) | Uji (sesudah) |
  |---|---|---|
  | Panggilan sesudah `start` | 0 dari 24.166 kena cache | 11.649 dari 16.762 |
  | Panggilan pertama giliran berikutnya | 0 dari 32.851 (giliran 5) | 11.681 dari 16.382 |
  | Panggilan builder tanpa cache, selain yang pertama | 11 dari 36 | 2 dari 17, keduanya panggilan pamit |
  | Porsi input kena cache, keseluruhan | 63% | 60% |

  Penilaiannya:
  - Dua titik yang dituju terbukti: sesudah `start` dan di awal giliran,
    cache kini berlaku.
  - Porsi keseluruhan tidak naik. Gemini menyimpan cache per blok sekitar
    4.000 token dari awal, jadi ujung percakapan yang terus tumbuh selalu
    dibayar penuh; percakapan uji lebih pendek, sehingga ujung itu porsinya
    lebih besar. Penghematan nyata ada pada hilangnya panggilan tanpa cache.
  - Kedua panggilan pamit tidak kena cache sama sekali. Kemungkinan besar
    karena pembatasan "hanya boleh membalas" ikut menjadi bagian kunci cache
    penyedia. Biayanya sekitar $0,01 per pamit, dan pamit hanya terjadi saat
    batas tercapai.
  - Riwayat sebelum `start` terbukti tersimpan: permintaan 1 berhenti sebelum
    modul dibuat, dan permintaan 2 menerima seluruhnya (akuntan pun membaca
    kedua pesan orang).
  - Bacaan berulang dan pemendekan tidak terpicu di uji ini: tidak ada bacaan
    yang diulang persis, dan percakapan paling panjang 21 ribu token. Keduanya
    baru terbukti oleh test otomatis.
  - Pamit berjalan di kedua permintaan, dalam bahasa Indonesia, dan isinya
    sesuai dengan yang benar-benar dikerjakan. Istilah teknis masih bocor
    (`@toko/stok-harian`, `count_date`, "blocking holes"); ini bagian tahap 3.
  - Batas biaya sempat terlewati $0,006 di permintaan 2, karena perkiraan
    memakai harga cache dari panggilan sebelumnya, sedangkan pamitnya tidak
    kena cache. Sudah diperbaiki: perkiraan memakai harga penuh.
  - Di luar cakupan tahap ini, tetapi tercatat: permintaan 1 ("langsung mulai
    saja") menghabiskan 9 panggilan hanya untuk membaca, termasuk tiga topik
    panduan. Lalu di permintaan 2 kolom bahan dibuat sebagai teks, bukan
    menunjuk `Ingredient` di `@demo/catalog` yang sudah dibacanya. Standar
    tidak menangkap ini karena tidak bisa dicek mesin. Keduanya bahan untuk
    tahap 3 dan sesi realistis 2.

**Hasil tahap penyetelan 3 (3 Oktober 2026).** Agent kini bekerja bertahap,
dan urutannya dijaga sistem, bukan diingat agent. Tidak ada panggilan model.

- **Kartu Rencana.** `Plan` menjadi cara keempat mengakhiri giliran: apa yang
  dibangun, dari catatan mana, angka apa yang keluar, dan apa yang belum bisa.
  - Rencana disimpan di samping draft (`draft.plan.yaml`) persis seperti yang
    ditunjukkan ke orang, juga sebelum modul di-`start`.
  - Persetujuannya adalah langkah Studio baru, `agree_plan`. Hanya orang yang
    bisa mengambilnya, dan langkah itu tercatat di transkrip.
  - Rencana yang diajukan ulang menggantikan yang lama dan harus disetujui
    lagi.
  - Setelah seal, rencana disimpan di samping versinya (`vN.plan.yaml`).
    Draft yang dibuang ikut membawanya pergi.
  - Catatan sistem di awal setiap permintaan menyebut keadaan rencana: belum
    ada, menunggu persetujuan, atau sudah disetujui.
- **Urutan dijaga sistem.** Langkah `aggregate`, `parameter` dan `expression`
  dari agent ditolak bila rencana belum disetujui (`plan_not_agreed`), dan
  bila belum ada contoh yang disetujui orang untuk tabel itu
  (`no_agreed_example`). Penolakannya menyebut apa yang harus didahulukan.
  Orang yang membangun sendiri di Studio tidak terikat urutan ini.
- **Angka yang menunggu rumusnya.** Ini bagian yang tidak ada di rencana
  tahap, tetapi ternyata dibutuhkan. Urutan baru meminta contoh disetujui
  sebelum rumus ditulis. Padahal, dari percobaan, tabel hitungan yang belum
  punya rumus belum dianggap tabel, sehingga contohnya ditolak seluruhnya.
  - Kini angka di tabel milik draft yang belum dibuat rumus, atau sel kosong
    di kolom yang belum punya rumus, ditandai "menunggu rumus" (`waiting`),
    bukan salah.
  - Contoh yang kekurangannya hanya angka yang menunggu bisa diajukan dan
    disetujui. Contoh itu tetap belum lulus, jadi seal tetap tertahan sampai
    rumusnya ditulis dan angkanya cocok.
- **Celah yang ditutup.** Contoh hanya boleh diajukan bila sudah dijalankan,
  dan bila ia lulus atau hanya menunggu rumus. Contoh yang tidak bisa
  dijalankan (tidak ada log) kini ditolak dengan alasannya. "Lulus" di
  rencana tahap ditafsirkan begini, karena dalam urutan baru contoh
  disetujui sebelum rumusnya ada.
- **Bahasa yang luwes**, sebagai prinsip di panduan:
  - ikuti bahasa dan gaya orangnya;
  - baca tingkat pemahamannya dari cara ia menulis;
  - pakai istilah teknis hanya bila ia memakainya, dan sebut sesuatu dengan
    kata-katanya sendiri;
  - tanyakan bila ragu seberapa rinci penjelasan yang diinginkan.

  Panduan ditulis ulang dalam lima tahap (pahami, rencana, contoh, rumus,
  seal) dan tetap di bawah 20.000 karakter.
- **Studio.**
  - Kartu Rencana punya tombol "Agree, go on" (langkah orang, lalu agent
    lanjut) dan "Change it" (kotak tulis meminta apa yang harus diubah).
  - Angka yang menunggu rumus ditandai "…", dengan keterangan "worked out once
    its rule is written".
  - Tombol setuju contoh aktif untuk contoh yang menunggu rumus.
- **Gladi** kini terdiri dari beberapa permintaan. Permintaan yang sedang
  dimainkan dibaca dari jumlah permintaan di percakapan, sehingga halaman bisa
  memintanya berulang kali. Skrip gladi dipecah menjadi rencana, contoh dan
  rumus. Di tengahnya, agent sengaja mencoba rumus terlalu awal dan ditolak.
- **Eval mesin**:
  - pemeran orang menyetujui rencana dan contoh lewat fungsi yang sama dengan
    gladi (`person_agrees`), lalu berkata "I agree. Go on.";
  - jawaban bakunya tidak lagi menyuruh menyelesaikan semuanya sendiri;
  - batas giliran naik dari 6 ke 8, karena satu tugas kini paling sedikit
    tiga permintaan;
  - bangunan rujukan dijalankan sebagai orang.
- **Uji**: 310 test Python dan 34 test tampilan lulus.
- **Dicoba di Studio** (Chrome, server pemeriksaan di salinan penyimpanan
  pengembangan, tanpa model):
  - rencana tampil sebelum ada draft;
  - "Change it" mengarahkan ke kotak tulis;
  - "Agree, go on" menyetujui lalu menjalankan permintaan berikutnya;
  - rumus yang dicoba terlalu awal ditolak `no_agreed_example`;
  - contoh flour tampil menunggu rumus dan bisa disetujui;
  - permintaan ketiga menulis rumus, lalu draft siap dibekukan sebagai v1.
- **Catatan untuk berikutnya**:
  - Contoh yang menunggu rumus masih tampil sebagai tiga pertanyaan
    penghalang di panel Studio, dengan kalimat teknis. Benar, tetapi ramai.
  - Teks tombol dan kerangka Studio masih berbahasa Inggris. Pesan yang
    dikirim tombol, "Agreed, go on.", karenanya juga berbahasa Inggris;
    panduan memberi tahu agent bahwa itu bukan bahasa orangnya.

**Hasil tahap penyetelan 4 (3 Oktober 2026): sesi realistis diulang.**
Claude berperan sebagai pemilik toko roti yang menulis dalam bahasa
Indonesia dan tidak tahu istilah teknis. Agent sungguhan (Gemini 3.8 Flash)
berjalan di server Studio dengan kode tahap 3, di atas salinan penyimpanan
pengembangan. Database diperiksa dulu. Batasnya diumumkan sebelum mulai:
paling banyak 6 permintaan per skenario, batas per permintaan tidak diubah
(25 panggilan, $0,20).

- **Skenario 1**, stok sederhana, pembanding sesi 1, dijalankan seluruhnya
  lewat Studio di Chrome dengan tombol-tombolnya:
  - jalannya: rencana; rencana diubah karena orangnya minta catatan gudang
    tidak dihitung; contoh yang menunggu rumus; rumus; siap dibekukan;
  - 4 permintaan, 25 panggilan, $0,20, sekitar 4,5 menit kerja agent;
    sesi 1 dulu 40 panggilan, $0,36, 8,5 menit.
- **Skenario 2**, dua sistem yang mencatat kejadian yang sama
  (`@toko/cek-gudang`, lewat API yang sama dengan Studio):
  - orangnya ingin melihat sisa stok menurut catatan toko dan menurut catatan
    gudang, berdampingan per bahan, beserta selisihnya;
  - agent bertanya dengan dua pilihan arah selisih, lalu mengajukan rencana,
    contoh dan rumus;
  - 4 permintaan, 24 panggilan, $0,19, sekitar 4 menit.
- **Skenario 3**, permintaan yang belum bisa dibangun
  (`@toko/stok-pemasok`, lewat API):
  - agent menjawab jujur bahwa sisa stok belum bisa dijumlahkan per pemasok,
    dengan alasan dalam bahasa sehari-hari, tanpa membangun apa pun;
  - ketika ditanya apa yang paling mendekati, ia menawarkan sisa stok per bahan
    beserta pemasok dan satuannya, dan menambahkan alasan sendiri: bahan
    dengan satuan berbeda memang tidak bisa dijumlahkan jadi satu angka;
  - rencananya mencantumkan yang belum bisa;
  - satu permintaan berhenti karena batas biaya: rumus untuk kolom pemasok dan
    satuan membutuhkan contoh baru yang disetujui orang;
  - 6 permintaan, 33 panggilan, $0,36, sekitar 8 menit.
- **Total**: 14 permintaan, 82 panggilan, $0,75, sekitar 16 menit kerja agent.

Penilaian:

- **Angka akhir**: ketiganya lulus kebenaran tersembunyi di salinan, dan
  ketiganya memenuhi standar pencatatan (bisa dibekukan):
  - skenario 1: tepung 20, gula 10, dan catatan gudang tidak ikut dihitung;
  - skenario 2: toko 20, gudang 30, selisih −10;
  - skenario 3: tepung 20, gula 10, dengan kolom pemasok dan satuan yang
    diambil lewat bahannya.
- **Tiga titik persetujuan**: ditaati di ketiga skenario, yaitu rencana,
  angka contoh, dan pembekuan yang dibiarkan untuk orangnya. Tidak ada rumus
  sebelum contoh disetujui. Agent juga sempat mencoba mengubah contoh yang
  sudah disetujui orang, dan sistem menolaknya.
- **Bahasa**:
  - pertanyaan, contoh dan penjelasan berbahasa Indonesia sehari-hari, dengan
    tanggal dan jumlah yang dirinci;
  - tetapi daftar sumber di setiap rencana memuat nama teknis
    (`@demo/catalog@v4`, `StockMovement`, "modul", "disematkan"), juga
    setelah orangnya bilang tidak paham nama dengan tanda @;
  - pesan akhir memakai "modul" dan "disegel (seal)", dan pesan berhenti
    menyebut nama contoh (`stok_awal`).
- **Catatan**: standar pencatatan terpenuhi di ketiga draft.
- **Biaya dan waktu**: permintaan rencana dan rumus murah ($0,01–0,04);
  permintaan contoh yang paling mahal ($0,06–0,14), karena di sana tabel
  dibangun, akuntan dipanggil dan contoh dijalankan.

Temuan untuk diperbaiki:

1. Nama teknis di daftar sumber rencana. Kolom `records` di Kartu Rencana
   tampaknya mengundang agent menyebut modul. Jalan yang diusulkan:
   panduannya meminta catatan disebut dengan kata-kata orangnya, dan Studio
   yang menunjukkan modulnya bila perlu.
2. Draft yang masih kosong, sebelum rencana disetujui, sudah ditandai "Ready
   to freeze as v1" di Studio. Sistem menganggap modul yang belum berisi apa
   pun boleh dibekukan.
3. Bila rumus membutuhkan contoh baru (kolom baru), satu permintaan bisa habis
   batasnya sebelum contoh itu diajukan. Contoh baru itu lalu harus dicari
   orangnya sendiri di panel contoh, bukan di kartu usulan.
4. Tampilan:
   - tanda tebal `**...**` di pesan agent tampil mentah;
   - cerita contoh dan pertanyaan di panel kanan berbahasa Inggris (bahasa
     pencatatan) dan teknis;
   - daftar tabel di panel kanan tidak ikut pilihan bahasa;
   - percakapan melompat posisinya setelah contoh disetujui.
5. Agent membangun tabel dan kolom sebelum rencana disetujui (skenario 2).
   Ini diizinkan, karena urutan hanya menjaga rumus, tetapi pemilik bisa
   memutuskan apakah bangunan juga harus menunggu rencana.

**Perbaikan temuan sesi (4 Oktober 2026).** Pemilik meminta temuan rumus (3)
dan tampilan (4) diperbaiki lebih dulu, lalu urutan kerja (5) disempurnakan,
sebelum uji dari lingkungan kosong. Tidak ada panggilan model.

- **Permintaan yang berhenti di tengah (temuan 3).** Ditelusuri dari sesi 3:
  rumus sudah selesai, tetapi anggaran habis sebelum contoh baru diajukan.
  Contoh baru itu juga ditulis agent tanpa akuntan.
  - Bila permintaan berhenti, sistem sendiri membaca draft dan menaruh apa
    yang menunggu orangnya di samping pesan berhenti: contoh yang bisa
    disetujui sekarang, dengan angka dan hitungan akuntan, dan apakah draft
    lalu siap dibekukan (`left_waiting`, `agree` dan `seal` pada `Stopped`).
    Pemeriksaannya sama dengan usulan agent. Contoh yang angkanya tidak dari
    akuntan tidak ikut ditaruh, seperti di sesi 3.
  - Studio menampilkan kartu berhenti itu seperti kartu usulan, dengan tombol
    setuju dan tombol bekukan.
  - Pesan perpisahan agent diberi tahu bahwa contoh itu ditunjukkan sistem,
    dan diminta tidak menyebut kode contoh.
  - Panduan tahap contoh kini meminta setiap kolom yang akan tampil di tabel,
    termasuk kolom yang diambil lewat rujukan, sudah diberi nilai di contoh
    pertama. Kolom baru di tahap rumus butuh contoh baru, dan giliran ditutup
    dengan mengajukannya.
- **Draft kosong (temuan 2).** Draft yang belum berisi apa pun, atau revisi
  yang tidak mengubah apa pun, ditandai `empty` dan tidak lagi disebut bisa
  dibekukan. Studio menulis "Nothing built yet". Usulan "siap dibekukan" dari
  agent atas draft kosong dikembalikan.
- **Tampilan (temuan 4).**
  - Pesan agent dibaca menjadi paragraf, daftar bernomor dan berbutir, huruf
    tebal dan kode pendek, tanpa memasukkan HTML. Tanda `**` tidak lagi
    tampil mentah.
  - Pilihan bahasa ("Words in") kini berlaku untuk seluruh halaman: daftar
    tabel di panel kanan, nama tabel dan kolom di setiap contoh, peta
    perubahan di kartu usulan, dan daftar "Changed:". Contoh membawa label
    bahasanya ke halaman, sehingga ceritanya tampil dalam bahasa orangnya.
  - Pertanyaan di panel kanan tentang contoh kini berbahasa biasa: "Apakah
    angka di contoh ini benar?", "Contoh ini menunggu rumusnya", "Contoh mana
    yang menyebut angka kolom ini?". Contoh yang menunggu rumus muncul sekali,
    bukan sekali per angka.
  - Percakapan hanya bergulir sendiri bila ada yang baru, dan hanya di dalam
    kotaknya. Diperiksa di Chrome: posisi gulir tetap sama setelah contoh
    disetujui.
  - Kerangka Studio tetap berbahasa Inggris, begitu pula bacaan sistem di
    bawah kartu usulan ("What the system reads off the draft").
- **Urutan kerja (temuan 5).** Agent kini tidak mengambil langkah apa pun,
  termasuk membuat draft, sebelum rencananya disetujui (`plan_not_agreed`).
  Rencana yang diajukan ulang menghentikan pembangunan sampai disetujui lagi.
  Orang yang membangun sendiri tetap bebas. Catatan sistem di awal permintaan
  dan pesan "modul belum ada" ikut menyebutnya.
- **Nama teknis di rencana (temuan 1, sebagian).** Kolom `records` di Kartu
  Rencana kini meminta kata-kata orangnya, bukan nama modul atau nama
  Inggrisnya, dan panduan tidak lagi meminta agent menyebut modul yang
  disematkan. Belum diuji dengan model.
- **Uji**: 313 test Python dan 37 test tampilan lulus. Panduan tetap di
  bawah 20.000 karakter.
- **Dicoba di Chrome**, di server pemeriksaan atas salinan penyimpanan tahap
  4, tanpa model: kartu berhenti dengan tombol setuju lalu bekukan; teks agent
  berformat; bahasa Indonesia di panel kanan, contoh dan peta perubahan;
  draft kosong "Nothing built yet".
- **Berikutnya**: uji dari lingkungan kosong (hanya inti), lima langkah
  dengan satu usaha baru (Kemah Ceria), batas paling banyak $7, disetujui
  pemilik; rinciannya di `UJI_LINGKUNGAN_KOSONG.md`.
- **Uji dari lingkungan kosong, 4–6 Oktober 2026: berhenti sesudah langkah
  3** ($0,47 dari $7). Langkah 1–3 berhasil dan angkanya benar, tetapi modul
  jaminan keluar terputus dari modul sewa. Analisanya membawa pemilik ke
  keputusan desain yang lebih besar, dicatat di `DESIGN_NOTES.md` §15: empat
  jenis modul (core, pustaka umum, modul komunitas, aplikasi), peran pengguna
  yang dipisah, kepemilikan nama tanpa perluasan, dan kernel per usaha dengan
  graph bersama tetap di toko berkas. Rinciannya di `UJI_LINGKUNGAN_KOSONG.md`
  §8.
- **Langkah 1 dari urutan baru selesai, 6 Oktober 2026:** pustaka umum
  `@uniti/party`, `@uniti/item` dan `@uniti/transaction` v1 dibekukan;
  larangan menurunkan kelas milik modul lain (`kind_of_foreign_class`);
  compiler mengelompokkan satu catatan lebih jauh (`slot.slot`). 321 test
  Python dan 38 test tampilan lulus. Rinciannya di `PUSTAKA_UMUM.md` §9.
- **Langkah 2 selesai, 6 Oktober 2026:** aplikasi menjadi jenis tersendiri
  milik satu usaha; kernel menyatakan pemiliknya; membekukan dan memasang
  dipisah; formulir hanya mencatat lewat versi yang terpasang untuk hari itu.
  Rinciannya di `APLIKASI_USAHA.md` §9.
- **Langkah 3 selesai, 6 Oktober 2026:** hanya pemilik sebuah nama yang
  membekukan di bawahnya; yang pertama membekukan di bawah nama baru menjadi
  pemiliknya; pemilik menambah dan mencabut pemilik lain dengan tanggal; nama
  aplikasi adalah nama usahanya. Rinciannya di `PEMILIK_NAMA.md` §9.
- **Berikutnya** (urutan disetujui pemilik): panduan agent per peran; lalu
  uji lingkungan kosong diulang dalam dua babak (komunitas membuat, pemilik
  usaha menyusun).

### Irisan 5: Compiler dan generator tumbuh sesuai kebutuhan

Dari kebutuhan yang terbukti di 2.8, satu per satu, masing-masing dengan
syarat pertumbuhan di atas: saring berdasarkan nilai; daftar nilai tertutup;
slot bernilai banyak; ~~kunci lewat satu lompatan rujukan (pembayaran → faktur
→ pemasok)~~ **[dibangun 6 Oktober 2026, `PUSTAKA_UMUM.md` §9]**; aggregate di atas tabel hitungan; nilai dari dokumen induk
(tanggal baris); satu catatan yang menghasilkan catatan lain (posting);
konversi satuan dengan mencocokkan entity satuan itu sendiri.

### Sesudahnya (belum diurutkan)

- perubahan definisi lintas versi, dengan riwayat yang diputar ulang; laporan
  kecocokan yang membandingkan arti, bukan hanya nama
- penyelarasan yang dinyatakan orang (kelas atau predikat yang bersesuaian
  antar modul)
- penemuan standar universal dan isi `@uniti/core` sebagai bibit
- MCP baca untuk agent eksternal, mengambil ide dari 11 primitif P1

---

## 7. Keputusan

### Keputusan sementara (boleh direvisi setelah melihat hasilnya)

| Topik | Keputusan | Alasan |
|---|---|---|
| Branch | Branch baru `p2/refactor` dari keadaan sekarang; file yang tidak dipakai dihapus; kembali lewat tag | Perbaikan yang berguna (pengaman test DB, pembersihan istilah domain) sudah ada di keadaan sekarang |
| Versi modul | Setiap seal menghasilkan versi baru yang tidak bisa diubah. Import menyebut versi persis (`@community/x@v1`), tanpa rentang. Pindah ke versi baru = seal ulang modul pengimpor. Studio mengusulkan versi sealed terakhir secara otomatis. | Makna tidak pernah berubah diam-diam. Rentang versi bisa ditambahkan nanti; pin persis sulit ditambahkan belakangan. |
| Kernel | Satu kernel untuk semua modul dan data. Satu operational DB per aplikasi (turunan, boleh dibuang). | Integrasi antar modul terjadi lewat `slot_uri` di satu registry. Multi-kernel adalah soal isolasi, belum dibutuhkan, dan pintunya tetap terbuka karena semua komponen menerima DSN. |
| Isi core selama refactor | Core minimal: hanya `entity_class`, satu-satunya bagian core yang dijalankan mekanisme hari ini. Standarnya didesain di irisan 2.5. | Lima archetype percobaan lalu tidak mengubah perilaku gerbang, generator, atau compiler mana pun, dan masih membawa sisa istilah data uji. |
| Cara menggantinya | `core@v1` di-reset di branch ini, bukan di-seal sebagai v2. | Melanggar "versi sealed tidak pernah diedit", tetapi sah selama masih refactor dan belum ada yang bergantung padanya. Disetujui 18 September 2026. |
| `ontology_version` untuk fakta instance | **Versi aplikasi** (`@demo/stock@v1`), bukan modul pemilik tiap slot. | Sebuah fakta dinyatakan di bawah map yang sedang dilihat orangnya; satu aksi punya satu map. Modul pemilik tiap predikat tetap bisa ditemukan lewat store dari `slot_uri`, jadi tidak ada informasi yang hilang. Kebalikannya tidak benar: dari daftar modul, map yang dipakai saat menulis tidak bisa direkonstruksi. |
| Penanda data uji | Manifest modul boleh menyatakan `purpose:`. `seal` dan `register` membawanya ke `reason_code` intent; `load_facts` membawanya ke tiap intent yang ditulisnya. | Log dibaca orang yang tidak memegang store. Kalau isinya karangan, barisnya sendiri yang harus mengatakannya — bukan konvensi nama scope yang harus dihafal. |
| Peran setelah 2.8 | Kosakata bersama untuk menemukan dan menyambungkan modul, bukan penjumlah otomatis lintas modul. Aplikasi menyebut jelas apa yang dihitung dari modul mana. Disepakati 29 September 2026. | Putaran 2 irisan 2.8: setiap pengisi `Flow` berkompromi, penerimaan tercatat di dua modul terhitung dua kali, dan peran yang cukup kaya untuk mencegahnya akan menjadi model kanonik. |
| Studio | Agent mengusulkan, sistem menjamin, user menyetujui; contoh bisnis adalah kontrak yang wajib lulus sebelum seal; LinkML untuk bentuk data plus kosakata aturan Uniti, tanpa stack baru untuk sekarang. Disepakati 29 September 2026. | "Arah sesudah 2.8" di §6. |
| Agent | Satu agent pembangun ditambah akuntan independen yang menghitung angka contoh tanpa melihat graph; angka yang dikonfirmasi user dikunci; agent tidak punya alat seal; modul beraturan hitung wajib punya contoh. Pydantic AI dengan model per peran lewat konfigurasi, terbuka untuk penyedia lain dan model self-hosted; sekarang Gemini lewat Vertex AI. Disetujui 30 September 2026. | Irisan 4 di §6. |
| Riwayat agent | Riwayat percakapan dikirim utuh, termasuk setiap pemanggilan alat dan hasilnya. Biaya ditekan dengan cache penyedia (instruksi tetap, keadaan di pesan), alat yang menandai bacaan berulang, dan pemendekan bacaan usang hanya bila percakapan sangat panjang. Disetujui 3 Oktober 2026. | Agent yang lupa apa yang sudah dibaca dan dikerjakannya akan mengulanginya. Ini praktik umum sistem agent. |
| Bahasa agent ke pengguna | Luwes, mengikuti bahasa dan tingkat pemahaman orangnya; diajarkan sebagai prinsip, bukan aturan kaku. Disetujui 3 Oktober 2026. | Pengguna berbeda-beda; kata-kata bisnis disediakan lewat label. |
| Standar pencatatan | Bahasa Inggris untuk semua nama, judul, deskripsi dan contoh yang dicatat; label dalam bahasa pengguna untuk ditampilkan. Pola nama, deskripsi, satuan, arah angka, dan arti tanggal wajib. Pelanggaran yang bisa dicek mesin menghalangi seal. Prosedur sama untuk setiap agent, ditulis satu kali di sistem. Disetujui 3 Oktober 2026. | Tanpa catatan yang seragam, modul tidak saling menemukan dan maknanya tidak bisa disambungkan; modularitas gagal. |
| Kernel pengembangan | Dimulai kosong. Tidak ada lagi seed sintetis 200 assertion di sana; seed itu hanya dipakai `make check` di database test. | Semua yang tampil di penjelajah kernel harus berasal dari mekanisme yang bisa ditelusuri: seal, registrasi, atau isian form. |

### Masih terbuka

| # | Pertanyaan | Kapan | Rekomendasi |
|---|---|---|---|
| 1 | Teknologi UI | awal irisan 0b | API JSON Python (Starlette/uvicorn, sudah terpasang) yang dipakai bersama oleh UI dan agent, ditambah frontend React + TypeScript + Vite (Node 22 sudah ada). Graph, diff, dan chat streaming butuh UI interaktif yang sungguhan. |
| ~~2~~ | ~~Isi `ontology_version` pada assertion di dunia modular~~ | **dijawab di irisan 2** | **Versi aplikasi.** Lihat keputusan di bawah. |
| 3 | Isi `@uniti/core` | irisan 2.5 | **Peran, bukan kamus istilah.** Ukurannya terikat pada jumlah eksekutor, bukan jumlah domain: ~30 deklarasi saat dewasa. Rumus, tiga lapis (`core` / `@uniti/*` / ekosistem), dan aturan pertumbuhannya di `DESIGN_NOTES.md` §4. |
| ~~4~~ | ~~Penyedia LLM, stack, dan implementasi agent~~ | **dijawab 30 September 2026** | **Pydantic AI, terbuka untuk banyak penyedia dan model self-hosted; sekarang Gemini lewat Vertex AI.** Rancangannya di Irisan 4. |
| ~~5~~ | ~~Koherensi: dua modul mengisi peran yang sama~~ | **dijawab di irisan 2.5** | **Slot: tepat satu per kelas, kalau tidak ditolak** — ambiguitas di dalam satu kelas tidak bisa dipecahkan siapa pun selain penulisnya. **Kelas: berapa pun, semuanya ikut, dan rencananya menyebut yang mana** — gabungan itu bermakna (dua gudang, dua modul), dan sebuah subjek hanya anggota satu kelas sehingga tidak ada baris yang terhitung dua kali. Yang tersisa adalah bahaya *data*: satu peristiwa dinyatakan dua kali di bawah dua kosakata. Itu soal penyelarasan, bukan skema. |
| 6 | Satuan, dan waktu yang punya dua sumber tanpa penjaga | sesudah 2.5 | `DESIGN_NOTES.md` §10.4–10.5 |

---

## 8. Temuan selama berjalan

- **Compiler belum punya test yang mengeksekusi.** Test-nya hanya memeriksa rencana
  dan teks SQL; angka hasilnya dulu hanya dibuktikan lewat demo P1. Test eksekusi
  (log → operational DB → angka) ditambahkan di irisan 2.
- **Dua mekanisme penamaan di kernel.** Seed sintetis menamai entity lewat
  predikat `has_label`, sedangkan seal lewat registry `uniti:uri`. Seed sekarang
  memakai registry, sehingga pembaca kernel hanya mengenal satu cara.
- **Label versi di kernel.** Dengan banyak modul, `ontology_version = "v1"` tidak
  menunjuk apa pun. Seal ke dalam modul kini mencatat `@scope/name@vN`. Label untuk
  fakta yang ditulis lewat form (versi aplikasi atau versi modul pemilik slot)
  tetap diputuskan di irisan 2.
- **Import ke versi yang di-seal belakangan.** Seal kini menolak draft yang memin
  versi yang di-seal setelah draft itu sendiri.
- **`submit` mencatat `ontology_version = "v1"`,** label telanjang yang tidak
  menunjuk modul mana pun. Sekarang `read_map` membawa label `@scope/name@vN`
  dan form memakainya, sama seperti seal.
- **Compiler menerima kelas yang tidak ada dengan `ValueError` LinkML**, bukan
  `MapError`, sehingga API mengembalikan 500. `plan_for` sekarang menolak lebih
  dulu dengan daftar kelas yang ada.
- **`read_map` tanpa store memuat map separuh.** SchemaView meresolusi import
  secara malas, jadi map aplikasi terbaca tanpa satu pun kelas dari modul yang
  dipin, tanpa error. Sekarang ditolak.
- **Jebakan YAML 1.1 di map P1:** kunci `on:` tanpa tanda kutip di blok `convert`
  terbaca sebagai boolean `True`. Beberapa aturan di map demo P1 terkena ini tanpa
  ada yang menolaknya. Seal atau compiler harus menolaknya (irisan 1 atau 2).
- **Slot abstrak ikut terinduksi sebagai kolom.** Saat memverifikasi mekanisme
  peran: `class_induced_slots()` mengembalikan slot abstrak milik mixin
  (`amount`, `affects`) bersama slot konkret kelasnya, dengan `slot_uri = None`.
  Tanpa penanganan, generator memunculkan kolom hantu berisi NULL di setiap
  proyeksi dan medan kosong di setiap form. `columns()` dan `plan()` harus
  melewati slot yang `abstract: true` (irisan 2.5).
- **`slot_uri` tidak diwariskan dari slot induk** — terverifikasi. Itu yang
  membuat peran tidak pernah sampai ke kernel: log selamanya hanya berisi predikat
  konkret, jadi mengubah peran tidak membatalkan satu pun pernyataan.
- **Pindah ke peran tidak menulis satu pun assertion.** `@demo/catalog@v3` dan
  `@demo/inventory@v3` menyatakan kelasnya mengisi peran apa, dan kernel tidak
  perlu tahu: tidak ada predikat baru, tidak ada yang berubah. Itu properti yang
  membuat pengikatan ulang fakta yatim mungkin, dan sekarang ada test-nya.
- **Laporan kecocokan versi pertama membandingkan hal yang salah.** Ia merencanakan
  tiap versi di closure-nya sendiri, jadi dua rencana yang sama-sama benar terlihat
  cocok — termasuk `@demo/stock@v1` yang sebenarnya tidak bisa pindah sama sekali.
  Pertanyaannya adalah "aturan **saya**, modul **mereka**", jadi `fit` sekarang
  membangun map hipotetis di memori: dokumen versi ini dengan `imports` milik versi
  itu. Tidak pernah di-seal, tidak pernah ditulis; kalau ditolak, penolakan itulah
  jawabannya.
- **Test yang mencocokkan prosa adalah test yang menahan prosa.** Sembilan belas
  test mencocokkan potongan kalimat penolakan, jadi memperbaiki kata-kata sebuah
  penolakan berarti memperbaiki test — persis insentif yang salah untuk pesan
  yang paling sering dibaca orang. Sekarang semuanya mencocokkan `code`, dan
  beberapa di antaranya juga memeriksa `options`, yang justru memperkuat: sebuah
  test sekarang menyatakan *jawaban apa yang ditawarkan*, bukan bagaimana
  penolakannya dieja.
- **Gerbang berhenti; halaman tidak boleh.** Compiler menolak tabel pertama yang
  bermasalah dan diam soal sisanya — benar untuk gerbang yang sedang di tengah
  memancarkan SQL, tidak berguna untuk orang yang memutuskan apa yang harus
  diperbaiki. `check()` memisahkan keduanya tanpa menduplikasi satu pun aturan:
  pembacanya sama persis, hanya penolakannya dikumpulkan.
- **Penolakan store tidak lagi dibungkus seal.** Dulu import yang tidak bisa
  diresolusi keluar sebagai "bukan LinkML yang sah", yang menyembunyikan
  perbaikannya. Sekarang penolakan store lewat utuh, karena **siapa yang
  menolak** menentukan siapa yang bisa menjawabnya.
- **CLI seal tidak pernah memberi store.** Akibatnya sebuah draft yang memin
  modul jatuh sebagai `FileNotFoundError` di tengah LinkML, bukan sebagai
  penolakan. Ditemukan saat menguji pembaca terminal irisan 2.6; sekarang
  `main()` membangun `Store.from_env()` seperti generator dan compiler.
- **Sebuah peran tidak boleh dapat tabel.** Tidak ada apa pun di log yang pernah
  menjadi `Flow`, jadi tabel entity untuknya akan kosong. Akibatnya: medan yang
  ber-range peran (seperti `item` di `@rival`) membaca pilihannya dari log, bukan
  dari operational store. Form sudah mengatakannya di halaman. Perbaikannya kelak
  adalah pengikat `label` di core dengan generator sebagai eksekutornya — dan itu
  contoh "eksekutor dulu, peran diekstrak" yang ditemukan, bukan diantisipasi.

- **Janji core yang belum ditepati.** Laporan kesehatan menemukan sesuatu yang
  tidak dicari: core v2 menulis bahwa `Event` "dieksekusi compiler lewat
  `moment`", dan tidak ada kode yang membaca `moment`. Kedua pengisinya
  (`movement_happened_on`, `happened`) adalah istilah mati di setiap aplikasi.
  Deskripsi fixture `@demo/inventory@v3` juga keliru ("mengisi `moment` yang
  memberinya pembaca"). Core v2 sudah ter-seal, jadi teksnya tidak diubah;
  perbaikannya adalah eksekutor untuk `moment` — yaitu pertanyaan waktu yang
  masih terbuka (#6) — atau v3 yang tidak mengklaimnya.
- **"Mati" harus dibaca terhadap satu aplikasi.** Versi store-wide membuat
  `inv:movement_quantity` terlihat mati (versi terbaru `@demo/stock` memin
  saingan), padahal `@demo/stock@v2` membacanya. Katalog menjawab sisi
  store-wide: "dibaca oleh" di sana melihat semua versi ter-seal.
- **Mekanisme adalah pembaca.** Definisi pertama (hanya aturan compiler)
  menandai setiap kode identitas sebagai mati. Generator membaca identifier dan
  slot kelas; itu dihitung.
- **Lebar minimum Chrome headless** sekitar 500px, jadi tangkapan layar 390px
  terpotong di semua halaman, termasuk yang tidak berubah. Tata letak diperiksa
  di 520px. Navigasi area sekarang boleh membungkus baris.

- **Lubang dan penolakan adalah benda yang sama.** Rencana irisan 3 menyebut
  "validasi yang sama persis dengan `seal`" sebagai mekanisme tersendiri.
  Ternyata tidak ada yang perlu dibangun untuk itu: sebuah lubang *adalah*
  penolakan yang belum dipicu, dan `repairs[].options` dari irisan 2.6 sudah
  berisi himpunan jawaban yang sah. Yang harus ditambahkan cuma cara
  mengumpulkannya — dua pembaca `seal` diubah jadi generator. Kalau Studio
  dibangun sebelum 2.6, kita akan menulis penghitung lubang kedua.
- **Sebuah operasi tidak boleh menilai.** `bind` memeriksa bahwa slotnya milik
  draft ini dan pengikatnya memang pengikat; ia **tidak** memeriksa bahwa
  kelasnya mewajibkan pengikat itu. Yang begitu diserahkan ke pembacanya, dan
  muncul sebagai lubang pada bacaan berikutnya. Aturannya: operasi menolak yang
  tidak bisa ia kerjakan sama sekali, bukan yang membuat drafnya belum benar.
- **Modul dengan nol kelas bisa di-seal.** Itu benar dan sempat terlihat salah:
  sebuah modul kosong tidak melanggar apa pun. Ia muncul sebagai *open question*
  (`nothing_declared`), bukan penolakan.
- **Identitas predikat tetap ditulis, bukan diturunkan.** Studio menawarkan
  `<prefix>:<nama_slot>` sebagai usulan dan menuliskannya **harfiah** ke berkas;
  `rename_slot` mempertahankannya. Jadi prinsip "slot_uri tidak diturunkan dari
  nama" tetap utuh sambil `add_slot` tetap satu langkah.
- **`from components.studio import holes` mengambil fungsinya, bukan modulnya.**
  `__init__.py` yang mengekspor fungsi bernama sama dengan berkasnya menimpa
  nama submodulnya. Berkasnya dinamai ulang jadi `read.py`, sejajar dengan
  `components/modules/read.py`.
- **Apa yang dibaca Studio dari sebuah penolakan.** Langkah yang menjawab
  `binding_unfilled` perlu tahu kelas dan pengikatnya, dan itu ada di `where`
  (`Kelas.pengikat`) — bukan sebagai medan tersendiri. Menambah medan yang
  hanya dipakai Studio berarti medan yang hanya dipelihara Studio; bentuk
  `where` dipegang oleh test.

- **Mekanisme yang benar tidak membuat layar yang bisa dipakai.** Tiga kolom
  pertama memenuhi setiap syarat "selesai" irisan 3.1 dan tetap tak terbaca:
  setiap kata di layar — *class*, *slot*, *binding*, `binding_unfilled`,
  "fills Flow" — adalah kata kompiler, satu fakta muncul tiga kali dalam tiga
  kosakata, dan tidak ada gambar sama sekali padahal yang dibangun adalah
  graph. Syarat "selesai" untuk irisan UI ditambah: bisa dibaca tanpa kamus.
- **Kata awam yang domain-agnostic harus dibaca, bukan ditulis.** Menerjemahkan
  `moment` jadi "kapan" di kode adalah menanam istilah satu peran ke dalam
  Studio. Yang dipakai halaman adalah `description` pengikat itu sendiri —
  "When this event happened." dari `@uniti/core` — jadi pertanyaannya berbunyi
  *"Which field of Wastage says when this event happened?"*, dan peran yang
  dibuat orang lain besok terbaca sama baiknya. Untuk itu `_bindings` mulai
  membawa `title`. Satu-satunya kamus yang ditulis di kode adalah tipe kolom
  (`decimal` → "number"), dan itu himpunan tertutup milik compiler, bukan
  milik subjek siapa pun.
- **Peta bukan katalog.** Yang layak digambar di sebelah kelas Anda adalah apa
  yang Anda tunjuk, lalu apa yang *itu* tunjuk — keterjangkauan, bukan seluruh
  isi modul yang dipin. `@demo/wastage` menunjuk Ingredient, dan Category serta
  Supplier ikut karena Ingredient menamai keduanya; sisanya tidak. Peran tidak
  pernah jadi node: peran adalah bentuk yang diklaim sebuah kelas, digambar
  *pada* kelas itu.
- **Target sebuah tarikan dihitung dari koordinat, bukan dari hover.** Versi
  pertama melacak node yang sedang dilewati lewat `onPointerEnter`. Itu gagal
  diuji dan akan gagal di layar sentuh, yang tidak punya hover sama sekali;
  tarikan cepat juga bisa melewati sebuah kotak tanpa pernah memasukinya.
  Sekarang node tujuan dicari dari titik lepas.
- **Ekstensi Chrome tidak tersambung, jadi kanvasnya diuji lewat iframe.**
  Halaman sekali pakai yang memuat Studio dalam iframe dan menembakkan
  `PointerEvent` sintetis: klik node, tarik garis, jawab pertanyaan. Yang
  ditemukan olehnya adalah bug hover di atas. Catatan: `pointerenter` tidak
  merambat, jadi React tidak pernah melihatnya — yang satu ini keterbatasan
  probe, tapi ia menunjuk ke masalah yang nyata.

- **Jebakan YAML `on:` muncul lagi.** Kunci tanggal catatan di contoh semula
  bernama `on`, dan YAML membacanya sebagai `true`. Namanya diganti `when`, dan
  test memastikan berkas yang masih memakai `on:` ditolak, tidak diam-diam
  kehilangan tanggalnya.
- **Pintu form mengandaikan log yang sudah dimulai.** `submit` tidak pernah
  mendaftarkan predikat penamaan `uniti:uri`, karena di log sungguhan seal
  selalu sudah melakukannya. Log sementara untuk contoh dimulai dengan langkah
  yang sama seperti log mana pun: predikat itu mendaftarkan dirinya sendiri.
- **Log sementara aman karena diperiksa, bukan karena diandaikan.** Tiga tabel
  sementara menutupi tabel kernel hanya untuk satu koneksi, di dalam transaksi
  yang selalu dibatalkan. Sebelum dan sesudah setiap contoh diperiksa bahwa
  nama tabelnya menunjuk ke tempat yang benar. Kalau tabel sementara tertinggal,
  tulisan berikutnya di koneksi itu (misalnya seal) akan hilang tanpa jejak,
  jadi yang itu dibuat berhenti keras, bukan menjadi penolakan.
- **Membaca draft sekarang butuh database untuk contohnya.** Tanpa koneksi,
  contoh hanya didaftar, tidak dijalankan, dan draft tidak disebut siap seal:
  contoh yang tidak dijalankan adalah contoh yang jawabannya belum diketahui.

---

## 9. Status

| Irisan | Status |
|---|---|
| 0a | selesai: file lama dihapus, fondasi lepas dari linter, istilah domain di test dinetralkan (compiler punya fixture netral sendiri), Makefile dan README ditulis ulang; 82 test lulus, replay identik |
| 0b | selesai, menunggu Anda melihatnya: API baca kernel (`components/api`), aplikasi web (`web/`) dengan penjelajah kernel dan bidang jam; seed sintetis dinetralkan dan menamai entity lewat registry `uniti:uri`; 96 test lulus |
| 1.5 | selesai: core dikecilkan ke `entity_class` dan di-reset sebagai v1, modul contoh lepas dari archetype, kernel pengembangan dimulai kosong |
| 1 | selesai, menunggu Anda melihatnya: store modul berversi (`components/modules`), import dipin dan diperiksa seal, `@uniti/core` di-seal sebagai v1, linimasa + detail versi + diff di aplikasi; 110 test lulus |
| 2 | selesai, menunggu Anda melihatnya: aplikasi sebagai versi yang memin (`components/api/application.py`), compiler dieksekusi lintas modul dengan test angka, pintu tulis massal `scripts/load_facts.py`, form yang menulis ke kernel, dan penelusuran satu sel sampai ke pernyataan yang menopangnya; graph kelas lintas modul + tabel proyeksi + penjelasan aturan per kolom di aplikasi web; fixture diganti tiga modul demonstrasi yang menandai dirinya di graph dan di kernel; 134 test lulus |
| 2.5 | selesai, menunggu Anda melihatnya: `@uniti/core@v2` membawa peran (`Thing`, `Resource`, `Event`, `Flow`) dan tiga pengikat; seal menolak kelas yang mengaku peran tanpa memenuhinya, dan menolak closure yang memuat satu modul di dua versi; compiler meresolusi slot abstrak ke predikat konkret tiap kelas pengisi; `@rival/stock-moves@v1` sebagai modul saingan yang menulis ulang semua namanya; `@demo/stock@v3` memindahkan pin tanpa mengubah satu baris aturan dan menghasilkan angka identik; panel peran + laporan kecocokan di aplikasi web; 153 test lulus |
| 2.6 | selesai, menunggu Anda melihatnya: `components/refusal/` — penolakan sebagai data dengan kalimat yang diturunkan darinya, 62 kode tertutup, dan `repairs[].options` yang dihitung dari graph; empat gerbang menyebut dirinya; `check()` mengumpulkan semua penolakan sekaligus dan menerima map yang belum di-seal; API mengirim strukturnya di samping kalimatnya; satu kartu penolakan di semua permukaan, dan laporan kecocokan membawa penolakannya utuh; test penolakan sekarang mencocokkan `code`, bukan prosa; 163 test lulus |
| 2.7 | selesai, menunggu Anda melihatnya: katalog terhitung yang bisa dikueri (`components/modules/catalogue.py`) dan enam diagnosa kesehatan per aplikasi (`components/modules/health.py`), lewat CLI, API, dan area Catalogue di aplikasi web; `inv:movement_happened_on` ditemukan sebagai istilah mati di `@demo/stock@v2` — 24 pernyataan, mengisi `moment`, nol pembaca — dan sebagai fakta yang tak terlihat di `@demo/stock@v3`; 173 test lulus |
| 3.1 | selesai, menunggu Anda melihatnya: draft sebagai berkas yang hanya berubah lewat 24 operasi tertutup (`components/studio/`), lubang yang dihitung dari pembaca gerbang itu sendiri — `uri_refusals` dan `role_refusals` jadi generator supaya bisa dikumpulkan — dan lima pertanyaan terbuka yang tidak ditolak siapa pun; `draft.txt` menjadi transkrip seal; CLI, API, dan area Studio di aplikasi web; satu aplikasi lengkap dengan aggregate, parameter dan expression dibangun dari nol tanpa satu baris YAML dan diterima `seal`; 191 test lulus |
| 3.1 UI | dibangun ulang setelah Anda melihat yang pertama dan tidak mengerti sama sekali: tiga kolom istilah kompiler diganti **peta** (`web/src/graph.tsx`) — node jenis hal, garis relasi, yang dipijak samar di atas, klik untuk panel, tarik untuk membuat relasi; pertanyaan dirangkai dari deskripsi pengikatnya sendiri sehingga tetap domain-agnostic; `state()` menambah `borrowed` (keterjangkauan, bukan seluruh yang dipin); semua kosakata mesin pindah ke satu tutup *Behind the scenes*; 191 test lulus |
| 2.8 | ditutup 29 September 2026: putaran 1 tidak menguji peran (rancangan tes); putaran 2 dihentikan setelah kelima modul ditulis dengan peran wajib, dan sudah menjawab: peran bukan penjumlah otomatis lintas modul, komposisi eksplisit menjadi cara resmi; perbaikan F1–F4 tetap di kode, 217 test lulus; rincian di `COMPOSITION_EXPERIMENT.md` |
| 3.2 | selesai 29 September 2026: bentrok nama ditolak; predikat dan kelas dicatat dengan URI penuh; enum, `required` per kelas, dan `multivalued` dibuka di Studio dan ditegakkan; range tak dikenal ditolak; sintaks rumus diajarkan; 226 test lulus; rincian di bagian "Irisan 3.2" |
| 3.3 | selesai 29 September 2026: contoh bisnis dijalankan di log sementara lewat pintu form dan compiler yang sama; Studio menjalankannya setiap kali draft dibaca dan seal menolak bila ada yang gagal; tujuh langkah Studio baru; aplikasi demo membawa dua contoh; 239 test lulus; rincian di bagian "Irisan 3.3" |
| 4 | berjalan, dipecah lima tahap: 4.1 (penjaga kontrak) dan 4.2 (alat agent dan panduan) selesai 30 September 2026; 4.3 (agent sungguhan di Gemini lewat ADC `us`, akuntan, batas biaya, pengawasan setiap panggilan, eval) selesai; 4.4 (Studio di sekitar agent) selesai dalam tiga bagian, 2 Oktober 2026; evaluasi dan penyetelan agent berjalan sejak 2 Oktober 2026 (eval mesin 8 dari 10 lulus, sesi realistis 1 benar tetapi belum bertahap); rencana empat tahap penyetelan disetujui 3 Oktober 2026 (standar pencatatan, riwayat utuh yang murah, agent bertahap dengan bahasa luwes, sesi realistis diulang); tahap penyetelan 1 (standar pencatatan), 2 (riwayat utuh yang murah), 3 (agent bertahap, bahasa yang luwes) dan 4 (tiga sesi realistis: semuanya benar dan bertahap, $0,75 total; nama teknis di rencana dan beberapa hal tampilan masih harus diperbaiki) selesai 3 Oktober 2026; temuan sesi diperbaiki 4 Oktober 2026 (kartu berhenti yang menaruh contoh di depan orangnya, draft kosong, tampilan, tidak ada yang dibangun sebelum rencana disetujui); 313 test Python dan 37 test tampilan lulus; uji dari lingkungan kosong berhenti sesudah langkah 3 pada 6 Oktober 2026 ($0,47) dan membawa keputusan desain di `DESIGN_NOTES.md` §15 (empat jenis modul, peran, kepemilikan, kernel per usaha); berikutnya pustaka umum, aplikasi sebagai jenis tersendiri, panduan agent per peran, uji lingkungan kosong diulang dalam dua babak, ujian akhir eval mesin 10 × 3, perbandingan akuntan Flash dan Pro, dan 4.5 (PT Maju dibangun ulang lewat agent) |
| 5 | belum dimulai: compiler dan generator tumbuh sesuai kebutuhan |
