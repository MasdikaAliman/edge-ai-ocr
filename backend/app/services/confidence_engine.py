"""
Confidence Engine — Computes composite weighted confidence scores for grounded OCR results.
"""

from typing import Dict, Optional

DEFAULT_WEIGHTS = {
    "ocr": 0.40,
    "semantic": 0.30,
    "validation": 0.20,
    "document_rules": 0.10
}


def compute_composite_confidence(
    ocr_confidence: Optional[float],
    semantic_match: bool,
    validation_passed: bool,
    document_rule_passed: bool,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Computes a weighted composite confidence score.

    ocr_confidence: float value between 0.0 and 1.0 from OCR engine.
    semantic_match: bool indicating if extracted value matches OCR text.
    validation_passed: bool indicating if format/regex validations passed.
    document_rule_passed: bool indicating if document-specific logical checks passed.
    weights: custom dictionary to override default weights.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    ocr_val = ocr_confidence if ocr_confidence is not None else 0.0
    sem_val = 1.0 if semantic_match else 0.0
    val_val = 1.0 if validation_passed else 0.0
    rule_val = 1.0 if document_rule_passed else 0.0

    score = (
        (ocr_val * weights.get("ocr", 0.40))
        + (sem_val * weights.get("semantic", 0.30))
        + (val_val * weights.get("validation", 0.20))
        + (rule_val * weights.get("document_rules", 0.10))
    )
    return round(score, 4)
