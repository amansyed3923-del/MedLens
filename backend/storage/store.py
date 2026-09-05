"""
Persistent Clinical Session Store for MedLens.
Stores patient intake, uploaded documents, extracted FHIR observations,
inconsistency flags, and summary reports.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from backend.models.fhir import (
    FHIRPatientIntake,
    FHIRObservation,
    FHIRInconsistency,
    FHIRClinicalSummary,
    FHIRClinicalBundle,
    ProvenanceRecord,
    ProvenanceSourceType,
    InterpretationCode,
)
from backend.services.evaluator import ReferenceRangeEngine, evaluate_observation
from backend.services.inconsistency import detect_inconsistencies
from backend.services.summarizer import generate_clinical_summary


class ClinicalStore:
    """Manages active session state and persistence."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        self.base_dir = Path(base_dir)
        self.uploads_dir = self.base_dir / "uploads"
        self.sessions_dir = self.base_dir / "sessions"

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # In-memory active clinical state
        self.current_patient: FHIRPatientIntake = self._default_patient()
        self.observations: List[FHIRObservation] = []
        self.raw_documents: List[Dict[str, str]] = []  # [{filename, content_preview, timestamp}]
        self.active_inconsistencies: List[FHIRInconsistency] = []
        self.current_summary: Optional[FHIRClinicalSummary] = None

    def _default_patient(self) -> FHIRPatientIntake:
        return FHIRPatientIntake(
            id="patient-101",
            age=45,
            sex="Female",
            symptoms=["Fatigue", "Cold intolerance", "Weight gain"],
            conditions=["Mild seasonal allergies"],
            allergies=["Penicillin"],
            medications=["Levothyroxine 50 mcg", "Multivitamin"],
            provenance=ProvenanceRecord(
                source_type=ProvenanceSourceType.USER_PROVIDED,
                raw_snippet="Initial intake completed by patient",
                confidence_score=1.0,
            ),
        )

    def update_patient_intake(self, intake: FHIRPatientIntake) -> FHIRPatientIntake:
        """Updates patient demographics, symptoms, conditions, allergies, and medications."""
        self.current_patient = intake
        self.recalculate()
        return self.current_patient

    def add_observations(
        self, new_obs: List[FHIRObservation], source_doc: Optional[Dict[str, str]] = None
    ) -> List[FHIRObservation]:
        """Merges new extracted observations with existing list (updating by test id)."""
        existing_map = {o.id: o for o in self.observations}
        for obs in new_obs:
            existing_map[obs.id] = obs
        self.observations = list(existing_map.values())

        if source_doc:
            self.raw_documents.append(source_doc)

        self.recalculate()
        return self.observations

    def update_observation(self, obs_id: str, updated_val: float, updated_range: Optional[str] = None) -> Optional[FHIRObservation]:
        """Allows clinician to edit an observation value or range with provenance audit tag."""
        for i, obs in enumerate(self.observations):
            if obs.id == obs_id:
                # Retain original test name & code
                ref_range = (
                    ReferenceRangeEngine.parse_reference_range(updated_range, unit=obs.valueQuantity.unit if obs.valueQuantity else "")
                    if updated_range is not None
                    else (obs.referenceRange[0] if obs.referenceRange else None)
                )
                interp = ReferenceRangeEngine.evaluate_value(updated_val, ref_range)

                obs.valueQuantity.value = updated_val if obs.valueQuantity else None
                obs.valueString = str(updated_val)
                obs.referenceRange = [ref_range] if ref_range else []
                obs.interpretation = interp
                obs.provenance.source_type = ProvenanceSourceType.CLINICIAN_EDITED
                obs.provenance.raw_snippet = f"Clinician amended value to {updated_val}"
                self.observations[i] = obs
                self.recalculate()
                return obs
        return None

    def recalculate(self):
        """Re-runs inconsistency detection and non-diagnostic summary."""
        self.active_inconsistencies = detect_inconsistencies(self.current_patient, self.observations)
        self.current_summary = generate_clinical_summary(self.current_patient, self.observations)

    def acknowledge_inconsistency(self, inc_id: str, notes: Optional[str] = None) -> bool:
        """Flags an inconsistency as reviewed by clinician."""
        for inc in self.active_inconsistencies:
            if inc.id == inc_id:
                inc.is_reviewed = True
                inc.review_notes = notes or "Acknowledged and reviewed by clinician."
                return True
        return False

    def clear_all(self):
        """Resets the active session."""
        self.current_patient = self._default_patient()
        self.observations = []
        self.raw_documents = []
        self.active_inconsistencies = []
        self.current_summary = None

    def export_bundle(self) -> FHIRClinicalBundle:
        """Serializes current clinical session into FHIR R4 Bundle."""
        self.recalculate()
        return FHIRClinicalBundle(
            id=f"bundle-{self.current_patient.id}",
            patient=self.current_patient,
            observations=self.observations,
            inconsistencies=self.active_inconsistencies,
            summary=self.current_summary,
        )


_clinical_store_instance: Optional[ClinicalStore] = None


def get_clinical_store() -> ClinicalStore:
    global _clinical_store_instance
    if _clinical_store_instance is None:
        _clinical_store_instance = ClinicalStore()
    return _clinical_store_instance
