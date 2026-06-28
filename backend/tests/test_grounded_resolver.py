"""Tests for Grounded Resolver — Resolves VLM extraction using Fragment IDs."""

import pytest
from app.services.fragment_store import FragmentStore
from app.services.grounded_resolver import resolve_grounded_json, is_any_field_grounded


def test_is_any_field_grounded():
    # Grounded value check
    assert is_any_field_grounded({"nik": {"value": "123", "sources": ["F0001"]}}) is True
    assert is_any_field_grounded({"nik": "123"}) is False
    assert is_any_field_grounded({"nested": {"nik": {"value": "123", "sources": ["F0001"]}}}) is True
    assert is_any_field_grounded([{"value": "123", "sources": []}]) is True
    assert is_any_field_grounded(None) is False


def test_resolve_single_source():
    store = FragmentStore()
    store.add(
        text="1234567890123456",
        bbox=[100, 200, 300, 220],
        confidence=0.98,
        page_no=1,
    )

    extracted = {
        "nik": {
            "value": "1234567890123456",
            "sources": ["F0001"]
        }
    }

    resolved = resolve_grounded_json(extracted, store)
    assert resolved["nik"]["text"] == "1234567890123456"
    assert resolved["nik"]["bbox"] == [100, 200, 300, 220]
    # Composite confidence: 0.4*0.98 + 0.3*1.0 + 0.2*1.0 + 0.1*1.0 = 0.992
    assert resolved["nik"]["confidence"] == 0.992
    assert resolved["nik"]["page_no"] == 1
    assert resolved["nik"]["status"] == "verified"


def test_resolve_multi_source():
    store = FragmentStore()
    store.add(text="JL", bbox=[100, 400, 130, 420], confidence=0.95, page_no=1)
    store.add(text="MELATI", bbox=[140, 400, 220, 420], confidence=0.92, page_no=1)
    store.add(text="NO 10", bbox=[230, 400, 300, 420], confidence=0.90, page_no=1)

    extracted = {
        "alamat": {
            "value": "JL MELATI NO 10",
            "sources": ["F0001", "F0002", "F0003"]
        }
    }

    resolved = resolve_grounded_json(extracted, store)
    assert resolved["alamat"]["text"] == "JL MELATI NO 10"
    assert resolved["alamat"]["bbox"] == [100, 400, 300, 420]
    # Average OCR: 0.9233. Composite: 0.4*0.9233 + 0.3*1.0 + 0.2*1.0 + 0.1*1.0 = 0.9693
    assert resolved["alamat"]["confidence"] == 0.9693
    assert resolved["alamat"]["status"] == "verified"
    assert resolved["alamat"]["ocr_text"] == "JL MELATI NO 10"


def test_status_determination_mismatch_and_low_confidence():
    store = FragmentStore()
    # Mismatch case
    store.add(text="BUDI", bbox=[100, 200, 200, 220], confidence=0.95, page_no=1)
    # Low confidence case
    store.add(text="SANTOSO", bbox=[100, 300, 200, 320], confidence=0.75, page_no=1)

    extracted = {
        "nama": {
            "value": "BUDY",
            "sources": ["F0001"]
        },
        "nama_belakang": {
            "value": "SANTOSO",
            "sources": ["F0002"]
        }
    }

    resolved = resolve_grounded_json(extracted, store)
    assert resolved["nama"]["status"] == "value_mismatch"
    assert resolved["nama_belakang"]["status"] == "low_confidence"


def test_fallback_to_fuzzy():
    # Setup store
    store = FragmentStore()
    store.add(
        text="3173010203040001",
        bbox=[100, 200, 300, 220],
        confidence=0.98,
        page_no=1,
    )

    # We pass a custom fallback function
    def fake_fallback(val, key):
        return {
            "text": val,
            "bbox": [50, 50, 150, 100],
            "confidence": 0.88,
            "page_no": 1,
            "status": "fuzzy_fallback",
            "validation_errors": None,
        }

    extracted = {
        "nik": {
            "value": "3173010203040001",
            "sources": ["F9999"]  # invalid ID
        }
    }

    resolved = resolve_grounded_json(extracted, store, fallback_fn=fake_fallback)
    assert resolved["nik"]["status"] == "fuzzy_fallback"
    assert resolved["nik"]["bbox"] == [50, 50, 150, 100]


def test_nested_fields_and_arrays():
    store = FragmentStore()
    store.add(text="ITEM1", bbox=[10, 10, 50, 20], confidence=0.9, page_no=1)
    store.add(text="100", bbox=[60, 10, 90, 20], confidence=0.95, page_no=1)

    extracted = {
        "table": [
            {
                "item": {"value": "ITEM1", "sources": ["F0001"]},
                "price": {"value": "100", "sources": ["F0002"]}
            }
        ]
    }

    resolved = resolve_grounded_json(extracted, store)
    assert isinstance(resolved["table"], list)
    assert resolved["table"][0]["item"]["text"] == "ITEM1"
    assert resolved["table"][0]["price"]["text"] == "100"
    assert resolved["table"][0]["item"]["status"] == "verified"


def test_fuzzy_locate_fallback():
    # Setup store with some fragments
    store = FragmentStore()
    store.add(
        text="PROVINSI DKI JAKARTA",
        bbox=[50, 10, 150, 25],
        confidence=0.96,
        page_no=1,
    )
    store.add(
        text="3175075410770010",
        bbox=[100, 50, 250, 70],
        confidence=0.98,
        page_no=1,
    )
    
    # Value is flat/un-grounded
    extracted = {
        "nik": "3175075410770010",
        "provinsi": "DKI JAKARTA"
    }
    
    resolved = resolve_grounded_json(extracted, store, show_only_mismatch=False)
    
    # NIK was located fuzzy and validated
    assert resolved["nik"]["text"] == "3175075410770010"
    assert resolved["nik"]["bbox"] == [100, 50, 250, 70]
    assert resolved["nik"]["status"] == "verified"
    assert resolved["nik"]["ocr_text"] == "3175075410770010"
    
    # Provinsi was located fuzzy and verified
    assert resolved["provinsi"]["text"] == "DKI JAKARTA"
    assert resolved["provinsi"]["bbox"] == [50, 10, 150, 25]
    assert resolved["provinsi"]["status"] == "verified"

