"""
Grounded Resolver — Resolves VLM extraction output using Fragment IDs.

Instead of fuzzy string matching, this resolver looks up Fragment IDs
directly in the FragmentStore to attach bounding boxes, confidence scores,
and page numbers to extracted values.

Falls back to the legacy fuzzy resolver when the VLM output does not
contain valid Fragment ID references.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.services.validator import validate_field, get_label_candidates, validate_grounded_field
from app.services.confidence_engine import compute_composite_confidence
from app.services.fuzzy_resolver import fuzzy_locate_value

if TYPE_CHECKING:
    from app.services.fragment_store import FragmentStore


def _is_grounded_value(val: Any) -> bool:
    """Check if a value follows the grounded format: {value: ..., sources: [...]}."""
    return (
        isinstance(val, dict)
        and "value" in val
        and "sources" in val
        and isinstance(val["sources"], list)
    )

def is_any_field_grounded(val: Any) -> bool:
    """Check recursively if any field in the JSON structure has grounded format."""
    if _is_grounded_value(val):
        return True
    if isinstance(val, dict):
        return any(is_any_field_grounded(v) for v in val.values())
    if isinstance(val, list):
        return any(is_any_field_grounded(item) for item in val)
    return False

def _resolve_single_field(
    key: str,
    grounded_val: dict,
    store: "FragmentStore",
    show_only_mismatch: bool,
    fallback_fn: Optional[callable] = None,
) -> Any:
    """
    Resolve a single grounded field {value, sources} into the final output format.

    Output format:
    {
        "text": "3173010203040001",
        "bbox": [120, 320, 480, 350],
        "confidence": 0.98,
        "page_no": 1,
        "status": "verified" | "value_mismatch" | ...,
        "ocr_text": "3173010203040001",
        "validation_errors": null
    }
    """
    value = grounded_val.get("value")
    sources = grounded_val.get("sources", [])

    # Normalize value
    value_str = "" if value is None else str(value).strip()
    is_missing = not value_str or value_str.lower() in ("null", "none", "-")

    # Resolve sources from FragmentStore
    resolved = store.resolve_sources(sources)
    bbox = resolved["bbox"]
    ocr_confidence = resolved["confidence"]
    page_no = resolved["page_no"]
    ocr_text = resolved["ocr_text"]
    fragments_found = resolved["fragments_found"]

    if fragments_found == 0 and not is_missing:
        if fallback_fn:
            return fallback_fn(value_str, key)
        f_bbox, f_conf, f_page, f_matched, f_found = fuzzy_locate_value(
            key, value_str, store.to_ocr_fragments()
        )
        if f_bbox is not None:
            bbox = f_bbox
            ocr_confidence = f_conf
            page_no = f_page
            ocr_text = f_matched
            fragments_found = f_found

    # Use validate_grounded_field for validation and status determination
    total_sources = len(sources)
    val_res = validate_grounded_field(
        key,
        value_str,
        ocr_text,
        ocr_confidence,
        fragments_found,
        total_sources
    )
    val_errors = val_res["errors"]
    status = val_res["status"]

    if is_missing:
        if bbox is None:
            return None
        return {
            "text": None,
            "bbox": bbox,
            "confidence": ocr_confidence,
            "page_no": page_no,
            "status": "not_found",
            "ocr_text": ocr_text,
            "validation_errors": val_errors if val_errors else None,
        }

    # Compute composite confidence score
    def clean(s):
        return re.sub(r"[\s\W_]+", "", s.lower()) if s else ""
    semantic_match = False
    if fragments_found > 0 and ocr_text:
        semantic_match = clean(value_str) == clean(ocr_text)

    validation_passed = len(val_errors) == 0
    document_rule_passed = True  # Extended in future rule engines

    confidence = compute_composite_confidence(
        ocr_confidence,
        semantic_match,
        validation_passed,
        document_rule_passed
    )

    # If show_only_mismatch and the field is verified, return plain value
    if show_only_mismatch and status == "verified":
        return value_str

    return {
        "text": None if is_missing else value_str,
        "bbox": bbox,
        "confidence": confidence,
        "page_no": page_no,
        "status": status,
        "ocr_text": ocr_text,
        "validation_errors": val_errors if val_errors else None,
    }



def resolve_grounded_json(
    extracted_json: Any,
    store: "FragmentStore",
    show_only_mismatch: bool = False,
    current_key: str = "",
    fallback_fn: Optional[callable] = None,
) -> Any:
    """
    Recursively traverse JSON output from VLM and resolve grounded values.

    If a value has the grounded format {value, sources}, resolve it via
    FragmentStore lookup. Otherwise, pass through unchanged.

    This function handles:
    - Scalar grounded values: {"nik": {"value": "...", "sources": ["F0002"]}}
    - Nested dicts: {"address": {"street": {"value": "...", "sources": [...]}}}
    - Arrays/tables: {"table": [{"col": {"value": "...", "sources": [...]}}]}
    - Mixed: some fields grounded, some plain (for backward compat)
    """
    if extracted_json is None:
        return None

    # Grounded leaf node
    if _is_grounded_value(extracted_json):
        return _resolve_single_field(
            current_key, extracted_json, store, show_only_mismatch, fallback_fn
        )

    # Dict with nested keys (but not a grounded value itself)
    if isinstance(extracted_json, dict):
        result = {}
        for k, v in extracted_json.items():
            result[k] = resolve_grounded_json(
                v, store, show_only_mismatch, current_key=k, fallback_fn=fallback_fn
            )
        return result

    # Array
    if isinstance(extracted_json, list):
        return [
            resolve_grounded_json(item, store, show_only_mismatch, current_key, fallback_fn)
            for item in extracted_json
        ]

    # Plain scalar (string, number, boolean) — not grounded, resolve via fuzzy matching fallback
    if isinstance(extracted_json, (str, int, float, bool)) or extracted_json is None:
        wrapped = {"value": extracted_json, "sources": []}
        return _resolve_single_field(
            current_key, wrapped, store, show_only_mismatch, fallback_fn
        )

    return extracted_json
