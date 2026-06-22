import json

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

BASE_INSTRUCTIONS = """You are given a list of OCR-extracted text fragments with their absolute bounding boxes and page numbers.
Your ONLY task is to identify the text and exact bounding box coordinates [x_min, y_min, x_max, y_max] for each requested field.

For each field:
1. Locate the text fragment(s) that correspond to the value of the field.
2. If the value spans a single fragment, copy its bbox coordinates [x_min, y_min, x_max, y_max] and page_no.
3. If the value spans multiple fragments, compute the union of their bounding boxes: [min(x_min_all), min(y_min_all), max(x_max_all), max(y_max_all)] and set page_no.
4. Extract the exact text from the fragments. Do not invent or modify values.
5. Format the value as: {"text": "<extracted_value>", "bbox": [x_min, y_min, x_max, y_max], "page_no": <page_no>}
6. If a field is not found or not applicable, return null values: {"text": null, "bbox": null, "page_no": null}

OUTPUT FORMAT:
- Return ONLY valid JSON matching the requested structure.
- Do NOT wrap in markdown code blocks (no ```json or ```).
- Do NOT include any additional comments or explanations.
"""

def get_doctype_semantic_prompt(doc_type: str) -> str:
    schema = SEMANTIC_SCHEMAS.get(doc_type, {})
    return f"""{BASE_INSTRUCTIONS}
We are extracting data from a {doc_type} document.
Extract all fields from the OCR fragments list. Return a JSON object with this exact schema:
{json.dumps(schema, indent=2)}
"""

def get_fields_semantic_prompt(fields: list[str]) -> str:
    schema = {f: FIELD_TEMPLATE for f in fields}
    return f"""{BASE_INSTRUCTIONS}
Extract ONLY the following custom fields from the OCR fragments list. Map each field name (snake_case) to the most likely label/value found in the document:
{json.dumps(schema, indent=2)}
"""

def get_custom_semantic_prompt(custom_prompt: str) -> str:
    return f"""{BASE_INSTRUCTIONS}
Follow the user's instructions below to extract custom data from the OCR fragments list.
Ensure that every leaf value in the output is formatted as an object with {"text": "...", "bbox": [xmin, ymin, xmax, ymax], "page_no": <page_no>}.

User Instructions:
{custom_prompt}
"""
