import pytest
from app.services.validator import validate_field, get_required_fields_from_schema, validate_grounded_field

def test_get_required_fields_from_schema():
    ktp_fields = get_required_fields_from_schema("KTP")
    assert "nik" in ktp_fields
    assert "nama" in ktp_fields
    assert "rt_rw" in ktp_fields
    assert "berlaku_hingga" in ktp_fields
    
    kk_fields = get_required_fields_from_schema("KK")
    assert "nomor_kk" in kk_fields
    assert "members" in kk_fields

def test_validate_field_presence():
    # Test missing/empty values
    assert "Field is missing or empty" in validate_field("nik", None)[0]
    assert "Field is missing or empty" in validate_field("nama", "")[0]
    assert "Field is missing or empty" in validate_field("alamat", "None")[0]
    assert "Field is missing or empty" in validate_field("nik", "  ")[0]

def test_validate_field_nik():
    # Valid NIK
    assert len(validate_field("nik", "1234567890123456")) == 0
    # Invalid length
    errs = validate_field("nik", "123456")
    assert any("Length mismatch" in e for e in errs)
    # Invalid characters
    errs = validate_field("nik", "123456789012345a")
    assert any("Character mismatch" in e for e in errs)

def test_validate_field_npwp():
    # Valid NPWP format: XX.XXX.XXX.X-XXX.XXX
    assert len(validate_field("nomor_npwp", "12.345.678.9-012.345")) == 0
    # Invalid format
    errs = validate_field("nomor_npwp", "123456789")
    assert any("Format mismatch" in e for e in errs)

def test_validate_field_date():
    # Valid dates
    assert len(validate_field("tanggal_lahir", "10-10-1990")) == 0
    assert len(validate_field("berlaku_hingga", "SEUMUR HIDUP")) == 0
    # Invalid logical date
    errs = validate_field("tanggal_lahir", "32-13-2020")
    assert any("Logical validation failure" in e for e in errs)


def test_new_validation_rules():
    # rt_rw
    assert len(validate_field("rt_rw", "003/007")) == 0
    assert len(validate_field("rt_rw", "12/34")) > 0
    
    # jenis_kelamin
    assert len(validate_field("jenis_kelamin", "LAKI-LAKI")) == 0
    assert len(validate_field("jenis_kelamin", "PEREMPUAN")) == 0
    assert len(validate_field("jenis_kelamin", "PRIA")) > 0
    
    # golongan_darah
    assert len(validate_field("golongan_darah", "A")) == 0
    assert len(validate_field("golongan_darah", "-")) == 0
    assert len(validate_field("golongan_darah", "Z")) > 0
    
    # status_perkawinan
    assert len(validate_field("status_perkawinan", "BELUM KAWIN")) == 0
    assert len(validate_field("status_perkawinan", "DUDA")) > 0
    
    # golongan_sim
    assert len(validate_field("golongan_sim", "A")) == 0
    assert len(validate_field("golongan_sim", "B1 Umum")) == 0
    assert len(validate_field("golongan_sim", "E")) > 0
    
    # model (INV_COO specific)
    assert len(validate_field("model", "J890L/46U3KBN")) == 0
    assert len(validate_field("model", "J890L-46U3KBN")) > 0
    
    # kode_pos
    assert len(validate_field("kode_pos", "12345")) == 0
    assert len(validate_field("kode_pos", "1234")) > 0

    # nama (> 2 characters)
    assert len(validate_field("nama", "BUDI SANTOSO SUDRAJAT")) == 0
    assert len(validate_field("nama_lengkap", "Mhd. Syarifuddin Siregar")) == 0
    assert len(validate_field("nama", "BUDI SANTOSO")) == 0
    assert len(validate_field("nama", "BUDI")) == 0
    assert len(validate_field("nama", "SE")) > 0
    assert len(validate_field("nama", "A")) > 0
    errs = validate_field("nama", "SE")
    assert any("must contain more than 2 characters" in e for e in errs)


def test_get_label_candidates():
    from app.services.validator import get_label_candidates
    
    # Overridden keys
    assert "PROVINSI" in get_label_candidates("provinsi")
    assert "Gol. Darah" in get_label_candidates("golongan_darah")
    assert "Tempat/Tgl Lahir" in get_label_candidates("tempat_lahir")
    
    # Dynamic fallback keys
    assert "Invoice Date" in get_label_candidates("invoice_date")
    assert "TOTAL AMOUNT" in get_label_candidates("total_amount")
    assert "custom_field" in get_label_candidates("custom_field")


def test_validate_grounded_field():
    # 1. verified status
    res = validate_grounded_field(
        field_name="nik",
        value="1234567890123456",
        ocr_text="1234567890123456",
        confidence=0.95,
        fragments_found=1,
        total_sources=1
    )
    assert res["status"] == "verified"
    assert res["valid"] is True
    assert len(res["errors"]) == 0

    # 2. value_mismatch status
    res = validate_grounded_field(
        field_name="nik",
        value="1234567890123456",
        ocr_text="1234567890123455",
        confidence=0.95,
        fragments_found=1,
        total_sources=1
    )
    assert res["status"] == "value_mismatch"
    assert res["valid"] is False

    # 3. format_invalid status
    res = validate_grounded_field(
        field_name="nik",
        value="12345",
        ocr_text="12345",
        confidence=0.95,
        fragments_found=1,
        total_sources=1
    )
    assert res["status"] == "format_invalid"
    assert res["valid"] is False

    # 4. partial_match status
    res = validate_grounded_field(
        field_name="alamat",
        value="JL MELATI",
        ocr_text="JL MELATI",
        confidence=0.95,
        fragments_found=1,
        total_sources=2
    )
    assert res["status"] == "partial_match"
    assert res["valid"] is True

    # 5. low_confidence status
    res = validate_grounded_field(
        field_name="nama",
        value="BUDI",
        ocr_text="BUDI",
        confidence=0.70,
        fragments_found=1,
        total_sources=1
    )
    assert res["status"] == "low_confidence"
    assert res["valid"] is True



