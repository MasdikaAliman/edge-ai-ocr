"""
Fuzzy Resolver — Legacy fuzzy string matching coordinate resolution.
Used as a fallback when grounded resolver cannot resolve via Fragment IDs.
"""

import re
import difflib
from typing import Any, Dict, List, Optional
from app.services.ocr_engine import OCRFragment
from app.services.validator import get_label_candidates, validate_field

STRUCTURED_FIELDS = {
    # KTP
    "provinsi",
    "kabupaten_kota",
    "nik",
    "nama",
    "tempat_lahir",
    "tanggal_lahir",
    "jenis_kelamin",
    "golongan_darah",
    "alamat",
    "rt",
    "rw",
    "rt_rw",
    "kelurahan_desa",
    "kecamatan",
    "agama",
    "status_perkawinan",
    "pekerjaan",
    "kewarganegaraan",
    "berlaku_hingga",
    # KK
    "nomor_kk",
    "nama_kepala_keluarga",
    "desa_kelurahan",
    "kode_pos",
    # NPWP
    "npwp",
    "nomor_npwp",
    # SIM
    "nomor_sim",
    "golongan_sim",
}


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
            start_ok = idx == 0 or not full_text[idx - 1].isalnum()
            end_idx = idx + len(query_clean)
            end_ok = end_idx == len(full_text) or not full_text[end_idx].isalnum()
            if start_ok and end_ok:
                return idx, end_idx
        else:
            return idx, idx + len(query_clean)

        idx += 1

    # Fallback to sliding window token-based fuzzy matching using difflib
    tokens = []
    for m in re.finditer(r"\S+", full_text):
        tokens.append({"text": m.group(0), "start": m.start(), "end": m.end()})
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

            for size in range(min_size, max_size + 1):
                for i in range(len(tokens) - size + 1):
                    window = tokens[i : i + size]
                    start_idx = window[0]["start"]
                    end_idx = window[-1]["end"]
                    candidate = full_text[start_idx:end_idx]

                    score = difflib.SequenceMatcher(
                        None, candidate.lower(), query_clean.lower()
                    ).ratio()
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
                    cand_text = full_text[best_range[0] : best_range[1]]
                    if len(cand_text.strip()) == len(query_clean):
                        return best_range
                else:
                    return best_range

    return None


def locate_text_in_fragments(
    query: str, fragments: List[OCRFragment]
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
        sorted_frags = sorted(
            page_frags, key=lambda f: (round(f["bbox"][1] / 10) * 10, f["bbox"][0])
        )

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
            for c_idx in range(
                start_char_idx, min(end_char_idx, len(char_to_frag_idx))
            ):
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
                avg_conf = round(
                    sum(f["confidence"] for f in matched_frags) / len(matched_frags),
                    4,
                )
                return (
                    [xmin, ymin, xmax, ymax],
                    avg_conf,
                    page_no,
                    full_text[start_char_idx:end_char_idx],
                )

    # Fallback search for a partial match or single matching fragment
    best_match = None
    best_score = 0.0
    for frag in fragments:
        if query.lower() in frag["text"].lower() or frag["text"].lower() in query.lower():
            score = min(len(query), len(frag["text"])) / max(
                len(query), len(frag["text"])
            )
            if score > best_score:
                best_score = score
                best_match = frag

    if best_match and best_score > 0.3:
        return (
            best_match["bbox"],
            best_match["confidence"],
            best_match["page_no"],
            best_match["text"],
        )

    return None, None, None, None


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


def fuzzy_locate_value(
    key: str,
    value_str: str,
    all_fragments: List[OCRFragment]
) -> tuple[Optional[List[int]], Optional[float], Optional[int], Optional[str], int]:
    """
    Fuzzy locates value_str inside all_fragments.
    Returns (bbox, confidence, page_no, matched_text, fragments_found).
    """
    bbox, confidence, page_no, matched_text = None, None, None, None
    value_found_in_ocr = False

    # 1. Call locate_text_in_fragments
    bbox, confidence, page_no, matched_text = locate_text_in_fragments(value_str, all_fragments)
    if bbox is not None:
        value_found_in_ocr = True

    def clean(s):
        return re.sub(r"[\s\W_]+", "", s.lower()) if s else ""
    q_clean = clean(value_str)

    is_exact = False
    if value_found_in_ocr and matched_text:
        is_exact = clean(value_str) == clean(matched_text)

    # 2. Exact match check across all fragments
    if not is_exact and q_clean:
        for frag in all_fragments:
            if clean(frag["text"]) == q_clean:
                is_exact = True
                bbox = frag["bbox"]
                confidence = frag["confidence"]
                page_no = frag["page_no"]
                matched_text = frag["text"]
                value_found_in_ocr = True
                break

    # 3. Clean pattern search check
    if not is_exact and q_clean:
        full_text = " ".join(
            frag["text"]
            for frag in sorted(
                all_fragments,
                key=lambda f: (
                    f.get("page_no", 1),
                    round(f["bbox"][1] / 10) * 10,
                    f["bbox"][0],
                ),
            )
        )
        words = re.findall(r"\w+|[^\w\s]", value_str)
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
                    # Let's find first overlapping fragment for bbox/page/conf
                    matched_lbl = match.group(0)
                    lbl_bbox, lbl_conf, lbl_page, lbl_matched = locate_text_in_fragments(matched_lbl, all_fragments)
                    if lbl_bbox is not None:
                        bbox = lbl_bbox
                        confidence = lbl_conf
                        page_no = lbl_page
                        matched_text = lbl_matched
            except Exception:
                pass

    # 4. Proximity Check
    if is_exact and value_found_in_ocr and bbox is not None and key:
        if not is_near_field_label(key, bbox, page_no, all_fragments):
            is_exact = False
            value_found_in_ocr = False
            bbox = None
            confidence = None
            page_no = None
            matched_text = None

    # 5. Label Fallback
    if not value_found_in_ocr and key:
        label_candidates = get_label_candidates(key)
        for cand in label_candidates:
            lbl_bbox, lbl_conf, lbl_page, lbl_matched = locate_text_in_fragments(cand, all_fragments)
            if lbl_bbox is not None:
                bbox = lbl_bbox
                confidence = lbl_conf
                page_no = lbl_page
                matched_text = lbl_matched
                break

    fragments_found = 1 if value_found_in_ocr else 0
    return bbox, confidence, page_no, matched_text, fragments_found
