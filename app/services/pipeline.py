import json
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from app.core.config import logger, MAX_IMAGES, model
from app.core.prompts import (
    get_prompt_for_document,
    get_prompt_for_fields,
    get_prompt_for_custom,
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
    if doc_type == "Custom" and custom_prompt:
        parts.append(f"\n\nInstructions:\n{custom_prompt}")
    markdown = page_data.get("markdown", "")
    if markdown:
        parts.append(f"\n\n### Page {page_data['page_no']} Text/Markdown:\n{markdown}")
    return "\n".join(parts)


def _invoke_model(messages: list) -> dict:
    response = model.invoke(messages)
    parsed = json.loads(clean_json_response(response.content))
    if isinstance(parsed, list):
        return parsed[0] if parsed else {}
    return parsed


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

    try:
        extracted_data = _invoke_model(messages)
        logger.info("Page %d extracted successfully.", page_data["page_no"])
    except Exception as e:
        logger.error("Error extracting page %d: %s", page_data["page_no"], e)
        extracted_data = {"error": str(e), "page": page_data["page_no"]}

    return {
        "page_results": state.get("page_results", []) + [extracted_data],
        "current_idx": idx + 1,
        "messages_log": state.get("messages_log", []) + [
            {"page_no": page_data["page_no"], "messages": messages, "response": extracted_data}
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
    prompt = f"""You are reprocessing page {page_data['page_no']} of a {doc_type} document.

The following fields were missing from the previous extraction:
{missing}

Re-analyze the document carefully, focusing on tables and structured rows.
IMPORTANT:
- Extract ONLY the missing fields listed above.
- Do NOT overwrite fields that were already correctly extracted.
- Return ONLY a raw JSON object. No markdown, no commentary.
"""
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    content.append(page_data["image"])
    for table_img in page_data.get("table_images", []):
        content.append(table_img)

    messages = [
        SystemMessage(content="You are an expert at extracting structured data from documents."),
        HumanMessage(content=content),
    ]

    try:
        new_data = _invoke_model(messages)
        logger.info("Reprocess page %d found additional data.", page_data["page_no"])
    except Exception:
        new_data = {}

    merged = {**last_result, **new_data}
    update = {"page_results": state["page_results"][:-1] + [merged]}
    update.update(_log_reprocess(state, new_data))
    return update


def _log_reprocess(state: OCRState, new_data: dict) -> Dict[str, Any]:
    return {
        "messages_log": state.get("messages_log", []) + [
            {"page_no": state["current_idx"] - 1, "reprocess": True, "response": new_data}
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


def aggregate_node(state: OCRState) -> Dict[str, Any]:
    page_results = state.get("page_results", [])
    doc_type = state["document_type"]

    if not page_results:
        return {"final_result": {}}
    if len(page_results) == 1:
        return {"final_result": page_results[0]}

    system_prompt = (
        f"You are an expert data arbitration engine for {doc_type} documents.\n"
        "Multiple pages from the same document were OCR'd independently. "
        "Produce ONE final JSON object.\n"
        "RULES:\n"
        "- For each field, choose the most complete and credible value across all pages.\n"
        "- If the same field appears on multiple pages with DIFFERENT values, prefer:\n"
        "    1. The value that is more complete (not empty/partial).\n"
        "    2. The value from the page where that field would naturally appear\n"
        "       (e.g. totals from the last page, header info from the first page).\n"
        "- For array fields (e.g. line items, members), MERGE arrays from all pages\n"
        "  and deduplicate identical rows.\n"
        "- If a field is empty (\"\") or null on ALL pages, output \"\" for that field.\n"
        "- NEVER fabricate or infer values not present in any page result.\n"
        "- Return ONLY a raw JSON object. No markdown, no commentary, no code fences."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(page_results, indent=2)),
    ]

    try:
        response = model.invoke(messages)
        final_data = json.loads(clean_json_response(response.content))
        if isinstance(final_data, list):
            final_data = final_data[0] if final_data else {}
        logger.info("Aggregation complete.")
    except Exception as e:
        logger.error("Error in aggregation node: %s", e)
        final_data = {"error": f"Aggregation failed: {str(e)}", "partial_results": page_results}

    return {"final_result": final_data, "messages_log": state.get("messages_log", []) + [{"aggregate": True}]}


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

    if len(pages) > MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "image_limit_exceeded",
                "message": f"Too many pages. Maximum is {MAX_IMAGES}, but {len(pages)} were provided.",
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
