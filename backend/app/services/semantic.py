import json
import asyncio
import re
from collections import Counter
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from PIL import Image
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import model, MODEL_NAME, logger
from app.services.pdf import PageImage
from app.services.ocr_engine import run_ocr_on_image, OCRFragment
from app.core.semantic_prompt import (
    get_doctype_semantic_prompt,
    get_fields_semantic_prompt,
    get_custom_semantic_prompt,
    sanitize_custom_prompt
)
from app.core.sys_prompt import _LAST_VALUE_FIELDS, get_aggregate_prompt
from app.utils.parsing import clean_json_response
from app.utils.errors import handle_llm_exception
from app.utils.image import pil_to_content_item
from app.services.validator import get_label_candidates, validate_field


def find_fuzzy_substring(full_text: str, query: str) -> Optional[tuple[int, int]]:
    # Normalize query by escaping special characters, and converting spaces/punctuation to flexible patterns
    words = re.findall(r"\w+|[^\w\s]", query)
    if not words:
        return None
        
    pattern_parts = []
    for i, w in enumerate(words):
        if w.isalnum():
            # Use word boundaries if it's a short word (e.g. <= 3 characters) to prevent false matches inside larger words
            if len(w) <= 3:
                pattern_parts.append(rf"\b{re.escape(w)}\b")
            else:
                pattern_parts.append(re.escape(w))
        else:
            pattern_parts.append(re.escape(w))
        if i < len(words) - 1:
            pattern_parts.append(r"[\s\W]*")
            
    pattern = "".join(pattern_parts)
    try:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            return match.start(), match.end()
    except Exception:
        pass
        
    # Fallback to direct lowercase substring search with boundary checks for short queries
    query_clean = query.strip()
    idx = 0
    while True:
        idx = full_text.lower().find(query_clean.lower(), idx)
        if idx == -1:
            break
        
        # If it's a short query, verify word boundary
        if len(query_clean) <= 3:
            start_ok = (idx == 0 or not full_text[idx - 1].isalnum())
            end_idx = idx + len(query_clean)
            end_ok = (end_idx == len(full_text) or not full_text[end_idx].isalnum())
            if start_ok and end_ok:
                return idx, end_idx
        else:
            return idx, idx + len(query_clean)
            
        idx += 1
        
    # Fallback to sliding window token-based fuzzy matching using difflib
    tokens = []
    for m in re.finditer(r"\S+", full_text):
        tokens.append({
            "text": m.group(0),
            "start": m.start(),
            "end": m.end()
        })
    if tokens:
        query_clean = query.strip()
        query_tokens = re.findall(r"\S+", query_clean)
        n_query = len(query_tokens)
        if n_query > 0:
            best_score = 0.0
            best_range = None
            
            # Sliding window size from max(1, n_query - 2) to n_query + 2
            min_size = max(1, n_query - 2)
            max_size = n_query + 2
            
            import difflib
            for size in range(min_size, max_size + 1):
                for i in range(len(tokens) - size + 1):
                    window = tokens[i : i + size]
                    start_idx = window[0]["start"]
                    end_idx = window[-1]["end"]
                    candidate = full_text[start_idx:end_idx]
                    
                    score = difflib.SequenceMatcher(None, candidate.lower(), query_clean.lower()).ratio()
                    if score > best_score:
                        best_score = score
                        best_range = (start_idx, end_idx)
                        
            # Determine threshold based on query length to prevent false matches on short strings
            if len(query_clean) == 1:
                threshold = 1.0
            elif len(query_clean) == 2:
                threshold = 0.8
            else:
                threshold = 0.7
                
            if best_score >= threshold and best_range is not None:
                # If short query, also check boundary for candidate
                if len(query_clean) <= 3:
                    cand_text = full_text[best_range[0]:best_range[1]]
                    if len(cand_text.strip()) == len(query_clean):
                        return best_range
                else:
                    return best_range
        
    return None


def locate_text_in_fragments(
    query: str, 
    fragments: List[OCRFragment]
) -> tuple[Optional[List[int]], Optional[float], Optional[int], Optional[str]]:
    """
    Locates the query text in the list of fragments.
    Returns (bbox, confidence, page_no) if found, otherwise (None, None, None).
    """
    if not fragments or not query:
        return None, None, None, None

    # Group fragments by page
    pages_fragments = {}
    for frag in fragments:
        p = frag.get("page_no", 1)
        pages_fragments.setdefault(p, []).append(frag)

    # Let's search page by page
    for page_no, page_frags in sorted(pages_fragments.items()):
        # Sort fragments on this page: top-to-bottom, left-to-right
        sorted_frags = sorted(page_frags, key=lambda f: (round(f["bbox"][1] / 10) * 10, f["bbox"][0]))
        
        # Build a single continuous text string and mapping
        full_text = ""
        char_to_frag_idx = []
        
        for idx, frag in enumerate(sorted_frags):
            frag_text = frag["text"]
            if full_text:
                full_text += " "
                char_to_frag_idx.append(-1)
                
            for _ in range(len(frag_text)):
                char_to_frag_idx.append(idx)
            full_text += frag_text

        match = find_fuzzy_substring(full_text, query)
        if match:
            start_char_idx, end_char_idx = match
            overlapping_frag_indices = set()
            for c_idx in range(start_char_idx, min(end_char_idx, len(char_to_frag_idx))):
                f_idx = char_to_frag_idx[c_idx]
                if f_idx != -1:
                    overlapping_frag_indices.add(f_idx)
            
            if overlapping_frag_indices:
                matched_frags = [sorted_frags[i] for i in overlapping_frag_indices]
                # Union of bounding boxes
                xmin = min(f["bbox"][0] for f in matched_frags)
                ymin = min(f["bbox"][1] for f in matched_frags)
                xmax = max(f["bbox"][2] for f in matched_frags)
                ymax = max(f["bbox"][3] for f in matched_frags)
                # Average confidence
                avg_conf = round(sum(f["confidence"] for f in matched_frags) / len(matched_frags), 4)
                return [xmin, ymin, xmax, ymax], avg_conf, page_no, full_text[start_char_idx:end_char_idx]

    # # Fallback search for a partial match or single matching fragment
    best_match = None
    best_score = 0.0
    for frag in fragments:
        if query.lower() in frag["text"].lower() or frag["text"].lower() in query.lower():
            score = min(len(query), len(frag["text"])) / max(len(query), len(frag["text"]))
            if score > best_score:
                best_score = score
                best_match = frag

    if best_match and best_score > 0.3:
        return best_match["bbox"], best_match["confidence"], best_match["page_no"], best_match["text"]

    return None, None, None, None

STRUCTURED_FIELDS = {
    # KTP
    "provinsi", "kabupaten_kota", "nik", "nama", "tempat_lahir", "tanggal_lahir",
    "jenis_kelamin", "golongan_darah", "alamat", "rt", "rw", "rt_rw",
    "kelurahan_desa", "kecamatan", "agama", "status_perkawinan", "pekerjaan",
    "kewarganegaraan", "berlaku_hingga",
    # KK
    "nomor_kk", "nama_kepala_keluarga", "desa_kelurahan", "kode_pos",
    # NPWP
    "npwp", "nomor_npwp",
    # SIM
    "nomor_sim", "golongan_sim"
}




def is_near_field_label(
    current_key: str,
    matched_bbox: List[int],
    matched_page: int,
    all_fragments: List[OCRFragment],
    max_y_distance: float = 80.0,
) -> bool:
    """
    Checks if the matched value bbox is near the field's label in the OCR layout.
    Returns True if the label is found nearby, or if no label is found in the OCR layout.
    """
    if not current_key:
        return True
        
    key_lower = current_key.lower()
    if key_lower not in STRUCTURED_FIELDS:
        return True  # Skip proximity check for unstructured / custom fields
        
    label_candidates = get_label_candidates(current_key)
    if not label_candidates:
        return True
        
    # Check if any label candidate is found in the OCR fragments
    label_found_in_ocr = False
    for cand in label_candidates:
        lbl_bbox, _, lbl_page, _ = locate_text_in_fragments(cand, all_fragments)
        if lbl_bbox is not None and lbl_page == matched_page:
            label_found_in_ocr = True
            
            # Check spatial proximity
            # We use the label height to dynamically scale our thresholds
            label_height = abs(lbl_bbox[3] - lbl_bbox[1])
            y_threshold = max(max_y_distance, 4.0 * label_height)
            
            y_distance = abs(matched_bbox[1] - lbl_bbox[1])
            x_distance = matched_bbox[0] - lbl_bbox[0]
            
            # The value should be close vertically, and generally to the right or slightly left of the label
            # We allow it to be slightly left to account for multi-line or colon spacing
            if y_distance <= y_threshold and x_distance >= -150:
                return True
                
    # If we found the label but the value wasn't near it, return False (contamination).
    # If the label itself is not present in the OCR, we cannot enforce proximity, so we fallback to True.
    return not label_found_in_ocr

def resolve_leaf_value(
    val: Any,
    all_fragments: List[OCRFragment],
    show_only_mismatch: bool,
    current_key: str
) -> Any:
    query_str = "" if val is None else str(val).strip()
    is_missing = not query_str or query_str.lower() in ("null", "none", "-")
    
    bbox, confidence, page_no, matched_text = None, None, None, None
    value_found_in_ocr = False
    
    if not is_missing:
        bbox, confidence, page_no, matched_text = locate_text_in_fragments(query_str, all_fragments)
        if bbox is not None:
            value_found_in_ocr = True
            
    def clean(s):
        return re.sub(r"[\s\W_]+", "", s.lower())
    q_clean = clean(query_str)
    
    is_exact = False
    if value_found_in_ocr and matched_text:
        is_exact = clean(query_str) == clean(matched_text)
        
    if not is_exact and q_clean and not is_missing:
        for frag in all_fragments:
            if clean(frag["text"]) == q_clean:
                is_exact = True
                bbox = frag["bbox"]
                confidence = frag["confidence"]
                page_no = frag["page_no"]
                matched_text = frag["text"]
                value_found_in_ocr = True
                break
                
    if not is_exact and q_clean and not is_missing:
        full_text = " ".join(frag["text"] for frag in sorted(all_fragments, key=lambda f: (f.get("page_no", 1), round(f["bbox"][1] / 10) * 10, f["bbox"][0])))
        words = re.findall(r"\w+|[^\w\s]", query_str)
        if words:
            pattern_parts = []
            for i, w in enumerate(words):
                if w.isalnum():
                    if len(w) <= 3:
                        pattern_parts.append(rf"\b{re.escape(w)}\b")
                    else:
                        pattern_parts.append(re.escape(w))
                else:
                    pattern_parts.append(re.escape(w))
                if i < len(words) - 1:
                    pattern_parts.append(r"\s*")
            pattern = "".join(pattern_parts)
            try:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match and clean(match.group(0)) == q_clean:
                    is_exact = True
                    value_found_in_ocr = True
            except Exception:
                pass
        else:
            is_exact = True
            value_found_in_ocr = True

    if is_exact and value_found_in_ocr and bbox is not None and current_key:
        if not is_near_field_label(current_key, bbox, page_no, all_fragments):
            is_exact = False
            value_found_in_ocr = False
            bbox = None
            confidence = None
            page_no = None

    # Fallback to field label bounding box if value was not found in OCR
    if not value_found_in_ocr and current_key:
        label_candidates = get_label_candidates(current_key)
            
        for cand in label_candidates:
            lbl_bbox, lbl_conf, lbl_page, lbl_matched = locate_text_in_fragments(cand, all_fragments)
            if lbl_bbox is not None:
                bbox = lbl_bbox
                confidence = lbl_conf
                page_no = lbl_page
                break

    # If even the label cannot be found, and the value is missing, return None
    if bbox is None and is_missing:
        return None

    # Run validation checks on the resolved value
    val_errors = validate_field(current_key, query_str) if current_key else []
    has_val_errors = len(val_errors) > 0
    
    if has_val_errors:
        is_exact = False

    if show_only_mismatch and is_exact:
        return query_str

    status = "uncertain"
    if has_val_errors:
        if not value_found_in_ocr:
            status = "not_found_in_ocr"
        else:
            status = "uncertain"
    else:
        if not value_found_in_ocr:
            status = "not_found_in_ocr"
        elif not is_exact:
            status = "text_modified"
        elif confidence is not None and confidence < 0.85:
            status = "low_confidence"
        elif is_exact:
            status = None

    return {
        "text": None if not query_str or query_str.lower() in ("null", "none") else query_str,
        "bbox": bbox,
        "confidence": confidence,
        "page_no": page_no,
        "status": status,
        "validation_errors": val_errors if val_errors else None
    }

def resolve_bboxes_for_flat_json(
    val: Any, 
    all_fragments: List[OCRFragment],
    show_only_mismatch: bool = False,
    current_key: str = ""
) -> Any:
    """
    Recursively traverse the flat JSON response and resolve text values
    to bounding boxes, page_no, and confidence from original OCR fragments.
    """
    if val is None:
        if current_key:
            res = resolve_leaf_value(None, all_fragments, show_only_mismatch, current_key)
            if res is not None:
                return res
        return None

    if isinstance(val, dict):
        if "text" in val:
            return resolve_leaf_value(val["text"], all_fragments, show_only_mismatch, current_key)
        # Recurse into dict keys
        return {k: resolve_bboxes_for_flat_json(v, all_fragments, show_only_mismatch, current_key=k) for k, v in val.items()}

    if isinstance(val, list):
        # Recurse into list items
        return [resolve_bboxes_for_flat_json(item, all_fragments, show_only_mismatch, current_key) for item in val]

    return resolve_leaf_value(val, all_fragments, show_only_mismatch, current_key)

# Backward compatibility alias for tests
resolve_field_bounding_boxes = resolve_bboxes_for_flat_json

def merge_ocr_fragments(
    fragments: List[OCRFragment], 
    max_x_gap: float = 60.0
) -> List[List[Dict[str, Any]]]:
    """
    Group OCR fragments that are vertically aligned on the same horizontal line.
    - Group fragments that are vertically aligned using an anchor-based overlap approach.
    - Sort from left to right on each line.
    - Retains original bbox and confidence values without merging/averaging, as they
      are resolved separately.
    Returns a list of lines, where each line is a list of original fragment dicts.
    """
    if not fragments:
        return []
    
    # Sort fragments by top coordinate first
    sorted_frags = sorted(fragments, key=lambda f: f["bbox"][1])
    
    lines = []
    
    for frag in sorted_frags:
        fh = frag["bbox"][3] - frag["bbox"][1]
        if fh <= 0:
            continue
            
        added = False
        for line in lines:
            anchor = line[0]
            ay1 = anchor["bbox"][1]
            ay2 = anchor["bbox"][3]
            ah = ay2 - ay1
            
            # Calculate vertical overlap between frag and anchor
            y_overlap = max(0, min(frag["bbox"][3], ay2) - max(frag["bbox"][1], ay1))
            min_h = min(fh, ah)
            
            # Check center distance
            f_center = (frag["bbox"][1] + frag["bbox"][3]) / 2.0
            a_center = (ay1 + ay2) / 2.0
            center_diff = abs(f_center - a_center)
            
            # If significant vertical overlap or centers are very close
            if (min_h > 0 and y_overlap / min_h >= 0.4) or (center_diff <= ah * 0.3):
                line.append(frag)
                added = True
                break
                
        if not added:
            lines.append([frag])
            
    # Sort the lines themselves by the Y coordinate of their anchors (top to bottom)
    lines = sorted(lines, key=lambda line: line[0]["bbox"][1])
            
    # Sort fragments within each line from left to right (X ascending)
    sorted_lines = []
    for line in lines:
        sorted_lines.append(sorted(line, key=lambda f: f["bbox"][0]))
        
    return sorted_lines

def build_field_tallies(page_results: List[Dict[str, Any]]) -> str:
    """Pre-compute tallies for every field across pages.

    Returns a human-readable, structured string that the LLM can consume
    without needing to count occurrences itself.
    """
    all_keys: List[str] = []
    for r in page_results:
        for k in r:
            if k not in all_keys:
                all_keys.append(k)

    lines: List[str] = []

    def get_comp_value(val):
        if isinstance(val, dict) and "value" in val:
            return val["value"]
        return val

    for key in all_keys:
        if any(isinstance(r.get(key), list) for r in page_results):
            merged: List[Dict[str, Any]] = []
            for i, r in enumerate(page_results):
                arr = r.get(key)
                if isinstance(arr, list):
                    for item in arr:
                        merged.append(item)
            lines.append(f"FIELD: {key} (ARRAY — {len(merged)} rows merged from {len(page_results)} pages)")
            lines.append(f"  MERGED DATA: {json.dumps(merged, ensure_ascii=False)}")
            lines.append("  NOTE: May contain duplicates — deduplicate by strongest identifier or semantic similarity.")
            lines.append("")
            continue

        values: List[tuple[int, Any]] = []
        null_pages: List[int] = []
        for i, r in enumerate(page_results):
            v = r.get(key)
            if v is not None and v != "":
                comp_val = get_comp_value(v)
                if comp_val is not None and comp_val != "":
                    values.append((i + 1, v))
                else:
                    null_pages.append(i + 1)
            else:
                null_pages.append(i + 1)

        if not values:
            lines.append(f"FIELD: {key} (ALL NULL)")
            lines.append(f"  All {len(page_results)} pages returned null/empty.")
            lines.append("  RECOMMENDED: null")
            lines.append("")
            continue

        if key.lower() in _LAST_VALUE_FIELDS:
            last_page, last_val = values[-1]
            lines.append(f"FIELD: {key} (NUMERIC — LAST PAGE RULE)")
            for pg, v in values:
                val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else str(v)
                lines.append(f'  {val_str} → page {pg}')
            val_str_last = json.dumps(last_val, ensure_ascii=False) if isinstance(last_val, dict) else str(last_val)
            lines.append(f'  RECOMMENDED: {val_str_last} (last page with value = page {last_page})')
            lines.append("")
            continue

        counts: Counter = Counter(get_comp_value(v) for _, v in values)
        sorted_counts = counts.most_common()
        max_count = sorted_counts[0][1]
        winner_comp = sorted_counts[0][0]

        winner = None
        for pg, v in values:
            if get_comp_value(v) == winner_comp:
                winner = v
                break

        if len(sorted_counts) == 1 or sorted_counts[0][1] > sorted_counts[1][1]:
            tag = "MAJORITY" if max_count > 1 else "SINGLE VALUE"
            lines.append(f"FIELD: {key} (SCALAR — {tag})")
            for val_comp, cnt in sorted_counts:
                pages = [pg for pg, v in values if get_comp_value(v) == val_comp]
                matching_vals = [v for pg, v in values if get_comp_value(v) == val_comp]
                val_str = json.dumps(matching_vals[0], ensure_ascii=False) if isinstance(matching_vals[0], dict) else str(matching_vals[0])
                marker = " ← MAJORITY" if val_comp == winner_comp and max_count > 1 else ""
                lines.append(f'  {val_str} → {cnt} page(s) {pages}{marker}')
            if null_pages:
                lines.append(f"  null/empty pages: {null_pages} (ignored)")
            winner_str = json.dumps(winner, ensure_ascii=False) if isinstance(winner, dict) else str(winner)
            lines.append(f'  RECOMMENDED: {winner_str}')
            lines.append("")
        else:
            earliest_winner = None
            for pg, v in values:
                if counts[get_comp_value(v)] == max_count:
                    earliest_winner = v
                    break
            lines.append(f"FIELD: {key} (SCALAR — TIE)")
            for val_comp, cnt in sorted_counts:
                pages = [pg for pg, v in values if get_comp_value(v) == val_comp]
                matching_vals = [v for pg, v in values if get_comp_value(v) == val_comp]
                val_str = json.dumps(matching_vals[0], ensure_ascii=False) if isinstance(matching_vals[0], dict) else str(matching_vals[0])
                lines.append(f'  {val_str} → {cnt} page(s) {pages}')
            if null_pages:
                lines.append(f"  null/empty pages: {null_pages} (ignored)")
            earliest_winner_str = json.dumps(earliest_winner, ensure_ascii=False) if isinstance(earliest_winner, dict) else str(earliest_winner)
            lines.append(f'  RECOMMENDED: {earliest_winner_str} (earliest page tiebreak)')
            lines.append("  NOTE: Tie detected — you may override if semantic context suggests a better choice.")
            lines.append("")

    return "\n".join(lines)


def aggregate_programmatic(page_results: List[Dict[str, Any]], doc_type: str) -> Dict[str, Any]:
    """Deterministic merge used as fallback when LLM aggregation fails."""
    if len(page_results) == 1:
        return page_results[0]

    all_keys: List[str] = []
    for r in page_results:
        for k in r:
            if k not in all_keys:
                all_keys.append(k)

    result: Dict[str, Any] = {}
    array_keys: List[str] = []

    def get_comp_value(val):
        if isinstance(val, dict) and "value" in val:
            return val["value"]
        return val

    for key in all_keys:
        if any(isinstance(r.get(key), list) for r in page_results):
            array_keys.append(key)
            continue

        values: List[tuple[int, Any]] = []
        for i, r in enumerate(page_results):
            v = r.get(key)
            if v is not None and v != "":
                comp_val = get_comp_value(v)
                if comp_val is not None and comp_val != "":
                    values.append((i, v))

        if not values:
            result[key] = None
            continue

        if key.lower() in _LAST_VALUE_FIELDS:
            result[key] = values[-1][1]
            continue

        counts: Counter = Counter(get_comp_value(v) for _, v in values)
        max_count = counts.most_common(1)[0][1]
        for page_idx, v in values:
            if counts[get_comp_value(v)] == max_count:
                result[key] = v
                break

    for key in array_keys:
        merged: List[Dict[str, Any]] = []
        seen_ids: set = set()
        id_keys = ("nik", "item_number", "material_code", "nomor_sim")
        for r in page_results:
            arr = r.get(key)
            if not isinstance(arr, list):
                continue
            for item in arr:
                item_id = None
                for ik in id_keys:
                    val_to_check = item.get(ik)
                    comp_val = get_comp_value(val_to_check)
                    if comp_val:
                        item_id = comp_val
                        break
                if item_id is None:
                    simplified_item = {}
                    for k, val in item.items():
                        simplified_item[k] = get_comp_value(val)
                    item_id = json.dumps(simplified_item, sort_keys=True)
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    merged.append(item)
        result[key] = merged

    return result

async def run_semantic(
    document_type: str,
    page_images: List[PageImage],
    fields: Optional[List[str]] = None,
    custom_prompt: str = "",
    show_only_mismatch: bool = False
) -> dict:
    """
    Runs the decoupled OCR + semantic pipeline:
    1. Runs PaddleOCR on each page to get fragments.
    2. Constructs a layout-preserving plain text context block from OCR fragments.
    3. Invokes the multimodal LLM (VLM) with both document page images and the plain text context.
    4. Recursively matches returned values back to original fragments to assign bounding boxes and confidence.
    """
    # Sanitize custom prompt to mitigate prompt injection
    custom_prompt = sanitize_custom_prompt(custom_prompt)

    if not page_images:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "no_image_provided",
                "message": "At least one image or PDF is required.",
            },
        )

    all_fragments = []
    page_results = []
    messages_log = []
    # 1. Process page-by-page
    for page_img in page_images:
        page_no = page_img["page_no"]
        fragments = run_ocr_on_image(page_img["image"], page_no)
        all_fragments.extend(fragments)

        # Merge OCR fragments on the same line to create plain text context
        merged_lines = merge_ocr_fragments(fragments)
        # Format text layout by joining line fragments with spaces
        page_lines_text = []
        for line in merged_lines:
            line_text = " ".join(frag["text"] for frag in line)
            page_lines_text.append(line_text)
            
        lines_text = "\n".join(page_lines_text)

        if document_type == "Custom":
            prompt = get_custom_semantic_prompt(custom_prompt)
        elif document_type == "Fields":
            prompt = get_fields_semantic_prompt(fields)
        else:
            prompt = get_doctype_semantic_prompt(document_type)
        
        ocr_context = f"RAW OCR CONTEXT: \n--- Page {page_no} ---\n{lines_text}"
        
        if document_type == "Custom":
            text_content = f"USER_PROMPT: {custom_prompt}\n {ocr_context}"
        else:
            text_content = f"{ocr_context}"
        content = [
            pil_to_content_item(page_img["image"]),
            {"type": "text", "text": text_content}
        ]
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=content)
        ]

        logger.info("Calling VLM (%s) via LangChain request for page %d of %s. Page fragments: %d.", 
                    MODEL_NAME, page_no, document_type, len(fragments))

        raw_response = ""
        try:
            response = await model.ainvoke(messages)
            raw_response = response.content
        except Exception as e:
            logger.error("VLM API call failed for page %d: %s", page_no, e)
            handle_llm_exception(e)

        # Clean and Parse LLM response
        cleaned_content = clean_json_response(raw_response)
        try:
            extracted_json = json.loads(cleaned_content)
        except Exception as e:
            logger.error("Failed to parse JSON response for page %d: %s. Raw: %s", page_no, e, raw_response)
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error_type": "json_parsing_failed",
                    "message": f"LLM returned invalid JSON on page {page_no}: {e}",
                }
            )

        page_results.append(extracted_json)
        messages_log.append({
            "page_no": page_no,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            "response": extracted_json,
            "raw_response": raw_response
        })

    # 2. Aggregation Phase
    if len(page_results) == 1:
        final_json = page_results[0]
    else:
        # Step 1: Pre-compute tallies
        tallies = build_field_tallies(page_results)
        logger.info("Built field tallies for %s (%d pages).", document_type, len(page_results))
        
        # Step 2: Get aggregate prompt and call VLM
        agg_prompt = get_aggregate_prompt(
            document_type,
            fields=fields,
            custom_prompt=custom_prompt
        )
        
        agg_messages = [
            SystemMessage(content=agg_prompt),
            HumanMessage(content=f"{tallies}\n\nSTRICT REQUIREMENT: Return ONLY a valid JSON object matching the consolidated schema. No code blocks, no ```json formatting, no markdown. Start directly with '{{'.")
        ]
        
        logger.info("Calling VLM for consolidation of %d pages.", len(page_results))
        agg_raw_response = ""
        try:
            agg_response = await model.ainvoke(agg_messages)
            agg_raw_response = agg_response.content
            agg_cleaned = clean_json_response(agg_raw_response)
            final_json = json.loads(agg_cleaned)
            method = "tally_llm"
        except Exception as e:
            logger.error("VLM aggregation failed (%s), falling back to programmatic.", e)
            final_json = aggregate_programmatic(page_results, document_type)
            method = "programmatic_fallback"

        messages_log.append({
            "aggregate": True,
            "method": method,
            "messages": [
                {"role": "system", "content": agg_prompt},
                {"role": "user", "content": [{"type": "text", "text": tallies}]}
            ],
            "response": final_json,
            "raw_response": agg_raw_response
        })

    # 3. Coordinate and Confidence Resolution
    resolved_data = resolve_bboxes_for_flat_json(final_json, all_fragments, show_only_mismatch)

    return {
        "success": True,
        "data": resolved_data,
        "messages_log": messages_log
    }

