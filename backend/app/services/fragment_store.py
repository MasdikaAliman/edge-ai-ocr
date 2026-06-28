"""
Fragment Store — Single source of truth for all OCR fragments during a pipeline request.

Each fragment produced by PaddleOCR is assigned a unique, deterministic ID (F0001, F0002, ...)
and stored here. All downstream components (prompt builder, resolver, confidence engine)
reference fragments by ID rather than performing fuzzy text matching.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Fragment:
    """Immutable representation of a single OCR text fragment."""
    id: str
    text: str
    bbox: List[int]       # [xmin, ymin, xmax, ymax] absolute pixels
    confidence: float     # 0.0–1.0 from PaddleOCR
    page_no: int
    line_no: Optional[int] = None
    word_order: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "bbox": list(self.bbox),
            "confidence": self.confidence,
            "page_no": self.page_no,
            "line_no": self.line_no,
            "word_order": self.word_order,
        }


class FragmentStore:
    """
    In-memory store for OCR fragments scoped to a single pipeline request.

    Usage:
        store = FragmentStore()
        frag = store.add(text="NIK", bbox=[10,20,100,40], confidence=0.95, page_no=1)
        print(frag.id)  # "F0001"
        retrieved = store.get("F0001")
    """

    def __init__(self) -> None:
        self._fragments: Dict[str, Fragment] = {}
        self._counter: int = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"F{self._counter:04d}"

    def add(
        self,
        text: str,
        bbox: List[int],
        confidence: float,
        page_no: int,
        line_no: Optional[int] = None,
        word_order: Optional[int] = None,
    ) -> Fragment:
        """Add a new fragment and return it with its assigned ID."""
        fid = self._next_id()
        frag = Fragment(
            id=fid,
            text=text,
            bbox=list(bbox),
            confidence=round(float(confidence), 4),
            page_no=page_no,
            line_no=line_no,
            word_order=word_order,
        )
        self._fragments[fid] = frag
        return frag

    def add_from_ocr_fragment(self, ocr_frag: Dict[str, Any]) -> Fragment:
        """Convenience method to add from an OCRFragment TypedDict."""
        return self.add(
            text=ocr_frag["text"],
            bbox=ocr_frag["bbox"],
            confidence=ocr_frag["confidence"],
            page_no=ocr_frag["page_no"],
        )

    def get(self, fragment_id: str) -> Optional[Fragment]:
        """Lookup a fragment by its ID. Returns None if not found."""
        return self._fragments.get(fragment_id)

    def get_page(self, page_no: int) -> List[Fragment]:
        """Return all fragments for a given page, ordered by ID."""
        return [
            f for f in self._fragments.values()
            if f.page_no == page_no
        ]

    def get_all(self) -> List[Fragment]:
        """Return all fragments ordered by ID."""
        return list(self._fragments.values())

    def resolve_sources(
        self, source_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Given a list of fragment IDs, compute the union bounding box,
        average confidence, and page number.

        Returns a dict with keys: bbox, confidence, page_no, ocr_text, fragments_found.
        If no valid sources are found, all values are None.
        """
        found: List[Fragment] = []
        for sid in source_ids:
            frag = self.get(sid)
            if frag is not None:
                found.append(frag)

        if not found:
            return {
                "bbox": None,
                "confidence": None,
                "page_no": None,
                "ocr_text": None,
                "fragments_found": 0,
            }

        # Union bounding box
        xmin = min(f.bbox[0] for f in found)
        ymin = min(f.bbox[1] for f in found)
        xmax = max(f.bbox[2] for f in found)
        ymax = max(f.bbox[3] for f in found)

        # Average confidence
        avg_conf = round(sum(f.confidence for f in found) / len(found), 4)

        # Combined OCR text (ordered by page, then y, then x)
        sorted_frags = sorted(
            found,
            key=lambda f: (f.page_no, f.bbox[1], f.bbox[0])
        )
        ocr_text = " ".join(f.text for f in sorted_frags)

        # Page number — use the first fragment's page (most common case is single page)
        page_no = sorted_frags[0].page_no

        return {
            "bbox": [xmin, ymin, xmax, ymax],
            "confidence": avg_conf,
            "page_no": page_no,
            "ocr_text": ocr_text,
            "fragments_found": len(found),
        }

    def to_ocr_fragments(self) -> List[Dict[str, Any]]:
        """Convert all fragments back to OCRFragment-compatible dicts for backward compatibility."""
        return [
            {
                "text": f.text,
                "bbox": list(f.bbox),
                "confidence": f.confidence,
                "page_no": f.page_no,
                "fragment_id": f.id,
            }
            for f in self._fragments.values()
        ]

    def __len__(self) -> int:
        return len(self._fragments)

    def __contains__(self, fragment_id: str) -> bool:
        return fragment_id in self._fragments
