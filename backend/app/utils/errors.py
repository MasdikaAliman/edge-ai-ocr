import re
from typing import Any, Dict

from fastapi import HTTPException

from app.core.config import BASE_URL_LLM, logger


def _extract_inner_message(error_str: str) -> str:
    try:
        match = re.search(r"'message':\s*'([^']+)'", error_str)
        if match:
            return match.group(1)
    except Exception:
        pass
    return error_str


def handle_llm_exception(exc: Exception) -> None:
    err = str(exc)

    checks = [
        (
            "Error code: 400" in err or "BadRequestError" in err,
            400,
            "llm_bad_request",
            _extract_inner_message(err),
            "Input is likely too long. Reduce image size or text length.",
        ),
        (
            "Error code: 401" in err,
            401,
            "llm_auth_error",
            "Unauthorized — check your LLM API key.",
            None,
        ),
        (
            "Error code: 429" in err,
            429,
            "llm_rate_limit",
            "LLM server is overloaded. Retry after a moment.",
            None,
        ),
        (
            "Error code: 503" in err or "Error code: 500" in err,
            502,
            "llm_server_error",
            "LLM backend returned a server error.",
            None,
        ),
        (
            "ConnectionError" in type(exc).__name__ or "ConnectError" in err,
            503,
            "llm_unreachable",
            f"Cannot connect to LLM server at {BASE_URL_LLM}.",
            None,
        ),
        (
            "TimeoutError" in type(exc).__name__ or "timed out" in err.lower(),
            504,
            "llm_timeout",
            "LLM server did not respond in time. Try a smaller image.",
            None,
        ),
    ]

    for condition, status, error_type, message, hint in checks:
        if condition:
            detail: Dict[str, Any] = {
                "success": False,
                "error_type": error_type,
                "message": message,
            }
            if hint:
                detail["hint"] = hint
            logger.error("vLLM error [%s]: %s", error_type, message)
            raise HTTPException(status_code=status, detail=detail)

    logger.error("Unhandled processing error [%s]: %s", type(exc).__name__, err)
    raise HTTPException(
        status_code=500,
        detail={
            "success": False,
            "error_type": "internal_error",
            "message": f"Unexpected error: {type(exc).__name__}",
            "detail": err,
        },
    )
