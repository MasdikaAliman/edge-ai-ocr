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
    get_custom_semantic_prompt
)
from app.core.sys_prompt import _LAST_VALUE_FIELDS, get_aggregate_prompt
from app.utils.parsing import clean_json_response
from app.utils.errors import handle_llm_exception
from app.utils.image import pil_to_content_item

def find_fuzzy_substring(full_text: str, query: str) -> Optional[tuple[int, int]]:
    # Normalize query by escaping special characters, and converting spaces/punctuation to flexible patterns
    words = re.findall(r"\w+|[^\w\s]", query)
    if not words:
        return None
        
    pattern_parts = []
    for i, w in enumerate(words):
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
        
    # Fallback to direct lowercase substring search
    idx = full_text.lower().find(query.lower())
    if idx != -1:
        return idx, idx + len(query)
        
    return None

def locate_text_in_fragments(
    query: str, 
    fragments: List[OCRFragment]
) -> tuple[Optional[List[int]], Optional[float], Optional[int]]:
    """
    Locates the query text in the list of fragments.
    Returns (bbox, confidence, page_no) if found, otherwise (None, None, None).
    """
    if not fragments or not query:
        return None, None, None

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
                return [xmin, ymin, xmax, ymax], avg_conf, page_no

    # # Fallback search for a partial match or single matching fragment
    # best_match = None
    # best_score = 0.0
    # for frag in fragments:
    #     if query.lower() in frag["text"].lower() or frag["text"].lower() in query.lower():
    #         score = min(len(query), len(frag["text"])) / max(len(query), len(frag["text"]))
    #         if score > best_score:
    #             best_score = score
    #             best_match = frag
                
    # if best_match and best_score > 0.3:
    #     return best_match["bbox"], best_match["confidence"], best_match["page_no"]

    return None, None, None

def resolve_bboxes_for_flat_json(
    val: Any, 
    all_fragments: List[OCRFragment]
) -> Any:
    """
    Recursively traverse the flat JSON response and resolve text values
    to bounding boxes, page_no, and confidence from original OCR fragments.
    """
    if val is None:
        return None

    if isinstance(val, dict):
        # Recurse into dict keys
        return {k: resolve_bboxes_for_flat_json(v, all_fragments) for k, v in val.items()}

    if isinstance(val, list):
        # Recurse into list items
        return [resolve_bboxes_for_flat_json(item, all_fragments) for item in val]

    # Otherwise, it's a leaf value (string, number, boolean)
    query_str = str(val).strip()
    if not query_str or query_str.lower() in ("null", "none"):
        return {
            "text": query_str,
            "bbox": None,
            "confidence": None,
            "page_no": None
        }

    # Find coordinates for query_str
    bbox, confidence, page_no = locate_text_in_fragments(query_str, all_fragments)
    
    return {
        "text": query_str,
        "bbox": bbox,
        "confidence": confidence,
        "page_no": page_no
    }

def merge_ocr_fragments(
    fragments: List[OCRFragment], 
    max_x_gap: float = 60.0
) -> List[List[Dict[str, Any]]]:
    """
    Merge adjacent OCR fragments on the same line to reduce tokens and improve LLM parsing.
    - Group fragments that are vertically aligned using an anchor-based overlap approach.
    - Sort from left to right on each line.
    - Merge adjacent fragments if their horizontal distance is within max_x_gap.
    Returns a list of lines, where each line is a list of merged fragment dicts.
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
            
    merged_lines = []
    
    for line in lines:
        # Sort fragments in the line from left to right (X ascending)
        line_sorted = sorted(line, key=lambda f: f["bbox"][0])
        
        merged_line = []
        current_merged = None
        for frag in line_sorted:
            if current_merged is None:
                current_merged = {
                    "text": frag["text"],
                    "bbox": list(frag["bbox"]),
                    "confidence": frag["confidence"],
                    "page_no": frag["page_no"]
                }
            else:
                # Check horizontal gap between the end of current_merged and start of frag
                gap = frag["bbox"][0] - current_merged["bbox"][2]
                if gap <= max_x_gap:
                    # Merge them
                    current_merged["text"] += " " + frag["text"]
                    current_merged["bbox"][0] = min(current_merged["bbox"][0], frag["bbox"][0])
                    current_merged["bbox"][1] = min(current_merged["bbox"][1], frag["bbox"][1])
                    current_merged["bbox"][2] = max(current_merged["bbox"][2], frag["bbox"][2])
                    current_merged["bbox"][3] = max(current_merged["bbox"][3], frag["bbox"][3])
                    current_merged["confidence"] = (current_merged["confidence"] + frag["confidence"]) / 2.0
                else:
                    merged_line.append(current_merged)
                    current_merged = {
                        "text": frag["text"],
                        "bbox": list(frag["bbox"]),
                        "confidence": frag["confidence"],
                        "page_no": frag["page_no"]
                    }
        if current_merged:
            merged_line.append(current_merged)
            
        merged_lines.append(merged_line)
            
    return merged_lines

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
    custom_prompt: str = ""
) -> dict:
    """
    Runs the decoupled OCR + semantic pipeline:
    1. Runs PaddleOCR on each page to get fragments.
    2. Constructs a layout-preserving plain text context block from OCR fragments.
    3. Invokes the multimodal LLM (VLM) with both document page images and the plain text context.
    4. Recursively matches returned values back to original fragments to assign bounding boxes and confidence.
    """
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
    from icecream import ic 

    # 1. Process page-by-page
    for page_img in page_images:
        page_no = page_img["page_no"]
        fragments = run_ocr_on_image(page_img["image"], page_no)
        all_fragments.extend(fragments)

        # Merge OCR fragments on the same line to create plain text context
        merged_lines = merge_ocr_fragments(fragments)
        ic(merged_lines)
        
        # Format text layout by joining line fragments with spaces
        page_lines_text = []
        for line in merged_lines:
            line_text = " ".join(frag["text"] for frag in line)
            page_lines_text.append(line_text)
            
        lines_text = "\n".join(page_lines_text)

        # Determine prompt for this page
        if document_type == "Custom":
            prompt = get_custom_semantic_prompt(custom_prompt)
        elif document_type == "Fields":
            prompt = get_fields_semantic_prompt(fields)
        else:
            prompt = get_doctype_semantic_prompt(document_type)

        # Construct message content for VLM
        content = [
            pil_to_content_item(page_img["image"]),
            {"type": "text", "text": f"After You read image see this context: \n--- Page {page_no} ---\n{lines_text}"}
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
            HumanMessage(content=tallies)
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
    resolved_data = resolve_bboxes_for_flat_json(final_json, all_fragments)

    return {
        "success": True,
        "data": resolved_data,
        "messages_log": messages_log
    }

