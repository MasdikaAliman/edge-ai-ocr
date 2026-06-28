"""Tests for FragmentStore — the single source of truth for OCR fragments."""

import pytest
from app.services.fragment_store import Fragment, FragmentStore


class TestFragment:
    """Tests for the Fragment dataclass."""

    def test_fragment_creation(self):
        frag = Fragment(
            id="F0001",
            text="3173010203040001",
            bbox=[125, 320, 480, 350],
            confidence=0.98,
            page_no=1,
        )
        assert frag.id == "F0001"
        assert frag.text == "3173010203040001"
        assert frag.bbox == [125, 320, 480, 350]
        assert frag.confidence == 0.98
        assert frag.page_no == 1
        assert frag.line_no is None
        assert frag.word_order is None

    def test_fragment_to_dict(self):
        frag = Fragment(
            id="F0002",
            text="BUDI",
            bbox=[100, 200, 200, 220],
            confidence=0.95,
            page_no=1,
            line_no=3,
            word_order=1,
        )
        d = frag.to_dict()
        assert d == {
            "id": "F0002",
            "text": "BUDI",
            "bbox": [100, 200, 200, 220],
            "confidence": 0.95,
            "page_no": 1,
            "line_no": 3,
            "word_order": 1,
        }


class TestFragmentStore:
    """Tests for the FragmentStore class."""

    def test_add_and_get(self):
        store = FragmentStore()
        frag = store.add(
            text="NIK",
            bbox=[10, 20, 100, 40],
            confidence=0.95,
            page_no=1,
        )
        assert frag.id == "F0001"
        assert frag.text == "NIK"

        retrieved = store.get("F0001")
        assert retrieved is not None
        assert retrieved.text == "NIK"
        assert retrieved.id == "F0001"

    def test_sequential_ids(self):
        store = FragmentStore()
        f1 = store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)
        f2 = store.add(text="B", bbox=[20, 0, 30, 10], confidence=0.8, page_no=1)
        f3 = store.add(text="C", bbox=[40, 0, 50, 10], confidence=0.7, page_no=1)

        assert f1.id == "F0001"
        assert f2.id == "F0002"
        assert f3.id == "F0003"

    def test_get_nonexistent_returns_none(self):
        store = FragmentStore()
        assert store.get("F9999") is None

    def test_add_from_ocr_fragment(self):
        store = FragmentStore()
        ocr_frag = {
            "text": "3173010203040001",
            "bbox": [125, 320, 480, 350],
            "confidence": 0.98,
            "page_no": 1,
        }
        frag = store.add_from_ocr_fragment(ocr_frag)
        assert frag.id == "F0001"
        assert frag.text == "3173010203040001"
        assert frag.confidence == 0.98

    def test_get_page(self):
        store = FragmentStore()
        store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)
        store.add(text="B", bbox=[20, 0, 30, 10], confidence=0.8, page_no=2)
        store.add(text="C", bbox=[40, 0, 50, 10], confidence=0.7, page_no=1)
        store.add(text="D", bbox=[60, 0, 70, 10], confidence=0.6, page_no=2)

        page1 = store.get_page(1)
        assert len(page1) == 2
        assert {f.text for f in page1} == {"A", "C"}

        page2 = store.get_page(2)
        assert len(page2) == 2
        assert {f.text for f in page2} == {"B", "D"}

        page3 = store.get_page(3)
        assert len(page3) == 0

    def test_get_all(self):
        store = FragmentStore()
        store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)
        store.add(text="B", bbox=[20, 0, 30, 10], confidence=0.8, page_no=1)

        all_frags = store.get_all()
        assert len(all_frags) == 2
        assert all_frags[0].id == "F0001"
        assert all_frags[1].id == "F0002"

    def test_resolve_sources_single(self):
        store = FragmentStore()
        store.add(text="3173010203040001", bbox=[125, 320, 480, 350], confidence=0.98, page_no=1)

        result = store.resolve_sources(["F0001"])
        assert result["bbox"] == [125, 320, 480, 350]
        assert result["confidence"] == 0.98
        assert result["page_no"] == 1
        assert result["ocr_text"] == "3173010203040001"
        assert result["fragments_found"] == 1

    def test_resolve_sources_multiple(self):
        store = FragmentStore()
        store.add(text="JL", bbox=[100, 400, 130, 420], confidence=0.95, page_no=1)
        store.add(text="MELATI", bbox=[140, 400, 220, 420], confidence=0.92, page_no=1)
        store.add(text="NO 10", bbox=[230, 400, 300, 420], confidence=0.90, page_no=1)

        result = store.resolve_sources(["F0001", "F0002", "F0003"])
        # Union bbox
        assert result["bbox"] == [100, 400, 300, 420]
        # Average confidence
        expected_conf = round((0.95 + 0.92 + 0.90) / 3, 4)
        assert result["confidence"] == expected_conf
        assert result["page_no"] == 1
        assert result["ocr_text"] == "JL MELATI NO 10"
        assert result["fragments_found"] == 3

    def test_resolve_sources_empty(self):
        store = FragmentStore()
        store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)

        result = store.resolve_sources([])
        assert result["bbox"] is None
        assert result["confidence"] is None
        assert result["page_no"] is None
        assert result["ocr_text"] is None
        assert result["fragments_found"] == 0

    def test_resolve_sources_invalid_ids(self):
        store = FragmentStore()
        store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)

        result = store.resolve_sources(["F9999", "FXXXX"])
        assert result["bbox"] is None
        assert result["fragments_found"] == 0

    def test_resolve_sources_partial_valid(self):
        store = FragmentStore()
        store.add(text="BUDI", bbox=[100, 200, 200, 220], confidence=0.95, page_no=1)

        # Mix of valid and invalid IDs
        result = store.resolve_sources(["F0001", "F9999"])
        assert result["bbox"] == [100, 200, 200, 220]
        assert result["confidence"] == 0.95
        assert result["fragments_found"] == 1

    def test_to_ocr_fragments(self):
        store = FragmentStore()
        store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)
        store.add(text="B", bbox=[20, 0, 30, 10], confidence=0.8, page_no=2)

        ocr_frags = store.to_ocr_fragments()
        assert len(ocr_frags) == 2
        assert ocr_frags[0]["text"] == "A"
        assert ocr_frags[0]["fragment_id"] == "F0001"
        assert ocr_frags[1]["text"] == "B"
        assert ocr_frags[1]["fragment_id"] == "F0002"

    def test_len_and_contains(self):
        store = FragmentStore()
        assert len(store) == 0
        assert "F0001" not in store

        store.add(text="A", bbox=[0, 0, 10, 10], confidence=0.9, page_no=1)
        assert len(store) == 1
        assert "F0001" in store
        assert "F0002" not in store

    def test_confidence_rounding(self):
        store = FragmentStore()
        frag = store.add(
            text="test",
            bbox=[0, 0, 10, 10],
            confidence=0.123456789,
            page_no=1,
        )
        assert frag.confidence == 0.1235

    def test_bbox_is_copy(self):
        """Ensure that modifying the input bbox doesn't mutate the stored fragment."""
        store = FragmentStore()
        original_bbox = [10, 20, 30, 40]
        frag = store.add(text="X", bbox=original_bbox, confidence=0.9, page_no=1)

        # Mutate the original
        original_bbox[0] = 999
        assert frag.bbox[0] == 10  # Fragment should be unaffected

    def test_multi_page_resolve_sources(self):
        """When sources span multiple pages, page_no should be from the first fragment."""
        store = FragmentStore()
        store.add(text="Page1Text", bbox=[10, 10, 100, 30], confidence=0.9, page_no=1)
        store.add(text="Page2Text", bbox=[10, 10, 100, 30], confidence=0.8, page_no=2)

        result = store.resolve_sources(["F0001", "F0002"])
        assert result["page_no"] == 1
        assert result["fragments_found"] == 2
        assert result["ocr_text"] == "Page1Text Page2Text"
