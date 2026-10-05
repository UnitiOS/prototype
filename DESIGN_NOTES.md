# Catatan desain — lapisan makna, core, dan Studio

> **Status: catatan, bukan aturan.**
>
> Isi dokumen ini adalah hasil satu percakapan panjang pada **18 September 2026**
> tentang apa itu `@uniti/core`, seberapa besar ia boleh tumbuh, dan bagaimana
> Studio serta agent memakai graph. Ia ditulis supaya kita tidak perlu mengulang
> diskusi itu dari nol, bukan supaya ada yang mengikatnya.
>
> - **Tidak mengikat.** Kalau kode membuktikan sebaliknya, kode yang benar.
> - **Bukan spesifikasi.** Tidak ada di sini yang wajib dibangun.
> - **Akan salah di beberapa tempat.** Bagian yang sudah diverifikasi terhadap
>   kode ditandai ✓; sisanya adalah penilaian.
> - **Sebagian sudah dibangun.** Irisan 2.5 dan 2.6 dikerjakan pada 18 September
>   2026, irisan 2.7 pada 19 September 2026, dan irisan 3.1 — separuh pertama
>   Studio — pada 23 September 2026, layarnya dibangun ulang sebagai peta pada
>   hari yang sama. Semuanya mengubah beberapa hal di sini dari usulan menjadi
>   kode, dan §8.2 justru dibantah olehnya. Yang sudah berjalan ditandai
>   **[dibangun]**, dan pertanyaan yang terjawab olehnya ditandai di §12.
> - **§15 ditambahkan 6 Oktober 2026**, sesudah uji lingkungan kosong: empat
>   jenis modul, peran pengguna, kepemilikan, dan kernel per usaha. Ia
>   menggantikan tiga lapis di §4.3 dan arti **aplikasi** di §14.
> - **Beda dari `REFACTOR_P2.md`**, yang merupakan dokumen kerja sementara dan
>   dihapus setelah refactoring selesai. Yang ini hidup lebih lama karena isinya
>   tentang bentuk sistemnya, bukan tentang urutan pengerjaannya.

---

## 0. Cara membaca

Bagian **1–3** adalah diagnosa dan mekanisme yang diusulkan — bagian yang paling
siap dikerjakan. Bagian **4–6** adalah aturan pertumbuhan: jawaban untuk
"seberapa besar core". Bagian **7–8** tentang bagaimana pengetahuan itu sampai ke
manusia dan agent. Bagian **9–14** adalah rencana, jebakan, hal yang sengaja
tidak dilakukan, pertanyaan terbuka, dan istilah. Bagian **15** adalah
keputusan tentang jenis modul, siapa memakainya, siapa memilikinya, dan di mana
data setiap usaha tinggal.

Kalau Anda hanya punya waktu untuk dua bagian: **§3.2** (contoh penukaran modul,
lengkap) dan **§11** (yang sudah diputuskan untuk tidak dilakukan).

---

## 1. Di mana kita sekarang

Empat temuan dari kode per commit `626f4b1`. Semuanya bisa diperiksa ulang.

**1.1 Core hari ini adalah satu slot.** `packages/@uniti/core/v1.yaml` berisi
`entity_class` dan `classes: {}`. Itu bukan kekurangan — itu hasil aturan yang
ditegakkan di `0e4666a` ("hanya yang dieksekusi mekanisme"). Tapi artinya core
belum menjadi standar apa pun; ia baru satu predikat bersama.

**1.2 Aplikasi memanggil nama privat modul lain, lima kali.** Di
`@demo/stock/v1.draft.yaml`:

| yang ditulis aplikasi | milik siapa |
|---|---|
| `over: StockMovement` | `@demo/inventory` |
| `sum: movement_quantity` | `@demo/inventory` |
| `by: {stock_ingredient: movement_ingredient}` | `@demo/inventory` |
| `range: Ingredient` | `@demo/catalog` |
| `slot: ingredient_reorder_level` | `@demo/catalog` |

Ganti modul inventory dan tiga baris pertama mati. Ini bukan `import`, ini
`#include`.

**1.3 Modul inventory terikat ke atas, bukan cuma aplikasi yang terikat ke
bawah.** `@demo/inventory` menulis `range: Ingredient` — nama kelas milik katalog
toko roti. Jadi modul itu **tidak bisa dipakai pabrik tekstil sama sekali**, bukan
canggung tapi mustahil. Ada dua masalah, bukan satu.

**1.4 `movement_happened_on` dinyatakan 245 kali dan dibaca nol aturan.**
`movement_reason` mengakuinya sendiri di deskripsinya: *"Read by nobody yet"*.
Tanpa aturan, graph mengumpulkan istilah mati tanpa batas dan tidak ada yang bisa
memberi tahu kita yang mana.

---

## 2. Diagnosa

> **Sistem modul ini punya `import`, tapi tidak punya `interface`.**

Setiap rujukan menunjuk ke nama konkret. Yang hilang bukan kamus istilah bersama;
yang hilang adalah **polimorfisme** — kemampuan menulis aturan terhadap sesuatu
yang implementasinya belum diputuskan.

Titik tengah antara fleksibilitas dan aturan, dirumuskan supaya mesin bisa
menegakkannya:

> **Modul bebas di dalam, terikat di tepinya.**
> Tunjuk ke *peran* kalau ingin bisa diganti. Tunjuk ke *nama* kalau memang ingin
> spesifik. Tugas core: membuat yang pertama mungkin — bukan membuat yang kedua
> ilegal.

Core yang mendikte "sebuah Item itu begini" adalah *canonical data model*. Jalan
itu sudah dicoba dan gagal berkali-kali (ISO 15926, OAGIS, CIM era SOA): tumbuh
oleh komite, mengantisipasi kebutuhan yang belum ada, dan setelah beberapa tahun
tidak bisa diubah siapa pun. Core yang mendikte **kewajiban** — "untuk bisa
dijumlahkan sepanjang waktu, sebuah kelas harus menunjuk satu jumlah, satu momen,
dan satu hal yang dipengaruhi" — tidak punya masalah itu, karena ia tidak bicara
tentang dunia; ia bicara tentang apa yang dibutuhkan mekanisme agar bisa jalan.

Disiplin yang sama persis dengan kernel: 3 tabel, 15 kolom, tanpa domain, tapi
mendrive skema apa pun. **Core adalah kernel-nya lapisan makna.**

---

## 3. Mekanisme yang diusulkan: peran

### 3.1 Bentuknya

Core mendeklarasikan **peran** sebagai kelas abstrak dan **pengikat** sebagai slot
abstrak. Modul mengisinya dengan nama-namanya sendiri.

```yaml
# @uniti/core v2 — sketsa
classes:
  Thing:    {abstract: true, slots: [entity_class]}
  Resource: {is_a: Thing, abstract: true, mixin: true}
  Event:    {is_a: Thing, abstract: true, mixin: true, slots: [moment]}
  Flow:     {is_a: Event, abstract: true, mixin: true, slots: [amount, affects]}
slots:
  entity_class: {designates_type: true}      # sudah ada di v1
  moment:  {abstract: true, range: date}
  amount:  {abstract: true, range: decimal}
  affects: {abstract: true, range: Resource}
```

Modul mengisi peran lewat `mixins:` (bukan `is_a:`) supaya satu kelas bisa
mengisi lebih dari satu peran — misalnya sebuah `StockMovement` yang kelak juga
menjadi `Fulfilment` dari sebuah komitmen. ✓ *terverifikasi: `class_descendants`
mengikuti mixin secara default.*

### 3.2 Contoh lengkap: penukaran modul

**Modul A** (`@demo/inventory@v3`):

```yaml
classes:
  StockMovement:
    mixins: [Flow]
    slots: [entity_class, movement_code, movement_quantity,
            movement_ingredient, movement_location, movement_at]
slots:
  movement_quantity:   {is_a: amount,  slot_uri: inv:movement_quantity, range: decimal}
  movement_ingredient: {is_a: affects, slot_uri: inv:movement_ingredient, range: Resource}
  movement_at:         {is_a: moment,  slot_uri: inv:movement_at, range: date}
```

**Modul C** (`@rival/stock-moves@v1`) — ditulis tanpa melihat nama-nama A:

```yaml
classes:
  Movement:
    mixins: [Flow]
    slots: [entity_class, move_ref, qty_delta, item, at]
slots:
  qty_delta: {is_a: amount,  slot_uri: rv:qty_delta, range: decimal}
  item:      {is_a: affects, slot_uri: rv:item, range: Resource}
  at:        {is_a: moment,  slot_uri: rv:at, range: date}
```

**Aplikasi** — tidak menyebut satu pun nama privat dari keduanya:

```yaml
quantity_on_hand:
  annotations:
    aggregate:
      value:
        over: Flow                          # dulu: StockMovement
        sum: amount                         # dulu: movement_quantity
        by: {stock_ingredient: affects}     # dulu: movement_ingredient
```

Lima nama privat (§1.2) turun jadi satu. Yang tersisa —
`slot: ingredient_reorder_level` — memang **harus** tetap spesifik: itu keputusan
bisnis si pemilik toko, bukan konsep bersama. Itulah "bebas di dalam, terikat di
tepinya" yang terlihat.

**Masalah tekstil hilang tanpa mesin tambahan.** Modul generik cukup *tidak
menyempitkan*: biarkan `affects` ber-`range: Resource`. Pabrik tekstil menulis
`Fabric` dengan `mixins: [Resource]` dan penelusuran yang sudah ada menemukannya.
Tidak perlu generics, tidak perlu parameter tipe. **Subsumsi sudah
melakukannya.** Modul yang menyempitkan ke `Ingredient` dengan sendirinya
menyatakan dirinya modul roti — itu pun sah, asal disengaja.

### 3.3 Kenapa ini murah: yang sudah ada di kode

Ini alasan utama merekomendasikan arah ini — bukan karena elegan, tapi karena
hampir seluruhnya sudah terpasang.

| yang dibutuhkan | statusnya |
|---|---|
| kelas abstrak, mixin, slot `is_a`/`abstract` | ✓ bawaan LinkML |
| `over: Flow` menemukan baris `StockMovement` | ✓ `_source_cte` sudah pakai `class_descendants` (`compile.py:540`) |
| `range: Resource` menemukan `ingredient_reorder_level` | ✓ `_read_parameter` sudah menelusuri turunan (`compile.py:313`) |
| `sum: amount` → slot konkret | `slot_descendants()` ada; perlu ~15 baris di `named_slot` (`compile.py:159`) |
| menolak peran yang tak dipenuhi | perlu ditulis, di `seal` |

Resolusi dan kedua penolakannya muat dalam empat baris — ✓ terverifikasi:

```python
def fillers(view, class_name, role_slot):
    below = set(view.slot_descendants(role_slot)) - {role_slot}
    mine  = {str(s.name) for s in view.class_induced_slots(class_name)}
    return sorted(below & mine)
# []           -> tolak: "Flow menuntut amount; StockMovement tak punya pengisinya"
# ['a','b']    -> tolak: "dua slot mengisi amount: a, b — sebutkan yang mana"
# ['qty']      -> pakai slot_uri-nya
```

### 3.4 Dua invarian yang tidak boleh dilanggar

**(a) Kernel tidak pernah tahu soal peran.** ✓ Terverifikasi: `slot_uri` **tidak**
diwariskan dari slot induk — `movement_quantity` tetap `inv:movement_quantity`,
sementara `amount` punya `slot_uri = None`. Jadi log selamanya hanya berisi
predikat konkret.

Konsekuensinya besar dan bagus: **mengubah peran tidak membatalkan satu pun
pernyataan di log.** Itu sebabnya mengikat ulang fakta yatim (§7.4) bisa bekerja,
dan itu sebabnya mencopot modul tidak menghancurkan data.

**(b) Slot abstrak adalah lubang, bukan kolom.** ✓ Ini jebakan yang baru ketahuan
saat verifikasi dan pasti akan memakan waktu kalau tidak dicatat:
`class_induced_slots('StockMovement')` mengembalikan **empat** slot — dua konkret
milik modul, **dan dua abstrak** (`amount`, `affects`) yang ikut terwarisi dari
mixin, dengan `slot_uri = None`.

Tanpa penanganan, generator akan memunculkan kolom hantu berisi NULL di setiap
proyeksi dan medan kosong di setiap form, lalu penjaga `if not slot.slot_uri`
yang ada sekarang akan menolaknya. Aturannya: **`columns()` dan `plan()` melewati
slot yang `abstract: true`.**

---

## 4. Seberapa besar core

### 4.1 Rumusnya

> **|core| = fungsi dari jumlah eksekutor, bukan jumlah domain.**

Core tidak tumbuh karena ada industri baru. Ia tumbuh hanya kalau ada *mekanisme*
baru — sesuatu yang bisa dihitung compiler dari sebuah log. Daftar itu pendek,
karena ia daftar hal yang bisa dilakukan aritmatika di atas catatan, bukan daftar
hal yang dilakukan bisnis.

| eksekutor | punya? |
|---|---|
| aggregate (jumlah/cacah/min/maks) | ya, baru `sum` |
| parameter (satu fakta tentang kunci) | ya |
| expression (aritmatika antar kolom) | ya |
| conversion (faktor/satuan) | sebagian (`convert`) |
| allocation (membagi satu jumlah menurut basis) | belum |
| schedule (penyusutan, akrual, langganan) | belum |
| matching (janji ↔ pemenuhan: PO↔terima↔faktur) | belum |
| duality (setiap aliran punya dua sisi) | belum |
| lifecycle (draf→disetujui→diposting) | belum |
| constraint (tidak boleh negatif; di atas X butuh persetujuan) | belum |
| permission (siapa boleh menyatakan apa) | belum |
| derivation-of-derivation (tabel di atas tabel) | belum |

Dua belas, mungkin lima belas. Masing-masing menuntut 2–3 deklarasi.

> **Core dewasa ≈ 8–12 kelas peran + 15–25 slot pengikat ≈ 30 deklarasi.
> Selamanya.**

Pembanding: REA — model ekonomi lengkap, sudah 40 tahun, jadi ISO/IEC 15944-4 —
punya 6 kelas dan 6 relasi. Trait inti Rust yang mengikat koherensi: ~30.
Interface Go yang menopang seluruh ekosistemnya bisa dihitung jari, dan kalimat
mereka layak ditempel di dinding: *"the bigger the interface, the weaker the
abstraction."*

### 4.2 Koreksi penting terhadap "tidak apa-apa core agak besar"

Semangatnya benar — jangan kelaparkan core secara artifisial; peran yang dituntut
eksekutor memang tempatnya di core. Tapi anak kalimat "yang penting bisa
memetakan **semuanya**" perlu diluruskan:

> **Core tidak memetakan semuanya. Yang memetakan semuanya adalah ekosistem
> modul.** Kalau core harus tumbuh supaya sebuah industri bisa dipetakan,
> mekanisme peran gagal — karena seluruh intinya adalah industri baru masuk lewat
> modul, bukan lewat core.

Asimetri yang membuat ini bukan soal selera:

> **Modul buruk bisa diganti. Core buruk tidak bisa diganti siapa pun, selamanya,
> karena semua orang mem-pin-nya.**

Seluruh §3 ada untuk membuat modul bisa diganti. Tidak ada mekanisme setara untuk
core. Anggaran kesalahan core adalah nol.

**Rasio biaya.** Satu deklarasi di modul: satu baris YAML. Satu deklarasi di core:
satu eksekutor, satu penolakan di seal, satu baris di laporan kecocokan, satu
pertanyaan yang harus diajukan Studio, satu paragraf yang harus dibaca agent, dan
— kalau salah — migrasi untuk semua orang. **Sekitar 50–100× lebih mahal.** Itu
governor-nya.

### 4.3 Tiga lapis, tiga laju — sengaja berbeda

| lapis | isi | besar | laju | bisa di-fork? |
|---|---|---|---|---|
| **core** | peran + kewajiban; dibaca eksekutor | ~30 deklarasi | 1–2/tahun | **tidak pernah** |
| **`@uniti/*`** | pustaka standar: satuan, kalender, uang, pihak, dokumen | ratusan | bebas | ya |
| **ekosistem** | `@siapa_pun/apa_pun` | tak terbatas | cepat | ya |

**Prosedur keputusan, satu pertanyaan:** apakah ada eksekutor yang membacanya?
Ya → core. Tidak, tapi banyak domain butuh → `@uniti/*`. Selain itu → ekosistem.

Jadi `Currency`, `UnitOfMeasure`, `Address`, `Person` **tidak masuk core**. Mereka
modul `@uniti/*` yang hampir semua orang pasang, tapi tetap bisa diganti kalau ada
yang membuat lebih baik. Rust punya `core` kecil dan `std` besar; Nix punya bahasa
mungil dan nixpkgs raksasa. Itu yang memberi rasa "lengkap" tanpa membayar dengan
core yang beku dan salah.

> **Diperbarui 6 Oktober 2026:** tiga lapis ini menjadi empat jenis, dengan
> **aplikasi** sebagai jenis tersendiri yang pribadi dan milik satu usaha. Lihat
> §15.2.

### 4.4 Aturan pertumbuhan dan uji "kelewat besar"

**Tumbuh secara aditif.** Tambahkan pengikat *opsional* ke peran yang sudah ada;
tambah peran baru hanya kalau benar-benar bukan sejenis dengan yang ada. Menambah
`core:basis` ke `Flow` itu aman. Menambah `core:AllocationEvent` adalah keputusan
taksonomi yang mengikat semua orang.

**Peran tidak pernah kehilangan pengikat.** Kebutuhan baru → peran baru, bukan
peran yang disunting.

**Ujinya, dan ini falsifiable:**

> **Core kelewat besar pada saat dua modul yang sama-sama masuk akal akan
> memodelkan hal yang sama secara berbeda, dan core sudah memilih pemenangnya.**

Di situlah ISO 15926 mati — bukan karena jumlahnya, tapi karena mulai memutuskan
hal yang bukan haknya.

---

## 5. Bagaimana core tumbuh: eksekutor dulu, peran diekstrak

Kalau core mendeklarasikan peran sebelum ada eksekutor yang membacanya, kita baru
saja membuat kosakata yang tidak ditegakkan apa pun — persis
`movement_happened_on` (§1.4), tapi permanen dan mengikat semua orang.

Urutan yang benar:

1. Seseorang menulis modul yang melakukan hal itu dengan nama-namanya sendiri.
   Jalan, tapi belum bisa dibagi.
2. Modul kedua, independen, melakukan hal serupa dengan cara berbeda.
3. **Baru** bentuknya ketahuan, dan eksekutor + peran diekstrak dari keduanya.

Go menemukan `io.Reader` begini — diekstrak dari kode yang sudah jalan, bukan
dirancang di muka. Idiom mereka: *discover the interface, don't design it.* Ini
penangkal langsung untuk kegagalan-oleh-komite.

**Konsekuensi: `@demo` bukan data buang.** Ia instrumen penemuan peran. Modul
kedua dan ketiga di domain yang sama adalah alat riset, bukan sekadar bukti.

**Setiap eksekutor baru datang bersama penolakannya.** Kualitas sistem ini diukur
dari apa yang ia tolak, bukan apa yang ia terima. Sekarang seal memvalidasi
LinkML tapi belum memeriksa satu pun kewajiban.

---

## 6. Keterbatasan sebagai fitur

> **Bahasa graph ini harus tetap lebih terbatas daripada SQL — dengan sengaja.**

Instingnya sudah ada di `compile.py:115`: `_ARITHMETIC` menolak apa pun selain
aritmatika di dalam sebuah expression. Pertahankan disiplin itu di setiap
eksekutor baru. Alasannya bukan kesederhanaan:

**Laporan kecocokan bisa tepat justru karena bahasanya terbatas.** Begitu
seseorang bisa menulis SQL bebas di dalam map, kita tidak bisa lagi menghitung apa
yang rusak kalau sebuah modul ditukar — dan seluruh premis app store mati
bersamanya. Hal yang sama berlaku untuk agent: ia bisa bernalar tentang graph ini
karena graph ini total dan bisa dianalisis, bukan Turing-complete.

Keterbatasan itu bukan harga yang dibayar; itu barang yang dibeli.

---

## 7. Dokumentasi yang dihitung, bukan ditulis

Tidak satu pun dari empat artefak ini boleh ditulis tangan. Semuanya diturunkan
dari isi yang sudah ter-seal, jadi tidak bisa basi.

### 7.1 Katalog — apa yang ada **[dibangun]**

Peran dan kewajibannya; modul, versi, apa yang dideklarasikan dan di-pin; per
kelas: peran apa yang diisinya, aturan apa yang membacanya. **Inilah "API
terdokumentasi" itu.**

**Harus bisa dikueri, bukan dimuat.** Kalau store berisi 500 modul, ia tidak muat
di prompt mana pun. Sejak awal katalog butuh bentuk pencarian: cari berdasarkan
peran, berdasarkan apa yang disediakan, berdasarkan apa yang dibutuhkan. Kalau
dibangun sebagai dokumen, menggantinya nanti mahal.

**Deskripsi menanggung beban, bukan hiasan.** Kalau dua modul sama-sama mengisi
`core:Flow`, deskripsi adalah satu-satunya pembeda yang dipunyai agent — dan
manusia — untuk memilih. Usulan: seal menolak pengisi peran yang tidak punya
deskripsi.

**Yang jadi di irisan 2.7** (`components/modules/catalogue.py`): satu daftar
entri — modul, peran, kelas, slot — dari versi ter-seal *terbaru* tiap modul,
dengan `find()` yang menyaring berdasarkan teks, jenis, peran/pengikat yang
diisi (`fills`), modul pemilik, dan modul yang di-pin (`pins`, "siapa yang kena
kalau X berubah"). Satu keputusan yang tidak ada di usulan: **"dibaca oleh"
melihat lebih lebar** — semua versi ter-seal, bukan hanya yang terbaru — karena
aplikasi yang masih memin versi lama tetap membaca. Usulan menolak pengisi peran
tanpa deskripsi belum dibangun.

### 7.2 Lubang — apa yang bisa saya lakukan di sini **[dibangun]**

Yang paling menentukan untuk tidak overwhelming. Diberi graph setengah jadi, apa
penyelesaian yang sah?

```
Movement mengisi Flow
  ✓ moment    → at
  ✗ amount    → belum terisi. Slot decimal yang Anda punya: qty_delta, unit_cost
  ✗ affects   → belum terisi. Slot ber-range kelas: item, warehouse
```

Ini *type-directed editing* — cara kerja lubang interaktif di Idris atau Agda,
dipindahkan ke makna. Tidak pernah ada halaman kosong; selalu satu lubang dengan
jawaban yang bisa dihitung.

**Yang jadi di irisan 3.1** (`components/studio/read.py`), dengan satu hal yang
ternyata lebih penting dari bentuk lubangnya sendiri:

1. **Lubang bukan konstruksi baru; ia penolakan yang belum dipicu.** Yang
   menghitung "belum terisi" adalah `seal.role_refusals` — pembaca milik gerbang
   itu sendiri — dan daftar jawabannya adalah `repairs[].options` milik irisan
   2.6, yang memang sudah dihitung dari range. Studio tidak menilai apa pun;
   ia menjalankan pembaca yang sama dan **mengumpulkan**. Kalau ia menilai
   sendiri, kita akan punya dua hakim lagi, dan itu persis kegagalan percobaan
   P2 yang pertama.
2. **Agar bisa dikumpulkan, dua pembaca seal jadi generator.**
   `uri_refusals` dan `role_refusals` menghasilkan penolakan satu per satu;
   `seal` mengambil yang pertama dan berhenti (itu yang dilakukan gerbang),
   halaman mengambil semuanya. Satu aturan, dua pembaca — sama seperti `check`
   untuk compiler di irisan 2.6.
3. **Ada lubang yang tidak ditolak siapa pun,** dan itu justru yang membedakan
   modul yang bisa dikompilasi dari modul yang bisa dipakai orang lain: kelas
   tanpa slot, slot yang tidak menempel di kelas mana pun, kelas yang tidak
   akan pernah punya baris, dan **deskripsi yang belum ditulis**. Daftarnya
   tertutup (`OPEN`, lima baris) persis seperti `refusal.CODES`. Usulan §7.1
   "seal menolak pengisi peran tanpa deskripsi" jadi tidak perlu: Studio
   menanyakannya tanpa gerbang harus menolaknya.

### 7.3 Penolakan — kenapa tidak, dan apa yang memperbaikinya **[dibangun]**

`MapError` sudah punya insting yang benar (lihat `compile.py:307`: menolak sambil
menyebutkan pilihan yang sah). Yang kurang: penolakan itu **string**, bukan
**data**.

```python
MapError(code="slot_not_on_class",
         where="IngredientStock.quantity_on_hand",
         expected="a slot of StockMovement", got="qty_delta",
         repairs=[...])
```

Satu sumber, tiga pembaca: kalimat untuk manusia, tombol perbaiki untuk Studio,
hasil tool untuk agent.

**Yang jadi di irisan 2.6** (`components/refusal/`): persis bentuk di atas, plus
tiga hal yang baru kelihatan saat dikerjakan.

1. **Kalimatnya diturunkan, tidak ditulis.** `str(refusal)` dirakit dari
   `where`/`expected`/`got`. Kalau kalimat ditulis di samping strukturnya, itu
   dua sumber, dan yang prosa adalah yang tidak pernah diperbarui.
2. **`code` adalah daftar tertutup.** 62 kode di `refusal.CODES`, masing-masing
   dengan satu baris artinya; konstruktor menolak kode yang tidak terdaftar, dan
   satu test memindai kode gerbang untuk memastikan tidak ada yang menyelinap.
   Daftar itu sendiri adalah dokumentasi: "apa saja yang bisa salah di sini"
   terjawab tanpa membaca kode.
3. **`repairs[].options` dihitung dari graph, bukan dinasihatkan.** Ini bagian
   yang paling berharga dan paling mudah terlewat: `binding_unfilled` pada
   sebuah kelas mengembalikan slot-slot kelas itu yang **range-nya cocok** dengan
   pengikatnya (§7.2 dalam bentuk kecil), dan `not_a_class` pada `over`
   mengembalikan dua daftar terpisah — kelas yang bisa jadi entity, dan **peran**
   yang bisa ditulis sebagai gantinya. Yang kedua itu nasihat irisan 2.5 yang
   datang sebagai instruksi, bukan sebagai pelajaran.

Yang juga ikut: `gate` (siapa yang menolak — store, seal, generator, compiler),
karena itu yang menentukan siapa yang bisa menjawabnya; dan `Repair.where`, file
yang harus disunting, yang sering bukan file yang sedang dibaca.

**Dan satu pembaca keempat yang tidak terduga:** `check()`
(`components/modules/check.py`). Gerbang berhenti di masalah pertama — benar
untuk gerbang, tidak berguna untuk halaman. `check` menjalankan pembaca yang
sama dan **mengumpulkan** penolakannya, jadi orang melihat semuanya sekaligus.
Itu juga yang akan dipakai Studio sambil orang mengetik, dan ia menerima map
yang belum di-seal (`map_=`), yang persis kebutuhan draft.

### 7.4 Diff — apa yang berubah kalau saya lakukan ini

Sebelum setiap tindakan yang tidak bisa ditarik: seal, pindah pin, pasang, copot.
Masukannya cuma dua closure dan aturan aplikasi, jadi bisa dihitung penuh.

```
Tukar @demo/inventory@v3 → @rival/stock-moves@v1

  terpenuhi
    core:Flow        Movement mengisinya (amount=qty_delta, affects=item, moment=at)
    core:Resource    tetap Ingredient, dari @demo/catalog@v2

  yang harus Anda putuskan
    movement_location  modul baru tak punya padanannya. Aplikasi Anda tidak
                       mengelompokkan dengannya — tapi 3 kolom di @demo/warehouse
                       iya. Ketiganya akan padam.

  log tetap menyimpan
    1.204 pernyataan di bawah inv:movement_quantity. Tidak ada yang dihapus.
    Untuk menghidupkannya lagi: nyatakan `inv:movement_quantity is_a core:amount`
    di sebuah modul penyelarasan, dan semuanya terhitung kembali.
```

**Blok terakhir itu keunggulan yang tidak bisa ditiru ERP mana pun.** Di SAP,
Odoo, atau Salesforce, uninstall menjatuhkan tabel atau menelantarkannya. Di sini
fakta hidup di bawah skema (§3.4a) — modul yang dicopot hanya berhenti *dibaca*.
Mengikatnya kembali adalah satu pernyataan penyelarasan, bukan migrasi.

Dan modul penyelarasan itu sendiri adalah modul: ter-seal, berversi, ada
penulisnya, bisa salah, bisa dipasang. `@seseorang/userA-ke-userC@v1` di app
store. **Adaptor jadi barang yang bisa diinstal.**

---

## 8. Studio

### 8.1 Prinsip anti-overwhelm

> **Jangan pernah tunjukkan seluruh graph. Tunjukkan lubang tempat orang itu
> berdiri, kewajibannya, dan himpunan berhingga yang bisa mengisinya.**

Konsekuensinya untuk agent — menurut saya keputusan arsitektur terpenting untuk
tahap 4:

> **Agent tidak menulis YAML. Agent memilih dari langkah sah yang dienumerasi,
> dan sistem yang menulis YAML-nya.**

Agent tidak bisa menghalusinasikan `movement_quantity` kalau jawaban yang sah
dienumerasi. Halusinasi struktural jatuh mendekati nol, dan keluarannya benar *by
construction*. Pembagian tugas: **struktur dari registry, bahasa dari model.**
Agent menerjemahkan kata-kata pemilik toko ke peran yang ada, menamai, dan
menjelaskan — ia bukan arsitek.

Ini sekaligus menjawab soal editor tanpa agent: **mekanismenya sama persis.** Form
editor dan chat adalah dua muka dari satu daftar langkah sah. Bangun daftarnya
sekali, dapat keduanya.

### 8.2 Bentuknya **[separuh dibangun]**

Studio bukan aplikasi baru — ia separuh lagi dari aplikasi yang sudah jalan. Yang
ada sekarang bisa *melihat* hasil graph; Studio adalah tempat graph-nya dibuat.

**~~Metafora utamanya bukan kanvas.~~ Metafora utamanya kanvas — yang tidak
bebas.** Catatan ini semula menolak kanvas: node-dan-panah mengundang orang
menggambar apa saja lalu ditolak. Keberatannya benar; kesimpulannya terlalu
jauh, dan tiga kolom yang dibangun atas dasar itu ternyata tidak terbaca sama
sekali oleh orang yang tahu subjeknya. Yang hilang dari catatan ini adalah
bahwa keduanya bisa sekaligus:

> **Peta adalah halamannya, dan setiap gerakan di atasnya adalah satu langkah
> dari daftar tertutup.** Menarik garis dari satu jenis hal ke jenis hal lain
> bukan menggambar; itu `add_slot` dengan range sebuah kelas, lalu `attach`.
> Tidak ada gerakan yang bisa menghasilkan dokumen yang tidak terurai, jadi
> "menggambar apa saja lalu ditolak" tidak pernah terjadi.

Sebuah modul *adalah* graph. Menyembunyikan graph-nya dari halaman yang
membuatnya berarti meminta orang membayangkan benda yang sedang mereka pegang.

| bagian | isi |
|---|---|
| peta | jenis hal sebagai node, isian yang menunjuk jenis hal lain sebagai garis; yang dipijak digambar samar di atas yang dibangun; jumlah pertanyaan sebagai lencana pada node |
| panel | apa pun yang dipilih di peta: apa itu, bentuk yang diklaimnya dan mana yang belum dipenuhi, isinya, dan **pertanyaannya lebih dulu** |
| di balik tutup | seluruh kosakata mesin: kata gerbang, diff, daftar 24 langkah, transkrip, berkas YAML-nya |

**Yang jadi di irisan 3.1** (`web/src/studio.tsx`, `web/src/graph.tsx`): peta,
panel, dan tutupnya — kecuali angka sungguhan, yang §8.3 dan irisan 3.2.

**Kata awam tidak boleh ditulis di kode.** Menerjemahkan `moment` jadi "kapan"
menanam istilah satu peran ke dalam Studio, dan peran yang dibuat orang lain
besok tidak akan kebagian. Yang dipakai halaman adalah `description` pengikat
itu sendiri: *"When this event happened."* dari `@uniti/core` jadi pertanyaan
*"Which field of Wastage says when this event happened?"*. Satu-satunya kamus
yang ditulis di kode adalah tipe kolom (`decimal` → "number") — himpunan
tertutup milik compiler, bukan milik subjek siapa pun.

Dua hal yang baru kelihatan saat dikerjakan:

1. **Daftar langkah adalah mekanismenya, bukan formulirnya.** Dua puluh empat
   operasi di `OPERATIONS`, tertutup seperti `CODES`, masing-masing dengan
   *kind* per argumen — dan `steps()` mengubah kind itu menjadi daftar jawaban
   yang muat sekarang. Halaman menggambarnya sebagai kontrol; agent di irisan 4
   memilih dari daftar yang sama. §8.1 menyebut ini konsekuensi untuk agent;
   ternyata ia juga yang membuat halamannya tidak mungkin menulis YAML yang
   salah.
2. **Transkrip tidak perlu ditulis siapa pun.** `seal` mewajibkan transkrip, dan
   di Studio transkrip itu adalah daftar langkah yang diambil — `draft.txt`,
   satu baris per operasi, yang disalin keluar sebagai `vN.txt`. Di irisan 4
   percakapan menggantikan daftar itu, dan bentuknya sudah ada.

### 8.3 Properti terpenting: umpan balik numerik langsung

`preview()` (`compile.py:797`) merencanakan, memancarkan SQL, menjalankannya
terhadap log, dan **tidak menulis apa pun**. Artinya:

> **Studio bisa menampilkan angka sungguhan dari aturan yang belum di-seal,
> terhadap data sungguhan, sambil orang mengetiknya.**

Itu perbedaan antara memodelkan di ruang hampa dan memodelkan dengan umpan balik.
Protégé dan hampir semua perkakas ontologi tidak punya loop ini — itulah sebabnya
ontologi melayang jadi tidak berguna tanpa ada yang sadar.

**Graph tidak bisa diverifikasi dengan dibaca; ia bisa diverifikasi dengan
dijalankan.** Studio harus membuat penjalanan itu terus-menerus.

### 8.4 Kurasi: laporan kesehatan graph **[dibangun]**

Enam diagnosa. Semua bahannya sudah ada di kode.

| diagnosa | sumber |
|---|---|
| **istilah mati** — slot dinyatakan di log, dibaca nol aturan | `inv:movement_happened_on`: 245 pernyataan, 0 pembaca |
| **kolom hampa** | `kind: "unfilled"` sudah ada di `plan()` (`compile.py:399`) |
| **kelas kosong** — tak ada apa pun di log yang menjadi salah satunya | penelusuran `designates_type` |
| **peran tak terisi** | katalog |
| **pin tertinggal** — ada versi ter-seal lebih baru | store |
| **fakta yatim** — predikatnya tak dideklarasikan modul mana pun lagi | log × katalog |

Yang terakhir membuat "copot modul tanpa kehilangan data" jadi nyata, bukan
slogan.

**Yang jadi di irisan 2.7** (`components/modules/health.py`), dengan tiga
koreksi terhadap tabel di atas:

1. **Dibaca terhadap satu aplikasi, bukan seluruh store.** "Dibaca nol aturan"
   hanya bermakna terhadap sekumpulan aturan tertentu, dan sekumpulan aturan
   adalah closure satu versi. Konsekuensinya: fakta yatim berarti "tidak
   dideklarasikan modul mana pun *di aplikasi ini*", dan tiap temuan menyebut
   modul mana di store yang *masih* mendeklarasikannya — kosong berarti yatim
   sungguhan.
2. **Pembaca termasuk mekanisme, bukan hanya aturan.** Slot identifier dibaca
   generator (untuk menamai subjek), slot `designates_type` dibaca generator
   dan compiler. Tanpa itu setiap kode dan identitas terlihat mati.
3. **Angkanya 24, bukan 245.** 245 berasal dari data P1. Kernel pengembangan P2
   memuat 24 perpindahan, dan laporan menghitung apa yang ada di log.

Istilah mati tetap panjang (sepuluh di `@demo/stock@v2`), karena label dan
catatan memang dibaca orang, bukan dihitung. Yang membedakan
`movement_happened_on` adalah bahwa ia **mengisi pengikat** — `moment` — dan
tak satu aturan pun membaca `moment`. Itu diurutkan pertama, dan itu temuan
yang sebenarnya: core v2 menulis bahwa `Event` "dieksekusi compiler lewat
`moment`", dan belum ada yang melakukannya.

---

## 9. Rencana per irisan

| irisan | isi | bukti di layar |
|---|---|---|
| ~~**2.5 peran**~~ **[selesai]** | core v2; resolusi slot abstrak; slot abstrak dilewati sebagai kolom; seal menolak peran tak terpenuhi dan closure berlian; `@rival/stock-moves`; panel peran + laporan kecocokan | pin ditukar, angkanya identik — 86/40/46 di kedua sisi |
| ~~**2.6 penolakan**~~ **[selesai]** | penolakan terstruktur di satu tempat (`components/refusal/`); 62 kode tertutup; `options` dihitung dari graph; `check()` mengumpulkan semuanya sekaligus | laporan kecocokan `v1 → v3` memperlihatkan aturan yang padam **berikut dua daftar jawaban yang sah** — kelas, dan peran |
| ~~**2.7 katalog**~~ **[selesai]** | katalog terhitung + enam diagnosa | halaman katalog; `movement_happened_on` menyala sebagai istilah mati — 24 pernyataan, mengisi `moment`, nol pembaca |
| ~~**3.1 Studio: draft**~~ **[selesai]** | draft sebagai file + 24 operasi tertutup + lubang dari pembaca gerbang | modul lengkap dibangun dari nol **tanpa menulis YAML**, dan `seal` menerimanya |
| **3.2 Studio: angka dan seal** | pratinjau angka langsung dari aturan yang belum di-seal + seal dengan konfirmasi | angka sungguhan berubah sambil aturannya diketik |
| **4 agent** | katalog + lubang + penolakan sebagai tool | pemilik toko bercerita di chat, keluar modul ter-seal, langkahnya ada di transkrip |
| **5 uji Anda** | integrasi dua modul milik Anda sendiri lewat chat | — |

**Satu urutan yang tidak bisa ditukar: 2.6 dan 2.7 mendahului Studio.** Permukaan
jelajah Studio *adalah* katalog, dan penyuntingnya digerakkan penolakan. Bangun
Studio lebih dulu, kita membangunnya dua kali.

---

## 10. Risiko dan jebakan yang sudah diketahui

**10.1 Tabrakan nama dengan core.** LinkML tidak memberi namespace pada nama kelas
di dalam satu closure. Modul yang mendeklarasikan kelasnya sendiri bernama `Flow`
akan bertabrakan dengan core. Mitigasi: nama core dicadangkan; seal menolak modul
yang memakainya.

**10.2 Berlian: dua versi core dalam satu closure.** **[dibangun]** Ditegakkan di
seal, dan lebih luas dari usulannya: **tidak ada modul apa pun yang boleh muncul
dua kali di satu closure pada dua versi**, bukan hanya core. Penolakannya menyebut
kedua jalur yang sampai ke sana. Konsekuensinya diterima: ekosistem bergerak
bersama untuk core, yang justru properti yang diinginkan untuk pondasi.

**10.3 Koherensi / hitung ganda.** **[dibangun]** Dijawab dengan membedakan dua
hal yang sebelumnya tercampur:

- **Slot yang mengisi satu pengikat: tepat satu per kelas, kalau tidak ditolak.**
  Mana di antara `qty_gross` dan `qty_net` yang *adalah* amount tidak bisa dijawab
  siapa pun selain penulisnya, dan menebaknya menghasilkan angka salah yang
  terlihat benar. Ditolak di seal dan sekali lagi di compiler.
- **Kelas yang mengisi satu peran: berapa pun, semuanya ikut.** Sebuah gabungan
  bermakna — dua gudang, dua modul — dan sebuah subjek hanya anggota satu kelas,
  jadi tidak ada baris yang terhitung dua kali. Rencananya membawa `covers`, dan
  halaman menyebut kelas mana yang benar-benar dijangkau, jadi gabungan itu
  terlihat alih-alih diam.

Yang tersisa adalah bahaya *data*, bukan skema: satu peristiwa nyata dinyatakan
dua kali di bawah dua kosakata. Itu urusan penyelarasan, dan tidak ada aturan
skema yang bisa mendeteksinya.

**10.4 Satuan.** Menjumlahkan `amount` lintas modul tanpa satuan menghasilkan
angka salah yang terlihat benar. Cepat atau lambat `Flow` harus menuntut `unit`,
atau compiler menolak menjumlahkan grup yang satuannya berbeda.

**10.5 Waktu punya dua sumber tanpa penjaga.** `movement_happened_on` menyimpan
tanggal yang sama dengan `valid_from` assertion-nya, di dua tempat. Hari ini
keduanya cocok karena kebetulan. Core harus memutuskan salah satu — jam kernel,
atau fakta tersendiri dengan seal yang menolak kalau berbeda. Yang tidak boleh
adalah yang sekarang.

**10.6 Identitas.** Mekanisme yang ada sudah menjawab dengan benar tanpa sengaja:
identitas ada di registry kernel dan **dinyatakan**, tidak pernah disimpulkan.
Yang perlu ditambahkan cuma penolakan: tidak ada modul yang boleh menyatakan dua
URI itu satu; hanya orang, lewat sebuah action. Ini jebakan `owl:sameAs` klasik.

**10.7 Skala.** `standing` melakukan `DISTINCT ON` atas seluruh tabel assertion,
sekali per tabel. Di 245 pernyataan tidak terasa; tanda-tanda awal sudah muncul
(`SET enable_nestloop = off; SET jit = off` di `compile.py:812`). Kompilasi
inkremental belum terpecahkan dan akan jadi masalah nyata. Bukan sekarang, tapi
jangan sampai mengagetkan.

**10.8 Godaan terbesar enam bulan ke depan** adalah menambahkan `Party`,
`Document`, `Address`, `Currency` ke core "supaya lengkap". Itu persis titik
matinya ISO 15926. Jawabannya ada di §4.3: mereka `@uniti/*`, bukan core.

---

## 11. Yang sudah diputuskan untuk **tidak** dilakukan

Daftar ini menghemat lebih banyak diskusi daripada daftar rencana.

| tidak dilakukan | alasan |
|---|---|
| Core sebagai kamus istilah universal (canonical data model) | §2 — gagal berkali-kali; core bicara kewajiban, bukan tentang dunia |
| Kanvas graph **bebas** sebagai penyunting utama | §8.2 — mengundang menggambar apa saja lalu ditolak. Kanvas yang **tidak** bebas justru penyunting utamanya: setiap gerakan adalah satu langkah dari daftar tertutup |
| SQL atau ekspresi bebas di dalam map | §6 — mematikan analisis, laporan kecocokan, dan agent |
| Duck typing: menyimpulkan peran dari bentuk | makna justru yang tidak bisa disimpulkan dari bentuk; sebuah `decimal` bisa harga atau berat |
| `owl:sameAs`-style penyimpulan identitas | §10.6 |
| Generics / parameter tipe pada modul | §3.2 — subsumsi sudah melakukannya, tanpa mesin tambahan |
| Jalur hitung kedua untuk penjelasan sel | sudah ditegakkan di `cell()`; ketidakcocokan harus muncul di layar, bukan tersembunyi |
| Agent menulis YAML langsung | §8.1 |
| Memposisikan Uniti sebagai "ontologi untuk enterprise" | ring yang sudah penuh mayat; posisinya adalah log bitemporal yang bisa dikompilasi |
| Modul menambah keterangan pada kelas milik modul lain, bahkan yang hanya menambah | §15.4 — kepemilikan harus jelas; dua modul terhubung hanya dengan menunjuk, lewat modul penghubung atau aplikasi |
| Satu kernel bersama untuk semua usaha dengan penanda usaha | §15.5 — data bercampur, sulit dipasang sendiri, menambah kolom ke daftar yang ditutup |
| Satu kernel per aplikasi | §15.5 — aplikasi berganti versi dan satu usaha bisa punya beberapa; kernelnya per usaha |

---

## 12. Pertanyaan terbuka

1. ~~**Koherensi** (§10.3)~~ — **terjawab di 2.5.** Ambiguitas slot ditolak;
   banyak kelas digabungkan dan disebutkan. Yang tersisa adalah soal data, bukan
   skema.
2. **Waktu** (§10.5) — jam kernel atau momen yang dinyatakan?
3. **Satuan** (§10.4) — di core sebagai pengikat wajib, atau modul `@uniti/units`
   dengan compiler yang menolak campuran?
4. **`Agent`/`Party` sebagai peran core?** Kernel sudah punya `actor_id` (siapa
   yang *menyatakan*). Yang dibutuhkan graph adalah siapa yang *terlibat* —
   pemasok yang mengirim. REA memisahkan keduanya. Apakah perbedaan ini cukup
   layak untuk satu peran core?
5. ~~**Satu core per closure** (§10.2)~~ — **terjawab di 2.5:** batasannya
   diterima, dan diperluas ke setiap modul, bukan hanya core.
6. **Apakah `@demo` dimigrasikan ke peran, atau dibiarkan sebagai bukti bahwa
   modul pra-peran tetap bisa hidup?** Argumen untuk memigrasikan: membuktikan
   migrasi mungkin. Argumen untuk membiarkan: di app store, modul yang tidak ikut
   standar akan jadi mayoritas, dan kita perlu tahu mereka tetap berguna.
7. **Penyelarasan (SKOS) sebagai pintu darurat** — kapan dibangun? Ia yang membuat
   modul yang tidak pernah ikut standar tetap bisa diintegrasikan.
8. **Tata kelola.** Di PoC, yang memutuskan core v2 adalah Anda. Di produk?
   Pertanyaan ini terdengar jauh, tapi ia menentukan apakah core bisa tetap kecil.
   **Sebagian terjawab di §15.4** (6 Oktober 2026): hanya pemilik sebuah nama yang
   membekukan versi di bawahnya. Tata kelola core dan pustaka umum masih terbuka
   (§15.7).
9. **Bisakah modul dipasang sebagian?** Mungkin tidak — tapi belum pernah
   ditanyakan.

---

## 13. Prior art — apa yang diambil dari mana

**Dipinjam, jangan diciptakan ulang:**

| sumber | yang diambil |
|---|---|
| **REA** (McCarthy 1982; ISO/IEC 15944-4) | Resource–Event–Agent–Commitment; "saldo diturunkan dari peristiwa". `StockMovement → IngredientStock` **sudah** REA tanpa sengaja. Pakai kata-katanya; `Commitment` sudah menunggu untuk procurement |
| **Debian `Provides:`, trait Rust, interface Go, service OSGi** | masalah userA→userC adalah masalah *virtual package*; termasuk *coherence rules* Rust untuk §10.3 |
| **SKOS** | `exactMatch`/`closeMatch`/`broadMatch` — eksplisit soal kekuatan kecocokan. Jangan pakai `owl:sameAs` longgar |
| **LinkML `is_a`/`abstract`/`mixin`** | sudah ada di stack, belum dipakai — inti §3 |
| **QUDT / UCUM** | satuan; jangan bikin kamus sendiri |
| **Elm** | semver otomatis dari diff API — model untuk laporan kecocokan |
| **dbt semantic layer / MetricFlow, LookML, Cube, Malloy** | kerabat terdekat compiler; kosakata mapan (entity/dimension/measure/metric). Kenali supaya tidak menemukan ulang dengan lebih buruk |
| **Idris / Agda** | lubang interaktif — model untuk §7.2 |

**Yang benar-benar baru dan bisa dipertahankan:**

1. Lapisan semantik di atas **log bitemporal append-only dengan provenance per
   pernyataan**, bukan di atas warehouse. Setiap angka bisa dibongkar jadi
   siapa-bilang-apa-kapan-dan-kapan-kita-tahu. dbt tidak bisa memberi tahu siapa
   yang bilang 25 kg itu datang, dan kapan kita baru mengetahuinya.
2. Unit distribusinya **versi makna yang ter-seal** dengan closure ter-pin dan
   transkrip percakapan yang menghasilkannya. Package manager untuk model.
3. **Uninstall tidak merusak** (§7.4). Tidak ada sistem enterprise yang punya ini.
4. DB operasional **bisa dibuang**. Skema adalah pandangan, bukan kebenaran.

**Yang bukan baru dan sebaiknya tidak diklaim baru:** graph-sebagai-model, metric
layer, upper ontology.

---

## 14. Istilah

| istilah | arti di sini |
|---|---|
| **peran** (role) | kelas abstrak di core yang menyatakan kewajiban, bukan isi dunia. Diisi lewat `mixins:` |
| **pengikat** (binding) | slot abstrak di core yang harus ditunjuk satu slot konkret |
| **mengisi** (fill) | sebuah kelas menyatakan `mixins: [Flow]` dan menyediakan slot konkret untuk setiap pengikat |
| **closure** | himpunan versi ter-seal yang terjangkau dari satu versi lewat pin |
| **pin** | rujukan ke tepat satu versi ter-seal; tidak ada rentang |
| **aplikasi** | susunan versi yang dikunci untuk satu usaha, dengan tambahan khusus dan contoh angka usaha itu; pribadi, milik usaha tersebut, terikat ke kernelnya. **Jenis tersendiri sejak 6 Oktober 2026** (§15.2) — sebelumnya "satu versi ter-seal biasa, bukan jenis benda baru" |
| **kernel usaha** | catatan yang hanya bertambah milik satu usaha: fakta, aplikasi, modul pribadi, dan kosakata yang dipakainya (§15.5) |
| **pustaka umum** | `@uniti/*`: pihak, barang dan satuan, uang, dokumen transaksi; dipakai hampir semua domain, bukan core (§15.2) |
| **modul penghubung** | modul komunitas yang menghubungkan dua modul dengan menunjuk, tanpa mengubah keduanya (§15.2) |
| **laporan kecocokan** (fit report) | diff yang dihitung sebelum pasang/copot/tukar pin |
| **lubang** (hole) | kewajiban yang belum terpenuhi, dengan himpunan berhingga pengisi yang sah |
| **istilah mati** | slot yang dideklarasikan dan dinyatakan di log, tapi tidak dibaca aturan mana pun |
| **fakta yatim** | pernyataan di log yang predikatnya tidak dideklarasikan modul mana pun lagi |

---

## 15. Jenis modul, peran pengguna, kepemilikan, dan kernel per usaha

> **Diputuskan pemilik pada 6 Oktober 2026. Belum dibangun.** Bagian ini lahir
> dari uji lingkungan kosong (`UJI_LINGKUNGAN_KOSONG.md`). Di langkah 3 modul
> jaminan keluar terputus dari modul sewa: ia membuat "pelanggan" sendiri dan
> tidak punya tempat untuk menempel ke penyewaan. Analisanya menunjukkan bahwa
> penyebab terbesarnya bukan agent, melainkan lapisan yang belum ada. Bagian
> ini menggantikan tiga lapis di §4.3 dengan empat jenis, dan mengubah arti
> **aplikasi** di §14.

### 15.1 Untuk apa modul

1. **Makna ditulis sekali, dipakai banyak usaha.** "Penyewaan alat" dibuat
   sekali oleh komunitas lalu dipakai ribuan usaha sewa. Inilah isi "milik
   bersama" (lihat filosofi Uniti).
2. **Batas tanggung jawab.** Setiap modul punya pemilik; versi yang dibekukan
   tidak berubah, dan pemakai mengunci versi tertentu. Perubahan satu pihak
   tidak merusak pihak lain.
3. **Bisa diganti tanpa kehilangan data.** Catatan milik usaha; modul hanya
   cara membacanya.
4. **Bisa dipercaya.** Setiap versi membawa contoh angka yang terbukti dan
   transkrip cara ia dibuat.

Sistem sampai hari ini baru menangani *membuat* modul. *Menyusun aplikasi dari
modul yang sudah ada*, yang paling sering terjadi di dunia nyata, belum punya
bentuk sendiri.

### 15.2 Empat jenis, dipisahkan

| jenis | isi | pemilik | sifat |
|---|---|---|---|
| **core** | peran dan pengikatnya; dibaca eksekutor | penjaga inti Uniti | terbuka, tidak bisa di-fork, tumbuh 1–2 kali setahun |
| **pustaka umum** `@uniti/*` | yang dipakai hampir semua domain: pihak (orang, pelanggan, pemasok), barang dan satuan, uang, dokumen transaksi (nota dengan baris) | penjaga inti Uniti | terbuka, bisa diganti kalau ada yang lebih baik |
| **modul komunitas** | satu fungsi bisnis — penyewaan, jaminan, gudang, kasir — memakai pustaka umum, tidak membuatnya ulang; termasuk **modul penghubung** yang menghubungkan dua modul ("penyewaan + jaminan") | pembuat modulnya | terbuka |
| **aplikasi** | susunan versi yang dikunci untuk **satu usaha**, tambahan khusus usaha itu, dan contoh angka dari usaha itu sendiri | usaha tersebut | **pribadi** |

Prosedur keputusan §4.3 tetap berlaku untuk tiga baris pertama. Baris keempat
baru: aplikasi bukan lagi "satu versi ter-seal biasa yang mem-pin yang lain",
melainkan jenis tersendiri — pribadi, milik satu usaha, terikat ke kernel usaha
itu (§15.5).

Pelajaran yang diambil dari ERP (Odoo, ERPNext, SAP):
- **Modul dipotong per fungsi bisnis**, bukan per tabel.
- **Data induk bersama ada di modul dasar** — satu "Partner" dipakai Penjualan,
  Pembelian, dan Akuntansi. Di uji lingkungan kosong, ketiadaan lapisan inilah
  yang membuat modul jaminan membuat pelanggan sendiri.
- **Transaksi berbentuk dokumen** (nota dengan baris), dan pembayaran, jaminan,
  atau pengiriman menempel ke notanya. Di uji, sewa dicatat per baris alat,
  jadi jaminan tidak punya tempat menempel.
- **Modul penghubung** (`sale_stock` di Odoo): dua modul saling kenal tanpa
  digabung.

Yang sengaja **tidak** ditiru: modul yang menimpa field dan logika modul lain
(`_inherit` di Odoo). Itu sumber tabrakan diam-diam dan "neraka upgrade".

### 15.3 Peran pengguna

| peran | contoh | yang dimilikinya | memakai Studio? |
|---|---|---|---|
| penjaga inti | tim Uniti | core dan pustaka umum | ya, jarang |
| pembuat modul | komunitas open source, ahli domain, vendor | modul komunitas | ya, inti pekerjaannya |
| penyusun aplikasi | mitra implementor, tim IT perusahaan | aplikasi satu usaha, atas nama usaha itu | ya, paling sering |
| pemilik proses | pemilik Kemah Ceria, manajer | persetujuan: contoh angka dan kapan aplikasi dipakai | lewat percakapan, tanpa membangun |
| staf | Sari di kasir | tidak ada; mengisi data | tidak — formulir dan laporan |
| pemeriksa | akuntan, auditor | tidak ada; membaca angka dan asal-usulnya | tidak |

**Agent membantu setiap peran dan tidak pernah memiliki apa pun** — ia
mengusulkan, manusia memutuskan (prinsip yang sudah berjalan sejak irisan 4).
Panduannya berbeda per peran: bagi penyusun aplikasi, *cari dulu di koleksi
bersama, susun, buat hanya yang kurang, dan sebut di jenis mana yang kurang
itu seharusnya dibuat*; bagi pembuat modul, *buat yang umum, bukan yang khusus
satu usaha*.

### 15.4 Kepemilikan

- **Hanya pemilik sebuah nama** (`@kemahceria`, `@uniti`) yang boleh
  membekukan versi baru di bawah nama itu.
- **Orang lain yang butuh perubahan** punya tiga jalan: mengusulkannya ke
  pemiliknya; menyalin ke nama sendiri (fork); atau menghubungkan lewat modul
  penghubung atau aplikasinya sendiri.
- **Tidak ada perluasan.** Modul tidak boleh menambah keterangan pada kelas
  milik modul lain, bahkan yang hanya menambah tanpa menimpa. Alasannya
  kepemilikan yang jelas: siapa pun yang membaca sebuah kelas tahu persis
  siapa yang bertanggung jawab atas seluruh isinya. Akibatnya **dua modul
  terhubung hanya dengan menunjuk** — jaminan menunjuk ke nota sewa, dan nota
  sewanya tidak berubah. Ini yang sudah ditegakkan studio hari ini (langkah
  pada kelas hanya untuk kelas milik draft sendiri) ✓.

### 15.5 Kernel per usaha; graph bersama di toko berkas

**Setiap usaha punya kernelnya sendiri.** Kernel adalah catatan yang hanya
bertambah (tiga tabel, `components/kernel/001_schema.sql`), dan yang ditulis
ke dalamnya adalah fakta usaha. Satu usaha, satu kernel:

- **Bukan satu kernel per aplikasi.** Aplikasi berganti versi dan menukar
  modul, sedangkan datanya harus tetap di satu tempat. Satu usaha juga bisa
  punya lebih dari satu aplikasi (sewa dan pembukuan) yang membaca pelanggan
  dan transaksi yang sama; memisahkan kernelnya mengulang masalah "modul
  terputus" di tingkat yang lebih tinggi. Sama dengan ERP: satu database untuk
  satu perusahaan, semua modul yang dipasang memakainya.
- **Bukan satu kernel bersama dengan penanda usaha.** Data bercampur, sulit
  dipasang di server sendiri, dan menambah kolom ke daftar yang sengaja
  ditutup.

Isi kernel usaha: seluruh catatan transaksinya, aplikasi-aplikasinya, modul
pribadinya, dan salinan kosakata dari versi yang dipakainya. **Aplikasi dan
modul pribadi tidak pernah masuk ke koleksi bersama** — isinya bisa membuka
rahasia bisnis.

**Graph bersama (core, pustaka umum, modul komunitas) tetap di toko berkas
untuk sekarang.** Berkas versi memang tidak pernah berubah, jadi itu cukup
untuk PoC; yang ditambahkan dulu adalah aturan kepemilikan nama (§15.4).
Arahnya, nanti: **kernel Uniti** — catatan yang hanya bertambah, sama
bentuknya, yang hanya berisi urusan graph: istilah baru, versi, siapa yang
merilis, versi mana yang memakai versi mana, dan penggantian. Berkas tetap
menjadi isi modulnya; kernel Uniti mencatat peristiwanya, sehingga "versi mana
yang dianjurkan pada tanggal sekian" bisa ditanyakan dengan kejujuran yang
sama seperti angka usaha. Satu kernel Uniti pusat cukup untuk awal, tanpa
menutup kemungkinan perusahaan besar menjalankan miliknya sendiri untuk modul
internal (seperti registry pribadi di dunia open source).

**Makna tetap sama di semua kernel usaha.** Setiap predikat dicatat dengan URI
lengkap dari modulnya (irisan 3.2) ✓, jadi "jumlah sewa" di kernel Kemah Ceria
dan di kernel usaha lain berarti hal yang persis sama. Ini membuka jalan,
kelak, untuk membandingkan angka antarusaha dan mengirim catatan dari satu
usaha ke usaha lain beserta asal-usulnya (`source = 'imported'`).

Yang sudah ada di kode hari ini ✓:
- Toko modul adalah berkas, terpisah dari database (`components/modules/store`).
- `seal.register` memperkenalkan kosakata satu versi yang sudah dibekukan ke
  catatan lain tanpa membekukan ulang — pemisahan "satu toko makna, banyak
  catatan" sudah diantisipasi.
- Uji lingkungan kosong berjalan di database sendiri (`uniti_blank`), membaca
  toko modul yang sama.

Yang belum: aplikasi sebagai jenis tersendiri yang tahu kernel mana miliknya;
aturan siapa boleh merilis di bawah nama apa; pemisahan toko pribadi usaha
dari toko bersama; kernel Uniti sebagai catatan.

### 15.6 Alur pembentukan aplikasi dalam praktik

1. Pemilik usaha bercerita ke agent tentang usahanya.
2. Agent **mencari di koleksi bersama dulu**, mengusulkan susunan modul, dan
   menyebut apa yang belum ada serta di jenis mana itu sebaiknya dibuat.
3. Pemilik memberi contoh angka dari usahanya; sistem membuktikan susunan itu
   menghasilkan angka yang sama.
4. Pemilik menyetujui; aplikasi dibekukan ke kernel usahanya; staf mulai
   mengisi.
5. Ketika pembuat modul merilis versi baru, contoh angka usaha itu dijalankan
   terhadap versi baru **sebelum** pindah.

Membuat modul baru dari nol hanya terjadi bila koleksi bersama belum
memilikinya — dan yang dibuat masuk ke jenis yang benar: umum ke komunitas,
khusus ke aplikasi.

### 15.7 Pertanyaan yang masih terbuka

1. Di mana toko pribadi sebuah usaha tinggal — di samping kernelnya, atau
   sebagai toko berkas tersendiri?
2. Bagaimana aplikasi menyatakan kernel miliknya, dan apakah satu aplikasi
   boleh dipasang ke lebih dari satu usaha (template oleh implementor)?
3. Usaha dengan beberapa perusahaan (grup) — satu kernel atau beberapa?
4. Tata kelola pustaka umum: siapa memutuskan isinya, dan seberapa cepat ia
   boleh tumbuh (§4.4 berlaku, tapi untuk `@uniti/*` belum ada ujinya).

---

## Lampiran: cara memverifikasi ulang klaim ✓

Probe yang dipakai untuk §3 ada di riwayat percakapan 18 September 2026. Ringkasan
hasilnya, terhadap `linkml_runtime` yang terpasang di `.venv`:

```
class_descendants('Flow')   -> ['Flow', 'StockMovement']      # mixin diikuti
slot_descendants('amount')  -> ['amount', 'movement_quantity']
movement_quantity.slot_uri  -> inv:movement_quantity           # TIDAK diwariskan
amount.slot_uri             -> None
class_induced_slots('StockMovement') -> movement_quantity, movement_ingredient,
                                        amount, affects        # ← dua terakhir abstrak
```

Baris terakhir itu yang melahirkan invarian §3.4b.
