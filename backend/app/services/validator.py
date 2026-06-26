import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.core.sys_prompt import (
    KTP_SCHEMA,
    KK_SCHEMA,
    NPWP_SCHEMA,
    INVOICE_SCHEMA,
    INV_COO_SCHEMA,
    QUOTATION_SCHEMA,
    SIM_SCHEMA,
    IJAZAH_SCHEMA,
    BL_SCHEMA,
    PEB_SCHEMA,
    PL_SCHEMA,
)

def get_label_candidates(key: str) -> List[str]:
    """
    Dynamically generates potential OCR display labels for a given field key.
    Includes custom overrides for KTP, KK, NPWP, and SIM fields to ensure high-precision matching.
    """
    special_mappings = {
        # KTP
        "provinsi": ["PROVINSI"],
        "kabupaten_kota": ["KABUPATEN", "KOTA"],
        "nik": ["NIK", "N.I.K"],
        "nama": ["Nama", "NAMA"],
        "tempat_lahir": ["Tempat/Tgl Lahir", "Tempat/Tgl", "Tempat", "Lahir"],
        "tanggal_lahir": ["Tempat/Tgl Lahir", "Tempat/Tgl", "Tgl Lahir", "Tanggal Lahir"],
        "jenis_kelamin": ["Jenis Kelamin", "Jenis", "Kelamin"],
        "golongan_darah": ["Gol. Darah", "Golongan Darah", "Darah"],
        "alamat": ["Alamat", "ALAMAT"],
        "rt": ["RT/RW", "RT", "R.T"],
        "rw": ["RT/RW", "RW", "R.W"],
        "rt_rw": ["RT/RW"],
        "kelurahan_desa": ["Kel/Desa", "Kelurahan/Desa", "Kelurahan", "Desa"],
        "kecamatan": ["Kecamatan", "KECAMATAN"],
        "agama": ["Agama", "AGAMA"],
        "status_perkawinan": ["Status Perkawinan", "Status", "Perkawinan"],
        "pekerjaan": ["Pekerjaan", "PEKERJAAN"],
        "kewarganegaraan": ["Kewarganegaraan", "KEWARGANEGARAAN"],
        "berlaku_hingga": ["Berlaku Hingga", "Berlaku", "Hingga"],
        
        # KK
        "nomor_kk": ["KARTU KELUARGA", "No.", "NOMOR KK", "Nomor KK"],
        "nama_kepala_keluarga": ["Nama Kepala Keluarga", "Kepala Keluarga"],
        "desa_kelurahan": ["Desa/Kelurahan", "Kelurahan/Desa", "Desa", "Kelurahan"],
        "kode_pos": ["Kode Pos", "KODE POS"],
        
        # NPWP
        "npwp": ["NPWP", "N.P.W.P"],
        
        # SIM
        "nomor_sim": ["No. SIM", "NOMOR SIM", "SIM"],
    }
    
    key_lower = key.lower()
    if key_lower in special_mappings:
        return special_mappings[key_lower]
        
    # Dynamic fallback: snake_case -> Title Case, Space Case, UPPERCASE
    title_case = key.replace("_", " ").title()
    upper_case = key.replace("_", " ").upper()
    return [title_case, upper_case, key]


# Regex format rules for common document fields
FIELD_FORMAT_RULES = {
    # Identity IDs
    "nik": r"^\d{16}$",
    "nomor_kk": r"^\d{16}$",
    "nomor_npwp": r"^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$",
    "nomor_sim": r"^\d{12}$",

    "kode_pos": r"^\d{5}$",          # Pos code (5 digits)
    
    # Dates (support both hyphens and slashes)
    "tanggal_lahir": r"^\d{2}-\d{2}-\d{4}$",
    "tanggal_terdaftar": r"^\d{2}-\d{2}-\d{4}$",
    "tanggal_lulus": r"^\d{2}-\d{2}-\d{4}$",
    "tanggal_ijazah": r"^\d{2}-\d{2}-\d{4}$",
    "tanggal_pendaftaran": r"^\d{2}-\d{2}-\d{4}$",
    "berlaku_hingga": r"^\d{2}-\d{2}-\d{4}$|SEUMUR HIDUP",
    
    # Document specifics
    "rt_rw": r"^\d{3}/\d{3}$",
    "rt": r"^\d{3}$",
    "rw": r"^\d{3}$",
    
    # Classified / Categorical fields
    "jenis_kelamin": r"^(LAKI-LAKI|PEREMPUAN)$",
    "golongan_darah": r"^(A|B|AB|O|-)$",
    "status_perkawinan": r"^(BELUM KAWIN|KAWIN|CERAI HIDUP|CERAI MATI)$",
    "kewarganegaraan": r"^(WNI|WNA)$",
    "golongan_sim": r"^(A|A\s+Umum|B1|B1\s+Umum|B2|B2\s+Umum|C|C1|D|D1)$",
    "document_level": r"^(D3|D4|S1|S2|S3)$",
    "currency": r"^[A-Za-z]{3}|[Rp$€£¥]$",
    "agama": r"^(ISLAM|KRISTEN|KATOLIK|KATHOLIK|HINDU|BUDHA|BUDDHA|KHONGHUCU|KONGHUCU)$",
    
    # Invoice COO specific
    "model": r"^[a-zA-Z0-9]{5}/[a-zA-Z0-9]{7}$",
    "nomor_pendaftaran": r"^\d{6}$",  # PEB pendaftaran (6 digits)
    
    # Names (must be more than 2 characters)
    "nama": r"^.{3,}$",
    "nama_lengkap": r"^.{3,}$",
    "nama_kepala_keluarga": r"^.{3,}$",
    "nama_ibu": r"^.{3,}$",
    "nama_ayah": r"^.{3,}$",
    "nama_ibu_kandung": r"^.{3,}$",
}

# Map document types to their schema strings from system prompts
SCHEMAS_MAP = {
    "KTP": KTP_SCHEMA,
    "KK": KK_SCHEMA,
    "NPWP": NPWP_SCHEMA,
    "Invoice": INVOICE_SCHEMA,
    "Invoice_SPBB": INVOICE_SCHEMA,
    "INV_COO": INV_COO_SCHEMA,
    "Quotation": QUOTATION_SCHEMA,
    "SIM": SIM_SCHEMA,
    "IJAZAH": IJAZAH_SCHEMA,
    "BL": BL_SCHEMA,
    "PEB": PEB_SCHEMA,
    "PL": PL_SCHEMA,
}

def get_required_fields_from_schema(doc_type: str) -> List[str]:
    """
    Dynamically parses the top-level keys from the system prompt schema string.
    """
    schema_str = SCHEMAS_MAP.get(doc_type)
    if not schema_str:
        return []
        
    keys = []
    for line in schema_str.splitlines():
        # Match lines with 2 spaces of indentation, e.g.:   "nik": "string",
        match = re.match(r'^\s{2}"([a-zA-Z0-9_]+)"\s*:', line)
        if match:
            keys.append(match.group(1))
    return keys

def validate_field(field_name: str, value: Any) -> List[str]:
    """
    Performs up to 5 validation checks on a field's value.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    
    # Check 1: Presence Check (Is empty or null?)
    if value is None or str(value).strip().lower() in ("", "null", "none"):
        errors.append("Field is missing or empty")
        return errors
        
    value_str = str(value).strip()
    
    # Check 2: Format (Regex rule check)
    pattern = FIELD_FORMAT_RULES.get(field_name)
    if pattern:
        if not re.match(pattern, value_str, re.IGNORECASE):
            if "nama" in field_name.lower():
                errors.append("Format mismatch: name must contain more than 2 characters")
            else:
                errors.append(f"Format mismatch: does not match pattern {pattern}")
            
    # Check 3: Length Check (Field-specific length validations)
    if field_name in ("nik", "nomor_kk"):
        if len(value_str) != 16:
            errors.append(f"Length mismatch: must be exactly 16 digits, got {len(value_str)}")
    elif field_name == "nomor_sim":
        if len(value_str) != 12:
            errors.append(f"Length mismatch: must be exactly 12 digits, got {len(value_str)}")
            
    # Check 4: Character Type Check
    if field_name in ("nik", "nomor_kk", "nomor_sim", "rt", "rw", "nomor_pendaftaran", "kode_pos"):
        if not value_str.isdigit():
            errors.append("Character mismatch: must contain digits only")
            
    # Check 5: Logical / Value Range Check (e.g. valid Date parsing)
    is_date_field = "tanggal" in field_name or "date" in field_name or field_name == "berlaku_hingga"
    if is_date_field:
        if value_str.upper() != "SEUMUR HIDUP":
            # Attempt to parse as date to verify logical correctness
            parsed = False
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d %b %Y", "%b %d, %Y"):
                try:
                    datetime.strptime(value_str, fmt)
                    parsed = True
                    break
                except ValueError:
                    continue
            if not parsed:
                errors.append("Logical validation failure: not a valid calendar date format")
                
    return errors

def compute_validation_summary(doc_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes overall validation summary for the parsed document data.
    """
    required = get_required_fields_from_schema(doc_type)
    print(required)
    field_reports = {}
    valid_fields_count = 0
    total_checked = 0
    
    # Check required fields
    for field in required:
        val = data.get(field)
        # Skip lists or complex objects for simple field validation checks
        if isinstance(val, (dict, list)):
            field_reports[field] = {"valid": True, "errors": []}
            valid_fields_count += 1
            total_checked += 1
            continue
            
        errors = validate_field(field, val)
        is_valid = len(errors) == 0
        field_reports[field] = {
            "valid": is_valid,
            "errors": errors
        }
        total_checked += 1
        if is_valid:
            valid_fields_count += 1
            
    accuracy_score = round(valid_fields_count / max(1, total_checked), 4)
    
    return {
        "document_type": doc_type,
        "is_complete": all(r["valid"] for r in field_reports.values()),
        "accuracy_score": accuracy_score,
        "fields": field_reports
    }
