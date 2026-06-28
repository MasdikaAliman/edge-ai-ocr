"""Tests for Confidence Engine — Calculates composite confidence scores."""

import pytest
from app.services.confidence_engine import compute_composite_confidence


def test_confidence_perfect():
    # Full confidence: OCR is 1.0, semantic_match is True, validation_passed is True, document_rule is True
    conf = compute_composite_confidence(
        ocr_confidence=1.0,
        semantic_match=True,
        validation_passed=True,
        document_rule_passed=True,
    )
    # 0.40 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.10 * 1.0 = 1.0
    assert conf == 1.0


def test_confidence_partial():
    # OCR: 0.90, semantic_match: True, validation_passed: False, document_rule: True
    conf = compute_composite_confidence(
        ocr_confidence=0.90,
        semantic_match=True,
        validation_passed=False,
        document_rule_passed=True,
    )
    # 0.40 * 0.90 + 0.30 * 1.0 + 0.20 * 0.0 + 0.10 * 1.0
    # = 0.36 + 0.30 + 0.0 + 0.10 = 0.76
    assert conf == 0.76


def test_confidence_ocr_none():
    conf = compute_composite_confidence(
        ocr_confidence=None,
        semantic_match=True,
        validation_passed=True,
        document_rule_passed=True,
    )
    # 0.40 * 0.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.10 * 1.0 = 0.60
    assert conf == 0.60


def test_confidence_custom_weights():
    custom_weights = {
        "ocr": 0.50,
        "semantic": 0.20,
        "validation": 0.20,
        "document_rules": 0.10,
    }
    conf = compute_composite_confidence(
        ocr_confidence=0.80,
        semantic_match=True,
        validation_passed=True,
        document_rule_passed=True,
        weights=custom_weights,
    )
    # 0.50 * 0.80 + 0.20 * 1.0 + 0.20 * 1.0 + 0.10 * 1.0
    # = 0.40 + 0.20 + 0.20 + 0.10 = 0.90
    assert conf == 0.90
