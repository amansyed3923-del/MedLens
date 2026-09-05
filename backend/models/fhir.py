"""
FHIR-Aligned Clinical Data Models for MedLens.
Adheres to HL7 FHIR Release 4 specification conventions for Patient, Observation,
and Provenance resources.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InterpretationCode(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    UNSPECIFIED = "UNSPECIFIED"


class ProvenanceSourceType(str, Enum):
    USER_PROVIDED = "[User Provided]"
    EXTRACTED_FROM_LAB_PDF = "[Extracted from Lab PDF]"
    EXTRACTED_FROM_IMAGE = "[Extracted from Image]"
    CLINICIAN_EDITED = "[Clinician Edited]"


class ProvenanceRecord(BaseModel):
    source_type: ProvenanceSourceType = Field(
        ..., description="Provenance origin tag complying with clinical audit standards"
    )
    source_file: Optional[str] = Field(None, description="Original file name if extracted")
    page_number: Optional[int] = Field(None, description="Page number where data was located")
    raw_snippet: Optional[str] = Field(
        None, description="Verbatim raw text snippet as found in source"
    )
    confidence_score: float = Field(
        1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of record capture or edit",
    )


class FHIRReferenceRange(BaseModel):
    low: Optional[float] = Field(None, description="Lower reference boundary")
    high: Optional[float] = Field(None, description="Upper reference boundary")
    text: Optional[str] = Field(None, description="Verbatim range representation from report")
    unit: Optional[str] = Field(None, description="Measurement unit of the reference range")


class FHIRCoding(BaseModel):
    system: Optional[str] = "http://loinc.org"
    code: Optional[str] = None
    display: str


class FHIRCodeableConcept(BaseModel):
    coding: List[FHIRCoding] = Field(default_factory=list)
    text: str


class FHIRQuantity(BaseModel):
    value: float
    unit: str
    comparator: Optional[str] = None


class FHIRObservation(BaseModel):
    resourceType: str = "Observation"
    id: str
    status: str = "final"
    code: FHIRCodeableConcept
    valueQuantity: Optional[FHIRQuantity] = None
    valueString: Optional[str] = None
    referenceRange: List[FHIRReferenceRange] = Field(default_factory=list)
    interpretation: InterpretationCode = InterpretationCode.UNSPECIFIED
    effectiveDateTime: Optional[str] = None
    category: Optional[str] = Field("laboratory", description="Observation category")
    provenance: ProvenanceRecord


class FHIRPatientIntake(BaseModel):
    resourceType: str = "Patient"
    id: str = "patient-default"
    age: int = Field(..., ge=0, le=130, description="Patient age in years")
    sex: str = Field(..., description="Biological sex (e.g., female, male, other)")
    symptoms: List[str] = Field(default_factory=list, description="Reported active symptoms")
    conditions: List[str] = Field(
        default_factory=list, description="Known past or chronic conditions"
    )
    allergies: List[str] = Field(
        default_factory=list, description="Documented drug or environmental allergies"
    )
    medications: List[str] = Field(
        default_factory=list, description="Current medications with optional dosage"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source_type=ProvenanceSourceType.USER_PROVIDED,
            raw_snippet="Patient intake questionnaire submitted directly",
            confidence_score=1.0,
        )
    )


class InconsistencySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class FHIRInconsistency(BaseModel):
    id: str
    severity: InconsistencySeverity
    category: str
    title: str
    description: str
    conflicting_elements: List[str] = Field(
        default_factory=list, description="List of contradictory statements or findings"
    )
    clinician_action: str = Field(
        ..., description="Recommended verification or clarifying step for clinician"
    )
    is_reviewed: bool = False
    review_notes: Optional[str] = None


class FlaggedFindingDetail(BaseModel):
    test_name: str
    value: str
    unit: str
    interpretation: InterpretationCode
    reference_range: str
    clinical_context: str
    provenance_tag: str


class FHIRClinicalSummary(BaseModel):
    headline: str
    overview: str
    flagged_findings: List[FlaggedFindingDetail] = Field(default_factory=list)
    discussion_points: List[str] = Field(
        default_factory=list, description="Questions for clinician discussion"
    )
    safety_disclaimer: str = Field(
        "MANDATORY SAFETY DISCLAIMER: MedLens is an informational and educational clinical intelligence "
        "utility. It does NOT provide medical diagnoses, treatment instructions, medication regimens, "
        "or clinical recommendations. All data points, evaluations, and extracted findings must be "
        "independently verified by a licensed physician or healthcare provider before any clinical action."
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class FHIRClinicalBundle(BaseModel):
    resourceType: str = "Bundle"
    type: str = "document"
    id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    patient: FHIRPatientIntake
    observations: List[FHIRObservation] = Field(default_factory=list)
    inconsistencies: List[FHIRInconsistency] = Field(default_factory=list)
    summary: Optional[FHIRClinicalSummary] = None
