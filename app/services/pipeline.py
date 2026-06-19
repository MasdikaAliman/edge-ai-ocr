import json
from collections import Counter
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from app.core.config import logger, MAX_DOC_PAGES, model
from app.core.doc_prompt import get_prompt_for_document
from app.core.sys_prompt import (
    _LAST_VALUE_FIELDS,
    get_prompt_for_fields,
    get_prompt_for_custom,
    get_reprocess_prompt,
    get_aggregate_prompt,
)
from app.services.pdf import PageData
from app.utils.errors import handle_llm_exception
from app.utils.image import validate_content
from app.utils.parsing import clean_json_response


class OCRState(TypedDict):
    document_type: str
    fields: Optional[List[str]]
    custom_prompt: Optional[str]
    pages: List[PageData]
    current_idx: int
    page_results: List[Dict[str, Any]]
    final_result: Dict[str, Any]
    messages_log: List[Dict[str, Any]]

def _build_user_message(page_data: PageData, doc_type: str, custom_prompt: str) -> str:
    parts = [f"This is page {page_data['page_no']} of a {doc_type} document."]
    
    # Inject color hints if available
    colored_texts = page_data.get("colored_texts", [])
    if colored_texts:
        parts.append("\n\nCOLOR TEXT MAPPING (from PDF source, use as ground truth):")
        for i, item in enumerate(colored_texts, 1):
            parts.append(f"  {i}. [{item['color']}] \"{item['text']}\"")
        parts.append(
            "\nIMPORTANT: These colored texts were extracted programmatically from the PDF. "
            "They are 100% accurate. When filling fields that require colored text "
            "(e.g. material_code), use ONLY these values. "
            "Do NOT attempt to detect colors from the image yourself."
        )
    
    if doc_type == "Custom" and custom_prompt:
        parts.append(f"\n\nInstructions:\n{custom_prompt}")
    
    markdown = page_data.get("markdown", "")
    if markdown:
        parts.append(f"\n\n### Page {page_data['page_no']} Text/Markdown:\n{markdown}")
    
    return "\n".join(parts)


def _invoke_model(messages: list) -> tuple[dict, str]:
    """Invoke the model and return (parsed_dict, raw_content)."""
    response = model.invoke(messages)
    raw_content = response.content
    cleaned_content = clean_json_response(raw_content)
    logger.debug("Cleaned JSON content before parsing: %s", cleaned_content)
    logger.debug("Raw JSON content before parsing: %s", raw_content)

    try:
        parsed = json.loads(cleaned_content)
    except Exception as e:
        logger.error("JSON parsing failed in _invoke_model. Raw content: %s", raw_content)
        raise e

    if isinstance(parsed, list):
        return (parsed[0] if parsed else {}), raw_content
    return parsed, raw_content


def process_page_node(state: OCRState) -> Dict[str, Any]:
    idx = state["current_idx"]
    page_data = state["pages"][idx]
    doc_type = state["document_type"]
    fields = state["fields"]
    custom_prompt = state.get("custom_prompt", "")

    content: List[Dict[str, Any]] = [
        {"type": "text", "text": _build_user_message(page_data, doc_type, custom_prompt)}
    ]
    content.append(page_data["image"])
    for table_img in page_data.get("table_images", []):
        content.append(table_img)

    if doc_type == "Custom":
        system_prompt = get_prompt_for_custom(custom_prompt)
    elif doc_type == "Fields":
        system_prompt = get_prompt_for_fields(fields)
    else:
        system_prompt = get_prompt_for_document(doc_type)

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=content)]

    raw_response = ""
    try:
        extracted_data, raw_response = _invoke_model(messages)
        logger.info("Page %d extracted successfully.", page_data["page_no"])
    except Exception as e:
        logger.error("Error extracting page %d: %s", page_data["page_no"], e)
        extracted_data = {"error": str(e), "page": page_data["page_no"]}

    return {
        "page_results": state.get("page_results", []) + [extracted_data],
        "current_idx": idx + 1,
        "messages_log": state.get("messages_log", []) + [
            {
                "page_no": page_data["page_no"],
                "messages": messages,
                "response": extracted_data,
                "raw_response": raw_response,
            }
        ],
    }


def reprocess_page_node(state: OCRState) -> Dict[str, Any]:
    idx = state["current_idx"] - 1
    page_data = state["pages"][idx]
    required_fields = state.get("fields") or []
    last_result = state["page_results"][-1]

    missing = [
        f for f in required_fields
        if f not in last_result
    ]
    if not missing:
        return {}

    doc_type = state["document_type"]
    prompt = get_reprocess_prompt(page_data['page_no'], doc_type, missing)
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    content.append(page_data["image"])
    for table_img in page_data.get("table_images", []):
        content.append(table_img)
    
    messages = [
        SystemMessage(content="You are an expert at extracting structured data from documents."),
        HumanMessage(content=content),
    ]

    raw_response = ""
    try:
        new_data, raw_response = _invoke_model(messages)
        logger.info("Reprocess page %d found additional data.", page_data["page_no"])
    except Exception:
        new_data = {}

    merged = {**last_result, **new_data}
    update = {"page_results": state["page_results"][:-1] + [merged]}
    update.update(_log_reprocess(state, new_data, raw_response))
    return update


def _log_reprocess(state: OCRState, new_data: dict, raw_response: str = "") -> Dict[str, Any]:
    return {
        "messages_log": state.get("messages_log", []) + [
            {
                "page_no": state["current_idx"] - 1,
                "reprocess": True,
                "response": new_data,
                "raw_response": raw_response,
            }
        ],
    }


def _after_process_page(state: OCRState) -> str:
    required_fields = [f for f in (state.get("fields") or []) if f and f.strip()]
    if required_fields:
        last_result = state["page_results"][-1] if state["page_results"] else {}
        missing = [f for f in required_fields if f not in last_result]
        if missing:
            logger.info("Missing fields detected, will reprocess: %s", missing)
            return "reprocess_page"
    if state["current_idx"] < len(state["pages"]):
        return "process_page"
    return "aggregate_results"


def _after_reprocess(state: OCRState) -> str:
    if state["current_idx"] < len(state["pages"]):
        return "process_page"
    return "aggregate_results"


# ---------- Aggregation Helpers ----------

def build_field_tallies(page_results: list[dict]) -> str:
    """Pre-compute tallies for every field across pages.

    Returns a human-readable, structured string that the LLM can consume
    without needing to count occurrences itself.
    """
    # Collect all keys in order of first appearance
    all_keys: list[str] = []
    for r in page_results:
        for k in r:
            if k not in all_keys:
                all_keys.append(k)

    lines: list[str] = []

    # Helper to extract raw value for comparison (handles Qwen3-VL grounding dict)
    def get_comp_value(val):
        if isinstance(val, dict) and "value" in val:
            return val["value"]
        return val

    for key in all_keys:
        # --- Array fields ---
        if any(isinstance(r.get(key), list) for r in page_results):
            # Merge arrays from all pages
            merged: list[dict] = []
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

        # --- Scalar fields ---
        # Gather (page_index, value) for non-null entries
        values: list[tuple[int, Any]] = []
        null_pages: list[int] = []
        for i, r in enumerate(page_results):
            v = r.get(key)
            if v is not None and v != "":
                comp_val = get_comp_value(v)
                if comp_val is not None and comp_val != "":
                    values.append((i + 1, v))  # 1-indexed page numbers
                else:
                    null_pages.append(i + 1)
            else:
                null_pages.append(i + 1)

        # All null
        if not values:
            lines.append(f"FIELD: {key} (ALL NULL)")
            lines.append(f"  All {len(page_results)} pages returned null/empty.")
            lines.append("  RECOMMENDED: null")
            lines.append("")
            continue

        # Numeric / last-page fields
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

        # Count occurrences for majority vote
        counts: Counter = Counter(get_comp_value(v) for _, v in values)
        sorted_counts = counts.most_common()
        max_count = sorted_counts[0][1]
        winner_comp = sorted_counts[0][0]

        # Find the first actual value mapping to the winning comparison value
        winner = None
        for pg, v in values:
            if get_comp_value(v) == winner_comp:
                winner = v
                break

        # Single unique value or clear majority
        if len(sorted_counts) == 1 or sorted_counts[0][1] > sorted_counts[1][1]:
            tag = "MAJORITY" if max_count > 1 else "SINGLE VALUE"
            lines.append(f"FIELD: {key} (SCALAR — {tag})")
            for val_comp, cnt in sorted_counts:
                pages = [pg for pg, v in values if get_comp_value(v) == val_comp]
                # Print the full structure of the first match
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
            # Tie — multiple values with same count
            # Recommend earliest page value as tiebreak
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


def aggregate_programmatic(page_results: list[dict], doc_type: str) -> dict:
    """Deterministic merge used as fallback when LLM aggregation fails."""
    if len(page_results) == 1:
        return page_results[0]

    all_keys: list[str] = []
    for r in page_results:
        for k in r:
            if k not in all_keys:
                all_keys.append(k)

    result: dict = {}
    array_keys: list[str] = []

    # Helper to extract raw value for comparison
    def get_comp_value(val):
        if isinstance(val, dict) and "value" in val:
            return val["value"]
        return val

    for key in all_keys:
        if any(isinstance(r.get(key), list) for r in page_results):
            array_keys.append(key)
            continue

        values: list[tuple[int, Any]] = []
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
        merged: list[dict] = []
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
                    # Simplify comparison: extract only "value"s for seen_ids check
                    simplified_item = {}
                    for k, val in item.items():
                        simplified_item[k] = get_comp_value(val)
                    item_id = json.dumps(simplified_item, sort_keys=True)
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    merged.append(item)
        result[key] = merged

    return result


# ---------- Aggregate Node ----------

def aggregate_node(state: OCRState) -> Dict[str, Any]:
    page_results = state.get("page_results", [])
    doc_type = state["document_type"]

    if not page_results:
        return {"final_result": {}}
    if len(page_results) == 1:
        return {"final_result": page_results[0]}

    # --- Step 1: Python pre-computes tallies ---
    tallies = build_field_tallies(page_results)
    logger.info("Built field tallies for %s (%d pages).", doc_type, len(page_results))
    logger.debug("Tallies:\n%s", tallies)

    # --- Step 2: LLM receives tallies and decides ---
    system_prompt = get_aggregate_prompt(
        doc_type,
        fields=state.get("fields"),
        custom_prompt=state.get("custom_prompt", ""),
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=tallies),
    ]

    raw_response = ""
    try:
        final_data, raw_response = _invoke_model(messages)
        logger.info("Unified aggregation (tally+LLM) complete.")
    except Exception as e:
        # Fallback to programmatic aggregation if LLM fails
        logger.error("LLM aggregation failed (%s), falling back to programmatic.", e)
        final_data = aggregate_programmatic(page_results, doc_type)
        return {
            "final_result": final_data,
            "messages_log": state.get("messages_log", []) + [
                {"aggregate": True, "method": "programmatic_fallback", "error": str(e)}
            ],
        }

    return {
        "final_result": final_data,
        "messages_log": state.get("messages_log", []) + [
            {"aggregate": True, "method": "tally_llm", "raw_response": raw_response}
        ],
    }


def _build_graph():
    workflow = StateGraph(OCRState)
    workflow.add_node("process_page", process_page_node)
    workflow.add_node("reprocess_page", reprocess_page_node)
    workflow.add_node("aggregate_results", aggregate_node)

    workflow.add_edge(START, "process_page")

    workflow.add_conditional_edges(
        "process_page",
        _after_process_page,
        {
            "reprocess_page": "reprocess_page",
            "process_page": "process_page",
            "aggregate_results": "aggregate_results",
        },
    )

    workflow.add_conditional_edges(
        "reprocess_page",
        _after_reprocess,
        {
            "process_page": "process_page",
            "aggregate_results": "aggregate_results",
        },
    )

    workflow.add_edge("aggregate_results", END)
    return workflow.compile()


_ocr_graph = _build_graph()


async def run_ocr(
    document_type: str,
    pages: List[PageData],
    fields: Optional[List[str]] = None,
    custom_prompt: str = "",
) -> dict:
    if not pages:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "no_image_provided",
                "message": "At least one image or PDF is required.",
            },
        )

    if len(pages) > MAX_DOC_PAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "image_limit_exceeded",
                "message": f"Too many pages. Maximum is {MAX_DOC_PAGES}, but {len(pages)} were provided.",
            },
        )

    for page in pages:
        validate_content([page["image"]] + page.get("table_images", []))

    initial_state: OCRState = {
        "document_type": document_type,
        "fields": fields,
        "custom_prompt": custom_prompt,
        "pages": pages,
        "current_idx": 0,
        "page_results": [],
        "final_result": {},
        "messages_log": [],
    }

    try:
        final_state = await _ocr_graph.ainvoke(initial_state)
        return {
            "success": True,
            "data": final_state.get("final_result", {}),
            "messages_log": final_state.get("messages_log", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_llm_exception(e)
