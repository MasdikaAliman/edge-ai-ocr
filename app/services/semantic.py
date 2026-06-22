import json
import asyncio
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
from app.utils.parsing import clean_json_response
from app.utils.errors import handle_llm_exception

def resolve_field_bounding_boxes(
    val: Any, 
    original_fragments: List[OCRFragment]
) -> Any:
    """
    Recursively traverse the LLM response JSON and match each 'bbox' and 'page_no'
    to the original OCR fragments to calculate average confidence.
    """
    if val is None:
        return None

    if isinstance(val, dict):
        # Check if it has the leaf signature
        if "text" in val and "bbox" in val:
            text = val.get("text")
            bbox = val.get("bbox")
            page_no = val.get("page_no")
            
            # If bbox and page_no are provided, lookup confidence
            if bbox and len(bbox) == 4 and page_no is not None:
                try:
                    page_no_idx = int(page_no)
                except (ValueError, TypeError):
                    page_no_idx = None
                
                if page_no_idx is not None:
                    x1, y1, x2, y2 = bbox
                    matched_confidences = []
                    max_overlap_ratio = 0.0
                    best_confidence = None
                    
                    for frag in original_fragments:
                        if frag.get("page_no") != page_no_idx:
                            continue
                        fx1, fy1, fx2, fy2 = frag["bbox"]
                        
                        # Calculate overlap
                        ix1 = max(x1, fx1)
                        iy1 = max(y1, fy1)
                        ix2 = min(x2, fx2)
                        iy2 = min(y2, fy2)
                        
                        if ix2 > ix1 and iy2 > iy1:
                            inter_area = (ix2 - ix1) * (iy2 - iy1)
                            frag_area = (fx2 - fx1) * (fy2 - fy1)
                            if frag_area > 0:
                                overlap_ratio = inter_area / frag_area
                                if overlap_ratio > 0.5:
                                    matched_confidences.append(frag["confidence"])
                                if overlap_ratio > max_overlap_ratio:
                                    max_overlap_ratio = overlap_ratio
                                    best_confidence = frag["confidence"]
                    
                    if matched_confidences:
                        confidence = round(sum(matched_confidences) / len(matched_confidences), 4)
                    elif best_confidence is not None and max_overlap_ratio > 0.05:
                        confidence = best_confidence
                    else:
                        confidence = None
                        
                    return {
                        "text": text,
                        "bbox": bbox,
                        "confidence": confidence,
                        "page_no": page_no_idx
                    }
            
            # Fallback if bbox/page_no is not resolved or not found
            return {
                "text": text,
                "bbox": bbox,
                "confidence": None,
                "page_no": page_no
            }

        # Otherwise, recurse into dictionary
        return {k: resolve_field_bounding_boxes(v, original_fragments) for k, v in val.items()}

    if isinstance(val, list):
        # Recurse into list
        return [resolve_field_bounding_boxes(item, original_fragments) for item in val]

    return val

async def run_semantic(
    document_type: str,
    page_images: List[PageImage],
    fields: Optional[List[str]] = None,
    custom_prompt: str = ""
) -> dict:
    """
    Runs the decoupled OCR + semantic pipeline:
    1. Runs PaddleOCR on each page to get fragments.
    2. Sorts and serializes fragments directly for LLM input context.
    3. Invokes the text-only LLM.
    4. Matches returned bboxes back to original fragments to assign confidence.
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
    global_lines_parts = []
    total_fragments_count = 0

    for page_img in page_images:
        page_no = page_img["page_no"]
        fragments = run_ocr_on_image(page_img["image"], page_no)
        all_fragments.extend(fragments)
        total_fragments_count += len(fragments)

        # Sort fragments: Y rounded to nearest 10px (to align lines), then by X ascending
        sorted_fragments = sorted(fragments, key=lambda f: (round(f["bbox"][1] / 10) * 10, f["bbox"][0]))

        page_lines = [f"--- Page {page_no} ---"]
        if sorted_fragments:
            for idx, frag in enumerate(sorted_fragments, 1):
                bbox_str = f"[{frag['bbox'][0]}, {frag['bbox'][1]}, {frag['bbox'][2]}, {frag['bbox'][3]}]"
                page_lines.append(f"Frag {idx}: bbox={bbox_str} text={json.dumps(frag['text'])}")
        else:
            page_lines.append("(No text detected on this page)")
            
        global_lines_parts.append("\n".join(page_lines))

    # Step 3: Build Prompt
    context_string = "\n\n".join(global_lines_parts)

    if document_type == "Custom":
        prompt = get_custom_semantic_prompt(custom_prompt)
    elif document_type == "Fields":
        prompt = get_fields_semantic_prompt(fields)
    else:
        prompt = get_doctype_semantic_prompt(document_type)

    # Inject context string into prompt
    full_prompt = f"{prompt}\n\nOCR FRAGMENTS:\n{context_string}"

    # Step 4: Call LLM (text-only)
    messages = [
        SystemMessage(content="You are a high-precision document extraction engine. Output raw JSON ONLY matching the requested schema."),
        HumanMessage(content=full_prompt)
    ]

    logger.info("Calling LLM (%s) via LangChain request for %s. Fragments count: %d", 
                MODEL_NAME, document_type, total_fragments_count)

    raw_response = ""
    try:
        response = await model.ainvoke(messages)
        raw_response = response.content
    except Exception as e:
        logger.error("LLM API call failed: %s", e)
        handle_llm_exception(e)

    # Step 5: Clean and Parse LLM response
    cleaned_content = clean_json_response(raw_response)
    try:
        extracted_json = json.loads(cleaned_content)
    except Exception as e:
        logger.error("Failed to parse JSON response: %s. Raw: %s", e, raw_response)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_type": "json_parsing_failed",
                "message": f"LLM returned invalid JSON: {e}",
            }
        )

    # Step 6: Resolve bounding box confidences from original fragments
    resolved_data = resolve_field_bounding_boxes(extracted_json, all_fragments)

    # Return matches standard API format
    return {
        "success": True,
        "data": resolved_data,
        "messages_log": [
            {
                "page_no": 1,
                "messages": [
                    {"role": "system", "content": "You are a high-precision document extraction engine. Output raw JSON ONLY matching the requested schema."},
                    {"role": "user", "content": full_prompt}
                ],
                "response": extracted_json,
                "raw_response": raw_response
            }
        ]
    }
