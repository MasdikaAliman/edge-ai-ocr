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
    INV_COO_PROMPT,
)
# ---------- Document-Specific Prompts ----------

KTP_PROMPT = f"""You are a high-precision OCR extraction engine specialized in Indonesian Kartu Tanda Penduduk (KTP / National ID Card).

You will receive:
1. The original KTP image.
2. OCR raw text/context extracted from the image.

Your task is to extract ONLY the fields listed below from the KTP.

{BASE_DIRECTIVES}

EXPECTED FIELDS — return ALL keys in this exact order:
1. `provinsi`
2. `kabupaten_kota`
3. `nik`
4. `nama`
5. `tempat_lahir`
6. `tanggal_lahir`
7. `jenis_kelamin`
8. `golongan_darah`
9. `alamat`
10. `rt`
11. `rw`
12. `kelurahan_desa`
13. `kecamatan`
14. `agama`
15. `status_perkawinan`
16. `pekerjaan`
17. `kewarganegaraan`
18. `berlaku_hingga`

FIELD-SPECIFIC RULES:

1. `provinsi`
   - Extract the province name from the top header.
   - Usually appears after or near the word "PROVINSI".
   - Example: "KEPULAUAN RIAU", "DKI JAKARTA", "JAWA BARAT".
   - Do NOT include the word "PROVINSI" unless it is part of the printed value.

2. `kabupaten_kota`
   - Extract the city/regency name from the second header line.
   - Usually starts with "KOTA" or "KABUPATEN".
   - Keep the prefix exactly as printed.
   - Example: "KOTA BATAM", "KABUPATEN BOGOR".

3. `nik`
   - Extract exactly the 16-digit NIK number.
   - Remove spaces only if OCR splits the digits.
   - Do NOT extract phone numbers, postal codes, dates, or other numbers.
   - If fewer or more than 16 digits are found, return "" unless the image clearly shows the complete NIK.

4. `nama`
   - Extract the full name after the label "Nama".
   - Use uppercase/lowercase exactly as printed.
   - Do NOT include the label "Nama".

5. `tempat_lahir`
   - Extract the birthplace from the "Tempat/Tgl Lahir" field.
   - It is the text before the birth date.
   - Example: if printed "BATAM, 17-08-1945", return "BATAM".
   - Do NOT include the birth date.

6. `tanggal_lahir`
   - Extract the birth date from "Tempat/Tgl Lahir".
   - Return the date exactly as printed.
   - Do NOT normalize the date format.
   - Example: "17-08-1945" must remain "17-08-1945".
   - Example: "17/08/1945" must remain "17/08/1945".

7. `jenis_kelamin`
   - Extract only the gender value.
   - Valid common values: "LAKI-LAKI", "PEREMPUAN".
   - Do NOT include the label "Jenis Kelamin".

8. `golongan_darah`
   - Extract the blood type if present.
   - Common values: "A", "B", "AB", "O", "-".
   - If the KTP shows "-" or blank, return null.
   - Do NOT confuse with gender or religion.

9. `alamat`
   - Extract the address after the label "Alamat".
   - Include only the street/address line.
   - Do NOT include RT/RW, Kel/Desa, Kecamatan, religion, marital status, or occupation.
   - Preserve punctuation and spacing as much as possible.

10. `rt`
   - Extract RT from the "RT/RW" field.
   - If printed as "003/007", return "003".
   - Preserve leading zeros.

11. `rw`
   - Extract RW from the "RT/RW" field.
   - If printed as "003/007", return "007".
   - Preserve leading zeros.

12. `kelurahan_desa`
   - Extract the value after label "Kel/Desa" or "Kelurahan/Desa".
   - Do NOT include the label.

13. `kecamatan`
   - Extract the value after label "Kecamatan".
   - Do NOT include the label.

14. `agama`
   - Extract the religion after label "Agama".
   - Common values include "ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDDHA", "KONGHUCU".
   - Return exactly as printed.

15. `status_perkawinan`
   - Extract the marital status after label "Status Perkawinan".
   - Common values include "BELUM KAWIN", "KAWIN", "CERAI HIDUP", "CERAI MATI".
   - Return exactly as printed.

16. `pekerjaan`
   - Extract the occupation after label "Pekerjaan".
   - Return exactly as printed.
   - Do NOT include nationality or validity period.

17. `kewarganegaraan`
   - Extract nationality after label "Kewarganegaraan".
   - Common values: "WNI", "WNA".
   - Return exactly as printed.

18. `berlaku_hingga`
   - Extract the value after label "Berlaku Hingga".
   - If "SEUMUR HIDUP" appears, return exactly "SEUMUR HIDUP".
   - Otherwise return the date exactly as printed.
   - Do NOT normalize the date.

OCR ERROR HANDLING:
- If OCR splits a label and value across lines, use the visual layout and nearby text to associate them.
- If OCR has minor spacing issues, correct only obvious spacing in labels, not in values.
- If two possible values exist for one field, choose the value closest to the correct label.
- Never copy values from unrelated fields.


Extract all fields from this KTP image. Return a JSON object with this exact schema:
{KTP_SCHEMA}
"""

KK_PROMPT = f"""You are an expert OCR engine specialized in Indonesian Kartu Keluarga (KK / Family Card).

You will receive:
1. The original KK image.
2. OCR raw text/context extracted from the image.

Your task is to extract ONLY the fields listed below from the KK.

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

Extract all fields from this KK image. Return a JSON object with this exact schema:
{KK_SCHEMA}
"""

NPWP_PROMPT = f"""You are an expert OCR engine specialized in Indonesian Nomor Pokok Wajib Pajak (NPWP / Tax ID Card).

You will receive:
1. The original NPWP image.
2. OCR raw text/context extracted from the image.

Your task is to extract ONLY the fields listed below from the NPWP.

{BASE_DIRECTIVES}

EXPECTED FIELDS (flat):
- `nomor_npwp`
- `nama`
- `alamat`
- `tanggal_terdaftar`
- `kantor_kpp`

FIELD-SPECIFIC RULES:
- nomor_npwp: exactly 15 digits as string, typically shown as XX.XXX.XXX.X-XXX.XXX
- tanggal_terdaftar: normalize dates to format: DD-MM-YYYY.

Extract all fields from this NPWP image. Return a JSON object with this exact schema:
{NPWP_SCHEMA}
"""

SIM_PROMPT = f"""You are an expert OCR engine specialized in Indonesian driving licenses (Surat Izin Mengemudi / SIM).

You will receive:
1. The original SIM image.
2. OCR raw text/context extracted from the image.

Your task is to extract ONLY the fields listed below from the SIM.

{BASE_DIRECTIVES}

EXPECTED FIELDS — return ALL keys in this exact order:
1. `nomor_sim`
2. `golongan_sim`
3. `nama`
4. `tempat_lahir`
5. `tanggal_lahir`
6. `jenis_kelamin`
7. `golongan_darah`
8. `alamat`
9. `pekerjaan`
10. `berlaku_hingga`
11. `instansi_penerbit`

FIELD-SPECIFIC RULES:
- nomor_sim: typically 12 digits (string).
- golongan_sim valid values: A, A Umum, B1, B1 Umum, B2, B2 Umum, C, C1, D, D1.
- tanggal_lahir: normalize to format DD-MM-YYYY.
- berlaku_hingga: normalize to format DD-MM-YYYY.

Extract all fields from this SIM image. Return a JSON object with this exact schema:
{SIM_SCHEMA}
"""

IJAZAH_PROMPT = f"""You are an expert OCR engine specialized in Indonesian higher education academic certificates (Ijazah D3/D4/S1/S2/S3).

You will receive:
1. The original Ijazah image.
2. OCR raw text/context extracted from the image.

Your task is to extract ONLY the fields listed below from the Ijazah.

{BASE_DIRECTIVES}

EXPECTED FIELDS — return ALL keys in this exact order:
1. `document_level`
2. `institution_name`
3. `nomor_ijazah`
4. `nama_lengkap`
5. `tempat_lahir`
6. `tanggal_lahir`
7. `nim`
8. `program_studi`
9. `fakultas`
10. `tanggal_lulus`
11. `tanggal_ijazah`

Use BOTH the visual context of the document image and the provided RAW OCR CONTEXT to resolve value spelling, registration numbers, and dates. If the image is slightly blurry or hard to read, cross-reference it with the RAW OCR CONTEXT, which contains high-precision text strings.

STEP 1 — LAYOUT SCAN

Mentally divide the document into zones before reading any value:
1. HEADER ZONE     — top section: institution logo, institution name (university/institute/college), document title, certificate number.
2. IDENTITY ZONE   — middle section: student personal data (name, place/date of birth, NIM/NPM).
3. ACADEMIC ZONE   — faculty, program of study (major), degree obtained, and graduation statement.
4. AUTHORITY ZONE  — bottom section: city of issue, date of issue, signing officials (rector, dean, director).

Never mix fields between zones.


STEP 2 — HEADER ZONE EXTRACTION

institution_name: Full official name of the university, institute, polytechnic, or academy (e.g., "UNIVERSITAS INDONESIA", "POLITEKNIK NEGERI BATAM").
- Look in the largest text of the header, close to the official logo.

nomor_ijazah: Certificate serial/registration number.
- Look for labels: "Nomor", "No.", "Nomor Seri", "Nomor Ijazah", "No. Ijazah", "Nomor Nasional", etc.
- Preserve the exact full string (including slashes, dots, and dashes).
- If not present or unreadable, return null.


STEP 3 — IDENTITY ZONE EXTRACTION

nama_lengkap: Full name of the graduate. Match casing (usually ALL CAPS) and keep any punctuation/accents if present.
- Cross-reference with RAW OCR CONTEXT to ensure exact character spelling.

tempat_lahir: City or regency of birth.
- Typically appears as part of "tempat, tanggal lahir". Extract only the place.

tanggal_lahir: Date of birth normalized to "DD/MM/YYYY".
- Convert Indonesian month name to number (e.g., "12 Maret 1999" → "12/03/1999").

nim: Student registration/identification number.
- Labels: "NIM", "NPM", "NRP", "Nomor Induk Mahasiswa", "Nomor Pokok Mahasiswa".
- Preserve full alphanumeric value. If absent: null.


STEP 4 — ACADEMIC ZONE EXTRACTION

program_studi: Program of study / major.
- Labels: "Program Studi", "Program Pendidikan", "Program", "Jurusan", "Program Sarjana/Diploma".
- Examples: "TEKNIK INFORMATIKA", "AKUNTANSI".
- If absent: null.

fakultas: Academic faculty.
- Labels: "Fakultas", "Faculty".
- Examples: "FAKULTAS TEKNIK", "FAKULTAS ILMU KOMPUTER".
- If absent: null.

tanggal_lulus: Graduation / decree date normalized to "DD/MM/YYYY".
- Look for the official graduation statement paragraph containing: "dinyatakan lulus pada tanggal..." or similar.
- Convert Indonesian month name to number. If absent: null.


STEP 5 — AUTHORITY ZONE EXTRACTION

tanggal_ijazah: Date the certificate was officially issued and signed.
- Look near the rector's or dean's signature block at the bottom right.
- Normalize to "DD/MM/YYYY" format.


Extract all fields from this Ijazah image. Return a JSON object with this exact schema:
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
