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

**Disimpan sebagai referensi, tidak dijalankan dan tidak dites:** `components/agent/*`
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
  yang benar.
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

- **Mekanisme:** `MapError` membawa struktur (`code`, `where`, `expected`, `got`,
  `repairs`), bukan cuma prosa. Satu sumber, tiga pembaca: kalimat untuk manusia,
  tombol perbaiki untuk Studio, hasil tool untuk agent.
- **Selesai jika:** setiap penolakan di layar datang bersama perbaikannya.

### Irisan 2.7: Katalog dan kesehatan graph

- **Mekanisme:** katalog yang dihitung dari isi ter-seal (peran, modul, kelas,
  siapa mengisi apa) — bisa dikueri, bukan dokumen. Enam diagnosa: istilah mati,
  kolom hampa, kelas kosong, peran tak terisi, pin tertinggal, fakta yatim.
- **Selesai jika:** `inv:movement_happened_on` muncul sebagai istilah mati — 245
  pernyataan, nol pembaca — tanpa ada yang menuliskannya.

**2.6 dan 2.7 mendahului Studio.** Permukaan jelajah Studio adalah katalog, dan
penyuntingnya digerakkan penolakan.

### Irisan 3: Studio manual (tanpa LLM)

- **Mekanisme:**
  - Operasi draft yang deterministik: tambah, ubah, hapus, rename kelas, slot,
    dan aturan.
  - Validasi yang sama persis dengan `seal`.
  - Katalog dari registry kernel.
- **Yang dilihat:**
  - editor draft lewat form
  - validasi langsung
  - diff draft terhadap versi terakhir
  - seal dengan konfirmasi
- **Selesai jika:** Anda bisa membuat modul lengkap tanpa menulis YAML, dan
  setiap penolakan menjelaskan dirinya.

### Irisan 4: Agent di Studio

- **Mekanisme:**
  - Agent tipis. Tool-nya adalah operasi draft yang sama dengan irisan 3, plus
    inspect dan *usulan* seal yang wajib dikonfirmasi manusia.
  - Sesi dan riwayat lengkap (termasuk tool call) disimpan di server.
  - Streaming event.
  - Percakapan menjadi transcript seal.
- **Yang dilihat:** chat di samping editor yang sama. Setiap tool call tampil
  sebagai perubahan draft saat itu juga.
- **Selesai jika:** modul yang dibuat lewat chat identik secara mekanisme dengan
  modul yang dibuat manual.

### Irisan 5: Uji integrasi oleh Anda

Modul pertama dibuat lewat chat, lalu modul kedua dibuat lewat chat dan mengimpor
yang pertama. Hasilnya harus menjadi satu graph, satu aplikasi, dan proyeksi yang
menghitung lintas modul.

### Sesudahnya (belum diurutkan)

- perluasan generator dan compiler: tipe data, relasi, koleksi, skema
- perubahan definisi lintas versi, dengan riwayat yang diputar ulang
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
| Kernel pengembangan | Dimulai kosong. Tidak ada lagi seed sintetis 200 assertion di sana; seed itu hanya dipakai `make check` di database test. | Semua yang tampil di penjelajah kernel harus berasal dari mekanisme yang bisa ditelusuri: seal, registrasi, atau isian form. |

### Masih terbuka

| # | Pertanyaan | Kapan | Rekomendasi |
|---|---|---|---|
| 1 | Teknologi UI | awal irisan 0b | API JSON Python (Starlette/uvicorn, sudah terpasang) yang dipakai bersama oleh UI dan agent, ditambah frontend React + TypeScript + Vite (Node 22 sudah ada). Graph, diff, dan chat streaming butuh UI interaktif yang sungguhan. |
| ~~2~~ | ~~Isi `ontology_version` pada assertion di dunia modular~~ | **dijawab di irisan 2** | **Versi aplikasi.** Lihat keputusan di bawah. |
| 3 | Isi `@uniti/core` | irisan 2.5 | **Peran, bukan kamus istilah.** Ukurannya terikat pada jumlah eksekutor, bukan jumlah domain: ~30 deklarasi saat dewasa. Rumus, tiga lapis (`core` / `@uniti/*` / ekosistem), dan aturan pertumbuhannya di `DESIGN_NOTES.md` §4. |
| 4 | Penyedia LLM untuk agent | irisan 4 | — |
| 5 | Koherensi: dua modul mengisi peran yang sama → hitung ganda | irisan 2.5 | `DESIGN_NOTES.md` §10.3. Harus dijawab sebelum ada yang rugi. |
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

---

## 9. Status

| Irisan | Status |
|---|---|
| 0a | selesai: file lama dihapus, fondasi lepas dari linter, istilah domain di test dinetralkan (compiler punya fixture netral sendiri), Makefile dan README ditulis ulang; 82 test lulus, replay identik |
| 0b | selesai, menunggu Anda melihatnya: API baca kernel (`components/api`), aplikasi web (`web/`) dengan penjelajah kernel dan bidang jam; seed sintetis dinetralkan dan menamai entity lewat registry `uniti:uri`; 96 test lulus |
| 1.5 | selesai: core dikecilkan ke `entity_class` dan di-reset sebagai v1, modul contoh lepas dari archetype, kernel pengembangan dimulai kosong |
| 1 | selesai, menunggu Anda melihatnya: store modul berversi (`components/modules`), import dipin dan diperiksa seal, `@uniti/core` di-seal sebagai v1, linimasa + detail versi + diff di aplikasi; 110 test lulus |
| 2 | selesai, menunggu Anda melihatnya: aplikasi sebagai versi yang memin (`components/api/application.py`), compiler dieksekusi lintas modul dengan test angka, pintu tulis massal `scripts/load_facts.py`, form yang menulis ke kernel, dan penelusuran satu sel sampai ke pernyataan yang menopangnya; graph kelas lintas modul + tabel proyeksi + penjelasan aturan per kolom di aplikasi web; fixture diganti tiga modul demonstrasi yang menandai dirinya di graph dan di kernel; 134 test lulus |
| 2.5 | belum dimulai — arah dan detail teknisnya dicatat di `DESIGN_NOTES.md` |
| 2.6 | belum dimulai |
| 2.7 | belum dimulai |
| 3 | belum dimulai |
| 4 | belum dimulai |
| 5 | belum dimulai |
