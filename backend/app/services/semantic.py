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
from app.services.fragment_store import FragmentStore
from app.core.grounded_prompt import build_grounded_context
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
from app.services.grounded_resolver import resolve_grounded_json

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
    fragment_store = FragmentStore()
    page_results = []
    messages_log = []
    # 1. Process page-by-page
    for page_img in page_images:
        page_no = page_img["page_no"]
        fragments = run_ocr_on_image(page_img["image"], page_no)
        # Populate FragmentStore and enrich fragments with IDs
        for frag in fragments:
            stored = fragment_store.add_from_ocr_fragment(frag)
            frag["fragment_id"] = stored.id
        all_fragments.extend(fragments)

        # Build grounded OCR context (with Fragment IDs) for VLM
        grounded_context = build_grounded_context(fragment_store, page_no)

        if document_type == "Custom":
            prompt = get_custom_semantic_prompt(custom_prompt)
        elif document_type == "Fields":
            prompt = get_fields_semantic_prompt(fields)
        else:
            prompt = get_doctype_semantic_prompt(document_type)
        
        ocr_context = f"GROUNDED OCR CONTEXT: \n--- Page {page_no} ---\n{grounded_context}"
        
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
            "raw_response": raw_response,
            "grounded_context": grounded_context,
            "raw_ocr": fragments
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
            "raw_response": agg_raw_response,
            "grounded_context": grounded_context
        })

    # 3. Coordinate and Confidence Resolution
    resolved_data = resolve_grounded_json(
        final_json,
        fragment_store,
        show_only_mismatch
    )

    return {
        "success": True,
        "data": resolved_data,
        "messages_log": messages_log
    }

