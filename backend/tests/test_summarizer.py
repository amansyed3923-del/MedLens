"""
Unit tests for Non-Diagnostic Summarizer and Safety Guardrails.
"""

import pytest
from backend.models.fhir import FHIRPatientIntake, InterpretationCode
from backend.services.evaluator import evaluate_observation
from backend.services.summarizer import ClinicalSummarizer


def test_non_diagnostic_summary_safety_disclaimer():
    patient = FHIRPatientIntake(
        id="pt-10",
        age=40,
        sex="Female",
        symptoms=["Fatigue"],
        conditions=[],
        allergies=[],
        medications=[],
    )

    tsh_obs = evaluate_observation(
        test_id="obs-tsh",
        test_name="TSH",
        value=6.20,
        unit="mIU/L",
        range_text="0.40 - 4.50",
    )

    summary = ClinicalSummarizer.summarize(patient, [tsh_obs])

    # Mandatory disclaimer must be present
    assert "MANDATORY SAFETY DISCLAIMER" in summary.safety_disclaimer
    assert "does NOT provide medical diagnoses" in summary.safety_disclaimer

    # Summary must have flagged findings
    assert len(summary.flagged_findings) == 1
    assert summary.flagged_findings[0].test_name == "TSH"
    assert summary.flagged_findings[0].interpretation == InterpretationCode.HIGH

    # Check discussion points are generated
    assert len(summary.discussion_points) > 0

    # Ensure no forbidden prescriptive text
    combined_text = summary.overview + " " + " ".join(summary.discussion_points)
    for pattern in ClinicalSummarizer.FORBIDDEN_DIAGNOSTIC_PATTERNS:
        assert not pattern.search(combined_text)
