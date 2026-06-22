import pytest
from app.services.semantic import resolve_field_bounding_boxes

def test_resolve_field_bounding_boxes_scalar():
    fragments = [
        {"text": "31.364.005.4-603.000", "bbox": [20, 101, 283, 126], "confidence": 0.9652, "page_no": 1},
        {"text": "TAMAN PONDOK JATI BLOK", "bbox": [18, 204, 445, 228], "confidence": 0.9807, "page_no": 1}
    ]
    
    extracted_json = {
        "nomor_npwp": {
            "text": "31.364.005.4-603.000",
            "bbox": [20, 101, 283, 126],
            "page_no": 1
        },
        "alamat": {
            "text": "TAMAN PONDOK JATI BLOK",
            "bbox": [15, 200, 450, 230],  # slightly larger box to check overlap matching
            "page_no": 1
        },
        "not_found": {
            "text": None,
            "bbox": None,
            "page_no": None
        }
    }
    
    resolved = resolve_field_bounding_boxes(extracted_json, fragments)
    
    # Check that confidence scores are correctly resolved via coordinate overlap
    assert resolved["nomor_npwp"]["confidence"] == 0.9652
    assert resolved["alamat"]["confidence"] == 0.9807
    assert resolved["not_found"]["confidence"] is None

def test_resolve_field_bounding_boxes_nested():
    fragments = [
        {"text": "Alice", "bbox": [100, 200, 200, 220], "confidence": 0.8, "page_no": 2}
    ]
    
    extracted_json = {
        "members": [
            {
                "nama_lengkap": {
                    "text": "Alice",
                    "bbox": [100, 200, 200, 220],
                    "page_no": 2
                }
            }
        ]
    }
    
    resolved = resolve_field_bounding_boxes(extracted_json, fragments)
    
    assert resolved["members"][0]["nama_lengkap"]["confidence"] == 0.8
    assert resolved["members"][0]["nama_lengkap"]["page_no"] == 2
