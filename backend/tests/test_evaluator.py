"""
Unit tests for Reference-Range & Provenance Engine.
Verifies deterministic classification (LOW, NORMAL, HIGH, UNSPECIFIED)
and strict non-defaulting behavior when reference ranges are omitted.
"""

import pytest
from backend.models.fhir import InterpretationCode, ProvenanceSourceType
from backend.services.evaluator import ReferenceRangeEngine, evaluate_observation


def test_reference_range_between_evaluation():
    # TSH range 0.40 - 4.50
    ref = ReferenceRangeEngine.parse_reference_range("0.40 - 4.50", unit="mIU/L")
    assert ref is not None
    assert ref.low == 0.40
    assert ref.high == 4.50

    # Test values
    assert ReferenceRangeEngine.evaluate_value(0.20, ref) == InterpretationCode.LOW
    assert ReferenceRangeEngine.evaluate_value(2.15, ref) == InterpretationCode.NORMAL
    assert ReferenceRangeEngine.evaluate_value(6.20, ref) == InterpretationCode.HIGH


def test_reference_range_upper_bound_only():
    # HbA1c < 5.7
    ref = ReferenceRangeEngine.parse_reference_range("< 5.7", unit="%")
    assert ref is not None
    assert ref.low is None
    assert ref.high == 5.7

    assert ReferenceRangeEngine.evaluate_value(5.2, ref) == InterpretationCode.NORMAL
    assert ReferenceRangeEngine.evaluate_value(5.7, ref) == InterpretationCode.NORMAL
    assert ReferenceRangeEngine.evaluate_value(6.8, ref) == InterpretationCode.HIGH


def test_reference_range_lower_bound_only():
    # eGFR > 60
    ref = ReferenceRangeEngine.parse_reference_range("> 60", unit="mL/min/1.73m2")
    assert ref is not None
    assert ref.low == 60.0
    assert ref.high is None

    assert ReferenceRangeEngine.evaluate_value(75.0, ref) == InterpretationCode.NORMAL
    assert ReferenceRangeEngine.evaluate_value(60.0, ref) == InterpretationCode.NORMAL
    assert ReferenceRangeEngine.evaluate_value(45.0, ref) == InterpretationCode.LOW


def test_unspecified_when_no_reference_range():
    """
    CRITICAL REQUIREMENT:
    Assign UNSPECIFIED if no reference range is provided.
    Do NOT invent external default ranges.
    """
    assert ReferenceRangeEngine.parse_reference_range(None) is None
    assert ReferenceRangeEngine.parse_reference_range("") is None
    assert ReferenceRangeEngine.parse_reference_range("   ") is None
    assert ReferenceRangeEngine.parse_reference_range("N/A") is None
    assert ReferenceRangeEngine.parse_reference_range("None") is None
    assert ReferenceRangeEngine.parse_reference_range("Not Established") is None

    # When ref_range is None, evaluate_value MUST return UNSPECIFIED
    assert ReferenceRangeEngine.evaluate_value(14.2, None) == InterpretationCode.UNSPECIFIED


def test_observation_provenance_tagging():
    obs = evaluate_observation(
        test_id="obs-tsh",
        test_name="TSH",
        value=6.20,
        unit="mIU/L",
        range_text="0.40 - 4.50",
        source_type=ProvenanceSourceType.EXTRACTED_FROM_LAB_PDF,
        source_file="lab_quest_2026.pdf",
        page_number=1,
        raw_snippet="TSH  6.20 H  0.40 - 4.50 mIU/L",
        confidence_score=0.98,
    )

    assert obs.interpretation == InterpretationCode.HIGH
    assert obs.provenance.source_type == ProvenanceSourceType.EXTRACTED_FROM_LAB_PDF
    assert obs.provenance.source_file == "lab_quest_2026.pdf"
    assert obs.provenance.page_number == 1
    assert obs.provenance.confidence_score == 0.98
    assert "TSH" in obs.provenance.raw_snippet
