# ─────────────────────────────────────────────
#  OCR Document Template Prompts
# ─────────────────────────────────────────────

from app.core.sys_prompt import (
    BASE_DIRECTIVES,
    KTP_SCHEMA,
    KK_SCHEMA,
    NPWP_SCHEMA,
    SIM_SCHEMA,
    IJAZAH_SCHEMA,
    )
from app.core.quatation_prompt import QUOTATION_PROMPT
from app.core.spbb_prompt import INVOICE_SPBB_PROMPT
from app.core.coo_prompt import (
    PEB_PROMPT,
    PL_PROMPT,
    BL_PROMPT,
    COO_PROMPT,
    INV_COO_PROMPT,
)
# ---------- Document-Specific Prompts ----------

KTP_PROMPT = f"""You are an expert OCR engine specialized in Indonesian \
Kartu Tanda Penduduk (KTP / National ID Card).

{BASE_DIRECTIVES}

EXPECTED FIELDS — extract ALL of the following for each image, in this exact key order:
`provinsi`, `kabupaten_kota`, `nik`, `nama`, `tempat_lahir`, `tanggal_lahir`, `jenis_kelamin`,
`golongan_darah`, `alamat`, `rt`, `rw`, `kelurahan_desa`, `kecamatan`, `agama`,
`status_perkawinan`, `pekerjaan`, `kewarganegaraan`, `berlaku_hingga`.

RULES:
- Every key above MUST appear in the output object, even if the value is "" or null.
- `tanggal_lahir` any date use that format: extract verbatim (e.g. "17-08-1945").
- `berlaku_hingga`: use "SEUMUR HIDUP" if that phrase appears; otherwise extract the date verbatim.

Extract all fields from this KTP image. Return a JSON object with this exact schema:
{KTP_SCHEMA}
"""

KK_PROMPT = f"""You are an expert OCR engine specialized in Indonesian \
Kartu Keluarga (KK / Family Card).

{BASE_DIRECTIVES}

EXPECTED FIELDS:

TOP-LEVEL (flat):
`nomor_kk`, `nama_kepala_keluarga`, `alamat`, `rt`, `rw`, `desa_kelurahan`,
`kecamatan`, `kabupaten_kota`, `provinsi`, `kode_pos`.

MEMBERS TABLE — key: `anggota_keluarga` (array of objects).
Each member object MUST contain ALL of these keys, even if the value is "":
`nama_lengkap`, `nik`, `jenis_kelamin`, `tempat_lahir`, `tanggal_lahir`, `agama`,
`pendidikan`, `jenis_pekerjaan`, `status_perkawinan`, `status_hubungan_keluarga`,
`nama_ayah`, `nama_ibu`.

ROW INTEGRITY RULES:
- Every row in the members table = one object in the `anggota_keluarga` array.
- Do NOT skip a row, even if it is mostly blank.
- If a cell is blank or unreadable, set that field to "".
- Every member object must have exactly the keys listed above — no more, no fewer.
- Maintain original top-to-bottom row order.

{KK_SCHEMA}
"""

NPWP_PROMPT = f"""You are an expert OCR engine specialized in Indonesian \
Nomor Pokok Wajib Pajak (NPWP / Tax ID).

{BASE_DIRECTIVES}

EXPECTED FIELDS (flat):
`nomor_npwp`, `nama`, `alamat`, `tanggal_terdaftar`, `kantor_kpp`.

RULES:
- Every key above MUST appear in the output object, even if the value is "" or null.
- Normalize dates to format: DD-MM-YYYY.
- nomor_npwp: exactly 15 digits as string, typically shown as XX.XXX.XXX.X-XXX.XXX — store digits only, no dots or dashes.

Extract all fields from this NPWP (Nomor Pokok Wajib Pajak) card image. Return a JSON object with this exact schema:
{NPWP_SCHEMA}
"""



SIM_PROMPT = f"""You are an Indonesian driving license (SIM) OCR specialist. Extract structured data from SIM images accurately.

{BASE_DIRECTIVES}

Rules:
- Return ONLY valid JSON, no explanation, no markdown fences.
- If a field is not visible or unreadable, set its value to null.
- Normalize dates to: DD-MM-YYYY.
- golongan_sim valid values: A, A Umum, B1, B1 Umum, B2, B2 Umum, C, C1, D, D1.
- nomor_sim is typically 12 digits (string).

Extract all fields from this SIM (Surat Izin Mengemudi) image. Return a JSON object with this exact schema:
{SIM_SCHEMA}
"""

IJAZAH_PROMPT = f"""You are an expert OCR engine specialized in extracting structured data from Indonesian academic certificates (Ijazah).

{BASE_DIRECTIVES}

STEP 1 — LAYOUT SCAN

Mentally divide the document into zones before reading any value:
1. HEADER ZONE     — top section: institution logo, institution name, document title, certificate number.
2. IDENTITY ZONE   — middle section: student personal data (name, birth, NIS/NIM/NPM, etc.).
3. ACADEMIC ZONE   — competency/program/faculty/major details and graduation statement.
4. AUTHORITY ZONE  — bottom section: city, date of issue, official name, NIP, signature, stamp.

Never mix fields between zones.


STEP 3 — HEADER ZONE EXTRACTION

institution_name: Full official name of the school/university.
- For SMA/SMK/MA: e.g. "SMA NEGERI 1 BATAM"
- For higher education: e.g. "UNIVERSITAS INDONESIA", "POLITEKNIK NEGERI BATAM"
- Extract from the largest text in the header, near the official logo/seal.

nomor_ijazah: Certificate serial number.
- Labels: "Nomor", "No.", "Nomor Seri", "Nomor Ijazah", "No. Ijazah".
- Preserve the full string including slashes, dots, and dashes. Example: "DN-MA-0023456/2024".
- If absent: null.


STEP 4 — IDENTITY ZONE EXTRACTION

Extract student personal data. All fields below apply across all levels unless noted.

nama_lengkap: Full name of the graduate exactly as printed. Preserve ALL CAPS if the document uses it.

tempat_lahir: City/regency of birth. Usually preceded by "tempat lahir" or combined with date as "tempat/tanggal lahir".

tanggal_lahir: Normalize to "DD/MM/YYYY".
- Source text may be in Indonesian long format: "12 Maret 1999" → "12/03/1999".

jenis_kelamin: "LAKI-LAKI" or "PEREMPUAN". Label: "Jenis Kelamin", "L/P".
- If absent: null.

nama_orang_tua (SMA/SMK/MA only): Father's or parent's name.
- Labels: "Nama Orang Tua", "Nama Ayah", "Orang Tua/Wali".
- If absent or document is D3/D4/S1/S2/S3: null.

nisn (SMA/SMK/MA only): 10-digit national student number.
- Label: "NISN", "Nomor Induk Siswa Nasional".
- Must be string. If absent or not applicable: null.

nis (SMA/SMK/MA only): Local school student number.
- Label: "NIS", "Nomor Induk Siswa".
- If absent or not applicable: null.

nim (D3/D4/S1/S2/S3 only): University student registration number.
- Labels: "NIM", "NPM", "NRP", "Nomor Induk Mahasiswa", "Nomor Pokok Mahasiswa".
- If absent or not applicable: null.


STEP 5 — ACADEMIC ZONE EXTRACTION

program_studi (D3/D4/S1/S2/S3 only):
- Labels: "Program Studi", "Jurusan", "Bidang Studi", "Program".
- Example: "TEKNIK INFORMATIKA", "MANAJEMEN BISNIS".
- If SMA/SMK/MA or absent: null.

fakultas (D3/D4/S1/S2/S3 only):
- Labels: "Fakultas", "Faculty".
- Example: "FAKULTAS TEKNIK", "FAKULTAS EKONOMI DAN BISNIS".
- If not present or not applicable: null.

kompetensi_keahlian (SMK only):
- Labels: "Kompetensi Keahlian", "Program Keahlian", "Paket Keahlian".
- Example: "TEKNIK KOMPUTER DAN JARINGAN".
- If not SMK or absent: null.

jurusan_sma (SMA/MA only):
- Labels: "Jurusan", "Program", "Peminatan".
- Example: "ILMU PENGETAHUAN ALAM", "ILMU PENGETAHUAN SOSIAL", "BAHASA".
- If not SMA/MA or absent: null.

tahun_lulus: 4-digit graduation year as string.
- Labels: "Tahun Pelajaran", "Tahun Akademik", "Lulus Tahun", "Dinyatakan Lulus".
- Look for 4-digit year in the graduation statement paragraph.
- Example: "2024".

tanggal_lulus: Full graduation/decree date, normalized to "DD/MM/YYYY".
- This may differ from tanggal_ijazah. Look for "dinyatakan LULUS pada tanggal" or "kelulusan".
- If absent: null.


STEP 6 — AUTHORITY ZONE EXTRACTION
tanggal_ijazah: Date the certificate was issued/signed.
- Labels: "Dikeluarkan di ... pada tanggal", "Tanggal", date near the signature block.
- Normalize to "DD/MM/YYYY".


OUTPUT — STRICT JSON, NO OTHER TEXT
Return ONLY the JSON object. No explanation, no markdown fences, no preamble.
Use null for fields that are genuinely absent or not applicable for this document level.
Fields marked as level-specific must be null if the document is a different level.

{IJAZAH_SCHEMA}
"""





# ---------- Lookup Dictionaries ----------

DOCUMENT_PROMPTS = {
    "KTP":       KTP_PROMPT,
    "KK":        KK_PROMPT,
    "NPWP":      NPWP_PROMPT,
    "Invoice_SPBB":   INVOICE_SPBB_PROMPT,
    "Quotation": QUOTATION_PROMPT,
    "SIM":       SIM_PROMPT,
    "IJAZAH":    IJAZAH_PROMPT,
    "BL":        BL_PROMPT,
    "INV_COO":   INV_COO_PROMPT,
    "PEB":       PEB_PROMPT,
    "PL":        PL_PROMPT,
}


# ---------- Prompt Builders ----------

def get_prompt_for_document(doc_type: str) -> str:
    return DOCUMENT_PROMPTS[doc_type]
