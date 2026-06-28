# Architecture V2 — Grounded OCR Semantic Pipeline

**Project:** Edge AI OCR
**Version:** 2.0 (Production)
**Status:** Fully Implemented & Verified

---

# 1. Background

Saat ini pipeline OCR menggunakan alur berikut:

```
Image / PDF
      │
      ▼
PaddleOCR
      │
      ▼
OCR Fragments
      │
      ▼
Merged OCR Context
      │
      ▼
VLM Extraction
      │
      ▼
Flat JSON
      │
      ▼
resolve_bboxes_for_flat_json()
      │
      ▼
Final JSON
```

Pipeline tersebut bekerja dengan baik untuk ekstraksi data, namun memiliki kelemahan mendasar.

Setelah PaddleOCR selesai, informasi spasial (bounding box) tidak lagi menjadi bagian dari konteks yang dikirim ke VLM.

VLM hanya menerima representasi teks sehingga hubungan antara hasil ekstraksi dan fragment OCR asli hilang.

Akibatnya sistem harus melakukan proses **post-processing** menggunakan fuzzy string matching untuk menemukan kembali fragment OCR yang sesuai.

---

# 2. Existing Problems

## 2.1 Lost Grounding

Saat OCR selesai, sistem memiliki data berikut:

```
Fragment
├── text
├── bbox
├── confidence
└── page
```

Namun sebelum dikirim ke VLM berubah menjadi:

```
OCR Context

3173010203040001

BUDI

JL MELATI
```

Identitas setiap fragment hilang.

---

## 2.2 Fuzzy Matching

Sesudah VLM menghasilkan JSON, sistem melakukan:

```
JSON Value

↓

Search Again

↓

Find Matching OCR Fragment

↓

Attach Bounding Box
```

Pendekatan ini memiliki beberapa kelemahan:

* false positive
* false negative
* duplicated value
* ambiguous text
* sulit di-debug
* mahal secara komputasi

---

## 2.3 Confidence

Confidence saat ini hanya berasal dari PaddleOCR.

Padahal confidence akhir seharusnya mempertimbangkan:

* OCR confidence
* format validation
* semantic consistency
* document rule
* OCR evidence consistency

---

# 3. Goals

Arsitektur baru harus memenuhi beberapa tujuan utama.

* Menghilangkan kebutuhan fuzzy matching.
* Mempertahankan hubungan antara OCR dan hasil ekstraksi.
* Tetap menyediakan Bounding Box untuk UI.
* Tetap menyediakan OCR Confidence.
* Mudah di-debug.
* Mudah dikembangkan ke jenis dokumen baru.
* Tidak mengubah API secara drastis.

---

# 4. Implemented Pipeline Architecture

```
                  Image / PDF
                       │
                       ▼
                   PaddleOCR
                       │
                       ▼
                 Fragment Store
                       │
                       ▼
            Grounded Prompt Builder
                       │
                       ▼
                      VLM (LLM)
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
  [Grounded Output]           [Flat Output]
 (with sources list)         (plain scalars)
         │                           │
         ▼                           ▼
  Grounded Lookup             Fuzzy Fallback
  (Fragment Store)        (fuzzy_locate_value)
         │                           │
         └─────────────┬─────────────┘
                       ▼
               Grounded Resolver
                       │
                       ▼
               Validation Engine
                       │
                       ▼
               Confidence Engine
                       │
                       ▼
                 Final Response (JSON)
```

---

# 5. Core Concept

Seluruh fragment OCR tidak lagi dianggap sebagai text biasa.

Setiap fragment menjadi object permanen selama pipeline berjalan.

Contoh:

```python
Fragment(
    id="F0001",
    text="3173010203040001",
    bbox=[125,320,480,350],
    confidence=0.98,
    page=1
)
```

Fragment ini tidak pernah dibuang.

Seluruh proses berikutnya hanya mereferensikan fragment tersebut.

---

# 6. Fragment Store

Fragment Store bertindak sebagai *single source of truth* untuk seluruh data teks spasial yang dihasilkan oleh OCR engine selama siklus hidup satu request request pipeline.

### 6.1 Struktur Data Fragment
Setiap kata/blok teks yang dideteksi oleh PaddleOCR dibungkus ke dalam objek `Fragment` yang bersifat *immutable*:

```python
class Fragment:
    id: str               # ID unik terurut (e.g., "F0001", "F0002")
    text: str             # Teks mentah hasil OCR
    bbox: List[int]       # Koordinat absolut [xmin, ymin, xmax, ymax]
    confidence: float     # Nilai akurasi OCR (0.0 - 1.0)
    page_no: int          # Nomor halaman ditemukannya fragment
    line_no: int          # Nomor baris hasil OCR grouping (optional)
    word_order: int       # Urutan kata dalam baris (optional)
```

### 6.2 Alur Kerja resolve_sources
Saat VLM mengembalikan satu atau lebih Fragment ID pada field `sources`, Fragment Store bertugas menggabungkannya secara spasial:
1. **Penyatuan Bounding Box (BBox Union):** Menghitung nilai pembatas terluar (`xmin` terkecil, `ymin` terkecil, `xmax` terbesar, dan `ymax` terbesar) dari semua fragment yang terdaftar di `sources` untuk menghasilkan satu area bounding box utuh.
2. **Kalkulasi Confidence OCR:** Menghitung nilai rata-rata (*average*) dari tingkat akurasi OCR dari semua fragment sumber.
3. **Penyusunan Teks OCR (`ocr_text`):** Menggabungkan teks dari masing-masing fragment, diurutkan secara logis dari atas-ke-bawah dan kiri-ke-kanan berdasarkan halaman, koordinat `y`, lalu koordinat `x`.

---

# 7. Prompt Builder

Prompt tidak lagi hanya berisi OCR text.

Prompt menjadi:

```
[F0001]

NIK

[F0002]

3173010203040001

[F0003]

Nama

[F0004]

BUDI
```

Bounding box **tidak** dikirim ke model.

Model tidak membutuhkan koordinat untuk reasoning.

Bounding box tetap berada di Fragment Store.

---

# 8. Grounded Extraction

Output model berubah.

Dari:

```json
{
  "nik":"3173010203040001"
}
```

Menjadi:

```json
{
    "nik":{
        "value":"3173010203040001",
        "sources":[
            "F0002"
        ]
    }
}
```

Jika field berasal dari beberapa fragment:

```json
{
    "alamat":{
        "value":"JL MELATI NO 10",
        "sources":[
            "F0010",
            "F0011",
            "F0012"
        ]
    }
}
```

---

# 9. Evidence-Based Output

Agar proses debugging lebih mudah, sistem akan menambahkan OCR evidence.

Contoh:

```json
{
    "nik":{
        "value":"3173010203040001",
        "evidence":[
            {
                "fragment_id":"F0002",
                "ocr_text":"3173010203040001"
            }
        ]
    }
}
```

Dengan demikian setiap hasil ekstraksi memiliki bukti yang jelas.

---

# 10. Resolver (Grounded & Fallback)

Resolver bertanggung jawab untuk mengubah JSON mentah hasil ekstraksi VLM menjadi format terstruktur yang kaya dengan metadata koordinat dan status.

### 10.1 Alur Rekursif resolve_grounded_json
Resolver menelusuri JSON ekstraksi secara rekursif:
* **Grounded Node (`{value, sources}`):** Langsung memproses field dengan melakukan lookup koordinat ke `FragmentStore` menggunakan daftar ID di `sources`.
* **Flat Node (Plain Scalar):** Jika nilai berupa string/angka biasa (un-grounded), resolver membungkusnya secara otomatis menjadi `{"value": scalar, "sources": []}` agar dapat melewati alur resolusi dan validasi terpadu yang sama.

### 10.2 Mekanisme Fallback Koordinat (fuzzy_locate_value)
Apabila pencarian berbasis `sources` tidak menghasilkan fragment apapun (`fragments_found == 0`), resolver memicu alur fallback bertahap untuk mencari koordinat spasial di halaman dokumen:
1. **Exact & Clean Matching:** Melakukan normalisasi string (menghilangkan spasi dan karakter non-alphanumeric) dan mencari fragment OCR yang memiliki teks yang persis sama.
2. **Fuzzy Substring Search:** Menggunakan algoritma *sliding window token matching* berbantuan `difflib.SequenceMatcher` untuk mencari kecocokan token dengan ambang batas (threshold) dinamis berdasarkan panjang kata.
3. **Proximity Check (Spatial Filtering):** Jika teks ditemukan secara fuzzy, resolver memverifikasi kedekatan koordinat vertikal dan horizontal dengan label field (misalnya, nilai NIK harus berada di dekat/sebelah kanan label "NIK"). Jika terlalu jauh, koordinat dibatalkan untuk menghindari kontaminasi data dari baris lain.
4. **Label Fallback:** Jika nilai sama sekali tidak ditemukan di dokumen, koordinat bounding box label field tersebut diambil sebagai fallback sementara agar kotak penyorot di UI tetap mengarah ke area field yang bersangkutan.

---

# 11. Validation Engine

Validation Engine bertugas menganalisis kelayakan data hasil ekstraksi VLM dengan membandingkannya secara langsung terhadap teks asli yang dibaca oleh OCR engine (PaddleOCR) dan aturan format dokumen.

### 11.1 Alur Kerja validate_grounded_field
Mesin validator menerima parameter berupa `field_name`, `value_str` (LLM), `ocr_text` (PaddleOCR), `confidence` OCR, dan jumlah fragment yang ditemukan. 

### 11.2 Evaluasi Status Kelayakan Field
Validator menentukan satu status spesifik untuk setiap field berdasarkan kriteria berikut:
* **`verified`:** Ekstraksi VLM cocok persis dengan teks OCR asli, format data valid berdasarkan aturan tipe field, dan tingkat akurasi OCR tinggi ($\ge 0.85$).
* **`value_mismatch`:** Teks ekstraksi VLM berbeda dengan teks OCR asli (menandakan LLM melakukan koreksi/normalisasi semantik atas kesalahan pembacaan OCR).
* **`low_confidence`:** Teks ekstraksi VLM cocok dengan OCR, format valid, namun nilai kepercayaan OCR di bawah batas minimum ($< 0.85$).
* **`format_invalid`:** Teks ekstraksi tidak memenuhi format standar (misal: NIK bukan 16 digit, atau format tanggal tidak sesuai aturan kalender), meskipun koordinat spasialnya ditemukan di dokumen.
* **`not_found`:** Nilai ekstraksi tidak dapat ditemukan baik secara grounded (via Fragment ID) maupun melalui pencarian fuzzy di seluruh layout dokumen.
* **`partial_match`:** Sebagian koordinat fragment sumber ditemukan, namun tidak mencakup keseluruhan panjang data yang diekstraksi.

---

# 12. Confidence Engine

Confidence Engine menggantikan persentase akurasi OCR mentah dengan perhitungan **Composite Confidence Score** tertimbang. Hal ini untuk memastikan tingkat keyakinan data mencerminkan validitas format dan konsistensi makna.

### 12.1 Formula Perhitungan Komposit
Nilai kepercayaan dihitung menggunakan bobot komponen berikut:

$$\text{Composite Score} = (w_{\text{ocr}} \times S_{\text{ocr}}) + (w_{\text{semantic}} \times S_{\text{semantic}}) + (w_{\text{validation}} \times S_{\text{validation}}) + (w_{\text{rules}} \times S_{\text{rules}})$$

Di mana bobot default yang diimplementasikan adalah:
* **$w_{\text{ocr}}$ (40%):** Akurasi mentah dari OCR Engine.
* **$w_{\text{semantic}}$ (30%):** Bernilai `1.0` jika teks ekstraksi VLM cocok secara bersih dengan teks OCR asli (`value_mismatch` bernilai `0.0`).
* **$w_{\text{validation}}$ (20%):** Bernilai `1.0` jika lolos semua uji regex format dan rentang nilai (`format_invalid` bernilai `0.0`).
* **$w_{\text{rules}}$ (10%):** Bernilai `1.0` jika lolos aturan spesifik dokumen (seperti kalkulasi silang antar field).

---

# 13. API Output

Struktur output akhir yang dikirim ke frontend:

```json
{
    "nik": {
        "text": "3173010203040001",
        "bbox": [120, 320, 480, 350],
        "confidence": 0.992,
        "page_no": 1,
        "status": "verified",
        "ocr_text": "3173010203040001",
        "validation_errors": null
    }
}
```

Struktur ini tetap kompatibel dengan interface UI frontend dan langsung menyertakan koordinat, status kelayakan, serta detail kesalahan format jika ada.

---

# 14. Migration Plan Status

Semua fase migrasi telah selesai diimplementasikan dan diverifikasi:

* **Phase 1 [COMPLETED]:** Integrasi Fragment ID unik ke setiap OCR Fragment dan pembuatan `FragmentStore` sebagai single source of truth.
* **Phase 2 [COMPLETED]:** Grounded Prompt Builder dengan penandaan Fragment ID untuk memandu VLM mengembalikan field ter-grounding (`sources`).
* **Phase 3 [COMPLETED]:** Grounded Resolver yang mengutamakan lookup Fragment ID dan ber-fallback secara seamless ke `fuzzy_locate_value`.
* **Phase 4 [COMPLETED]:** Implementasi Validation Engine terpadu (status status verifikasi) dan Confidence Engine berbasis bobot komposit.
* **Phase 5 [COMPLETED]:** Pembersihan fungsi legacy yang usang dan integrasi status pemetaan visual di frontend (`DocumentPreviewer.jsx`).

---

# 15. Future Improvements

Setelah arsitektur ini stabil, beberapa peningkatan berikut dapat dilakukan.

## Layout Graph

Menghubungkan label dan value berdasarkan posisi.

Contoh:

```
NIK
↓

3173010203040001

Nama
↓

BUDI
```

Sehingga model tidak perlu mencari hubungan sendiri.

---

## Fragment Retrieval

Untuk dokumen yang sangat besar, Prompt Builder dapat mengirim hanya Top-K fragment yang relevan sehingga token usage tetap rendah.

---

## Rule Engine

Menambahkan validasi berbasis pengetahuan.

Contoh:

* validasi NIK
* validasi NPWP
* validasi tanggal
* validasi provinsi
* validasi antar field

---

# Expected Benefits

* Tidak ada lagi kehilangan hubungan antara OCR dan hasil ekstraksi.
* Bounding box selalu berasal dari OCR asli.
* Tidak bergantung pada fuzzy matching.
* Lebih mudah di-debug.
* Lebih mudah dikembangkan.
* Lebih scalable untuk dokumen multi halaman.
* Menjadi fondasi untuk Document Intelligence Pipeline yang lebih kompleks.
