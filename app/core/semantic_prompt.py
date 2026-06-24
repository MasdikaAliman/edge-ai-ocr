import json
from app.core import sys_prompt
from app.core.doc_prompt import DOCUMENT_PROMPTS

FIELD_TEMPLATE = {
    "text": "string | null",
    "bbox": [100, 150, 300, 200],  # Example absolute coordinates [x_min, y_min, x_max, y_max]
    "page_no": "integer | null"
}

KTP_SEMANTIC_SCHEMA = {
    "provinsi": FIELD_TEMPLATE,
    "kabupaten_kota": FIELD_TEMPLATE,
    "nik": FIELD_TEMPLATE,
    "nama": FIELD_TEMPLATE,
    "tempat_lahir": FIELD_TEMPLATE,
    "tanggal_lahir": FIELD_TEMPLATE,
    "jenis_kelamin": FIELD_TEMPLATE,
    "golongan_darah": FIELD_TEMPLATE,
    "alamat": FIELD_TEMPLATE,
    "rt_rw": FIELD_TEMPLATE,
    "kelurahan_desa": FIELD_TEMPLATE,
    "kecamatan": FIELD_TEMPLATE,
    "agama": FIELD_TEMPLATE,
    "status_perkawinan": FIELD_TEMPLATE,
    "pekerjaan": FIELD_TEMPLATE,
    "kewarganegaraan": FIELD_TEMPLATE,
    "berlaku_hingga": FIELD_TEMPLATE
}

KK_SEMANTIC_SCHEMA = {
    "nomor_kk": FIELD_TEMPLATE,
    "nama_kepala_keluarga": FIELD_TEMPLATE,
    "alamat": FIELD_TEMPLATE,
    "rt": FIELD_TEMPLATE,
    "rw": FIELD_TEMPLATE,
    "desa_kelurahan": FIELD_TEMPLATE,
    "kecamatan": FIELD_TEMPLATE,
    "kabupaten_kota": FIELD_TEMPLATE,
    "provinsi": FIELD_TEMPLATE,
    "kode_pos": FIELD_TEMPLATE,
    "members": [
        {
            "nama_lengkap": FIELD_TEMPLATE,
            "nik": FIELD_TEMPLATE,
            "jenis_kelamin": FIELD_TEMPLATE,
            "tempat_lahir": FIELD_TEMPLATE,
            "tanggal_lahir": FIELD_TEMPLATE,
            "agama": FIELD_TEMPLATE,
            "pendidikan": FIELD_TEMPLATE,
            "jenis_pekerjaan": FIELD_TEMPLATE,
            "status_perkawinan": FIELD_TEMPLATE,
            "status_hubungan_keluarga": FIELD_TEMPLATE,
            "nama_ayah": FIELD_TEMPLATE,
            "nama_ibu": FIELD_TEMPLATE
        }
    ]
}

NPWP_SEMANTIC_SCHEMA = {
    "nomor_npwp": FIELD_TEMPLATE,
    "nama": FIELD_TEMPLATE,
    "alamat": FIELD_TEMPLATE,
    "tanggal_terdaftar": FIELD_TEMPLATE,
    "kantor_kpp": FIELD_TEMPLATE
}

SIM_SEMANTIC_SCHEMA = {
    "nomor_sim": FIELD_TEMPLATE,
    "golongan_sim": FIELD_TEMPLATE,
    "nama": FIELD_TEMPLATE,
    "tempat_lahir": FIELD_TEMPLATE,
    "tanggal_lahir": FIELD_TEMPLATE,
    "jenis_kelamin": FIELD_TEMPLATE,
    "golongan_darah": FIELD_TEMPLATE,
    "alamat": FIELD_TEMPLATE,
    "pekerjaan": FIELD_TEMPLATE,
    "berlaku_hingga": FIELD_TEMPLATE,
    "instansi_penerbit": FIELD_TEMPLATE
}

IJAZAH_SEMANTIC_SCHEMA = {
    "document_level": FIELD_TEMPLATE,
    "institution_name": FIELD_TEMPLATE,
    "nomor_ijazah": FIELD_TEMPLATE,
    "nama_lengkap": FIELD_TEMPLATE,
    "tempat_lahir": FIELD_TEMPLATE,
    "tanggal_lahir": FIELD_TEMPLATE,
    "nisn": FIELD_TEMPLATE,
    "nis": FIELD_TEMPLATE,
    "nim": FIELD_TEMPLATE,
    "jurusan_sma": FIELD_TEMPLATE,
    "kompetensi_keahlian": FIELD_TEMPLATE,
    "program_studi": FIELD_TEMPLATE,
    "fakultas": FIELD_TEMPLATE,
    "tahun_lulus": FIELD_TEMPLATE,
    "tanggal_lulus": FIELD_TEMPLATE,
    "tanggal_ijazah": FIELD_TEMPLATE
}

INVOICE_SPBB_SEMANTIC_SCHEMA = {
    "invoice_number": FIELD_TEMPLATE,
    "invoice_date": FIELD_TEMPLATE,
    "due_date": FIELD_TEMPLATE,
    "purchase_order": FIELD_TEMPLATE,
    "currency": FIELD_TEMPLATE,
    "total_amount": FIELD_TEMPLATE,
    "sales_order": FIELD_TEMPLATE,
    "remark": FIELD_TEMPLATE
}

QUOTATION_SEMANTIC_SCHEMA = {
    "quotation_number": FIELD_TEMPLATE,
    "quotation_date": FIELD_TEMPLATE,
    "sales_agent": FIELD_TEMPLATE,
    "no_telp": FIELD_TEMPLATE,
    "currency": FIELD_TEMPLATE,
    "purchasing_group": FIELD_TEMPLATE,
    "plant": FIELD_TEMPLATE,
    "lead_time": FIELD_TEMPLATE,
    "submitted_by": FIELD_TEMPLATE,
    "total_amount": FIELD_TEMPLATE,
    "material_items": [
        {
            "item_number": FIELD_TEMPLATE,
            "material_code": FIELD_TEMPLATE,
            "material_description": FIELD_TEMPLATE,
            "quantity": FIELD_TEMPLATE,
            "unit": FIELD_TEMPLATE,
            "unit_price": FIELD_TEMPLATE,
            "amount": FIELD_TEMPLATE,
            "UoM": FIELD_TEMPLATE
        }
    ]
}

BL_SEMANTIC_SCHEMA = {
    "vessel_voyage_no": FIELD_TEMPLATE,
    "mvs": FIELD_TEMPLATE,
    "document_no": FIELD_TEMPLATE,
    "document_date": FIELD_TEMPLATE,
    "ship_date": FIELD_TEMPLATE,
    "consignee": FIELD_TEMPLATE,
    "country_of_destination": FIELD_TEMPLATE
}

PEB_SEMANTIC_SCHEMA = {
    "nomor_pendaftaran": FIELD_TEMPLATE,
    "tanggal_pendaftaran": FIELD_TEMPLATE
}

PL_SEMANTIC_SCHEMA = {
    "no": FIELD_TEMPLATE,
    "date": FIELD_TEMPLATE
}

INV_COO_SEMANTIC_SCHEMA = {
    "invoice_number": FIELD_TEMPLATE,
    "invoice_date": FIELD_TEMPLATE,
    "form": FIELD_TEMPLATE,
    "table": [
        {
            "no": FIELD_TEMPLATE,
            "kategori_barang": FIELD_TEMPLATE,
            "model": FIELD_TEMPLATE,
            "quantity_ctns": FIELD_TEMPLATE,
            "quantity_pcs": FIELD_TEMPLATE,
            "unit_price": FIELD_TEMPLATE,
            "amount_usd": FIELD_TEMPLATE,
            "bruto": FIELD_TEMPLATE,
            "netto": FIELD_TEMPLATE
        }
    ],
    "total_amount": FIELD_TEMPLATE,
    "total_weight_bruto": FIELD_TEMPLATE,
    "total_weight_netto": FIELD_TEMPLATE,
    "total_quantity_ctns": FIELD_TEMPLATE,
    "total_quantity_pcs": FIELD_TEMPLATE
}

SEMANTIC_SCHEMAS = {
    "KTP": KTP_SEMANTIC_SCHEMA,
    "KK": KK_SEMANTIC_SCHEMA,
    "NPWP": NPWP_SEMANTIC_SCHEMA,
    "SIM": SIM_SEMANTIC_SCHEMA,
    "IJAZAH": IJAZAH_SEMANTIC_SCHEMA,
    "Invoice_SPBB": INVOICE_SPBB_SEMANTIC_SCHEMA,
    "Quotation": QUOTATION_SEMANTIC_SCHEMA,
    "BL": BL_SEMANTIC_SCHEMA,
    "PEB": PEB_SEMANTIC_SCHEMA,
    "PL": PL_SEMANTIC_SCHEMA,
    "INV_COO": INV_COO_SEMANTIC_SCHEMA,
    "COO": INV_COO_SEMANTIC_SCHEMA
}

def get_doctype_semantic_prompt(doc_type: str) -> str:
    # Use the legacy document-specific system prompts directly.
    # These prompts are already optimized for flat JSON outputs.
    return DOCUMENT_PROMPTS.get(doc_type, "")

def get_fields_semantic_prompt(fields: list[str]) -> str:
    from app.core.sys_prompt import BASE_DIRECTIVES
    field_list = "\n".join(f"  - `{f}`" for f in fields)
    schema = {f: "string | null" for f in fields}
    return f"""You are a high-precision document extraction engine.
Your task is to extract ONLY the specific fields listed below.

{BASE_DIRECTIVES}

TARGET FIELDS TO EXTRACT:
{field_list}

Please extract all fields from the document image and OCR text. Return a JSON object matching this exact schema:
{json.dumps(schema, indent=2)}
"""

def get_custom_semantic_prompt(custom_prompt: str) -> str:
    from app.core.sys_prompt import BASE_DIRECTIVES
    return f"""You are a flexible document extraction assistant. \
Your primary directive is to follow the user's custom prompt below.

Only reject if the instruction has absolutely nothing to do with the provided \
document/image. When in doubt, follow the user's instruction.

OUTPUT CONVENTION:
- Follow the format the user requests (JSON, CSV, text, etc.).
- If no specific format is requested, output JSON.
- Use snake_case for any keys you invent yourself.
{BASE_DIRECTIVES}

User Instructions:
{custom_prompt}
"""
