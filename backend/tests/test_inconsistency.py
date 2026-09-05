"""
Unit tests for Clinical Inconsistency Detection Engine.
Validates cross-checking of patient intake conditions, medications,
allergies, and extracted lab observations.
"""

import pytest
from backend.models.fhir import (
    FHIRPatientIntake,
    InconsistencySeverity,
    InterpretationCode,
    ProvenanceRecord,
    ProvenanceSourceType,
)
from backend.services.evaluator import evaluate_observation
from backend.services.inconsistency import InconsistencyEngine


def test_thyroid_inconsistency_detection():
    # Patient reports no thyroid history, but takes Levothyroxine and lab has High TSH
    patient = FHIRPatientIntake(
        id="pt-1",
        age=45,
        sex="Female",
        symptoms=["Fatigue"],
        conditions=["Seasonal allergies"],  # No thyroid condition
        allergies=[],
        medications=["Levothyroxine 50 mcg"],
    )

    tsh_obs = evaluate_observation(
        test_id="obs-tsh",
        test_name="TSH",
        value=6.20,
        unit="mIU/L",
        range_text="0.40 - 4.50",
    )

    inconsistencies = InconsistencyEngine.check_inconsistencies(patient, [tsh_obs])
    assert len(inconsistencies) >= 1
    thyroid_inc = next((i for i in inconsistencies if "thyroid" in i.id), None)
    assert thyroid_inc is not None
    assert thyroid_inc.severity == InconsistencySeverity.WARNING
    assert any("Levothyroxine" in c for c in thyroid_inc.conflicting_elements)
    assert any("TSH" in c for c in thyroid_inc.conflicting_elements)


def test_allergy_medication_conflict():
    # Patient has Penicillin allergy, but is taking Amoxicillin
    patient = FHIRPatientIntake(
        id="pt-2",
        age=30,
        sex="Male",
        symptoms=["Dental pain"],
        conditions=[],
        allergies=["Penicillin"],
        medications=["Amoxicillin 500 mg TID"],
    )

    inconsistencies = InconsistencyEngine.check_inconsistencies(patient, [])
    allergy_inc = next((i for i in inconsistencies if "allergy" in i.id), None)
    assert allergy_inc is not None
    assert allergy_inc.severity == InconsistencySeverity.CRITICAL
    assert "penicillin" in allergy_inc.title.lower()


def test_diabetes_glycemic_inconsistency():
    # Patient has no documented diabetes, but HbA1c is 7.1 (High) and takes Metformin
    patient = FHIRPatientIntake(
        id="pt-3",
        age=52,
        sex="Male",
        symptoms=["Frequent thirst"],
        conditions=["Hypertension"],  # No diabetes
        allergies=[],
        medications=["Metformin 500 mg BID"],
    )

    a1c_obs = evaluate_observation(
        test_id="obs-hba1c",
        test_name="Hemoglobin A1c",
        value=7.1,
        unit="%",
        range_text="< 5.7",
    )

    inconsistencies = InconsistencyEngine.check_inconsistencies(patient, [a1c_obs])
    dm_inc = next((i for i in inconsistencies if "diabetes" in i.id), None)
    assert dm_inc is not None
    assert dm_inc.severity == InconsistencySeverity.CRITICAL
