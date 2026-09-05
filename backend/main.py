"""
MedLens FastAPI Application Server.
Provides RESTful APIs for patient intake, multimodal report extraction,
deterministic reference-range evaluation, clinical inconsistency detection,
non-diagnostic AI synthesis, and HL7 FHIR R4 Bundle management.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.models.fhir import (
    FHIRClinicalBundle,
    FHIRClinicalSummary,
    FHIRObservation,
    FHIRPatientIntake,
    InterpretationCode,
    ProvenanceRecord,
    ProvenanceSourceType,
)
from backend.services.evaluator import ReferenceRangeEngine, evaluate_observation
from backend.services.extractor import extract_report_from_file
from backend.services.inconsistency import detect_inconsistencies
from backend.services.summarizer import generate_clinical_summary
from backend.storage.store import get_clinical_store

# Application initialization
app = FastAPI(
    title="MedLens — AI-Powered Clinical Information Intelligence",
    description="Consolidates fragmented patient intake and medical reports into a FHIR-aligned, reviewable clinical dashboard.",
    version="1.0.0",
)

# CORS configuration for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
SAMPLE_DIR = BASE_DIR / "backend" / "sample_data"

# Request / Response Schemas
class IntakeRequest(BaseModel):
    id: Optional[str] = "patient-default"
    age: int
    sex: str
    symptoms: List[str] = []
    conditions: List[str] = []
    allergies: List[str] = []
    medications: List[str] = []


class ObservationUpdateRequest(BaseModel):
    value: float
    reference_range_text: Optional[str] = None


class InconsistencyReviewRequest(BaseModel):
    notes: Optional[str] = None


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "MedLens Clinical Intelligence Platform", "version": "1.0.0"}


@app.get("/api/intake", response_model=FHIRPatientIntake)
def get_patient_intake():
    store = get_clinical_store()
    return store.current_patient


@app.post("/api/intake", response_model=FHIRClinicalBundle)
def update_patient_intake(payload: IntakeRequest):
    store = get_clinical_store()
    intake = FHIRPatientIntake(
        id=payload.id or store.current_patient.id,
        age=payload.age,
        sex=payload.sex,
        symptoms=payload.symptoms,
        conditions=payload.conditions,
        allergies=payload.allergies,
        medications=payload.medications,
        provenance=ProvenanceRecord(
            source_type=ProvenanceSourceType.USER_PROVIDED,
            raw_snippet="Patient intake questionnaire submitted",
            confidence_score=1.0,
        ),
    )
    store.update_patient_intake(intake)
    return store.export_bundle()


@app.post("/api/extract")
async def extract_report(file: UploadFile = File(...)):
    """
    Multimodal extraction endpoint.
    Accepts PDF or text laboratory report, parses findings into FHIR observations,
    evaluates reference ranges, and re-computes clinical bundle.
    """
    try:
        content = await file.read()
        filename = file.filename or "uploaded_report.pdf"

        # Save to uploads storage
        store = get_clinical_store()
        saved_path = store.uploads_dir / filename
        saved_path.write_bytes(content)

        # Extract observations
        observations, raw_pages = extract_report_from_file(content, filename)

        if not observations:
            # If no tabular lines matched directly, return informative error
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Could not identify structured laboratory observations in '{filename}'. "
                    "Ensure the report contains standard tabular lab columns (Test Name, Result, Reference Interval, Units)."
                ),
            )

        source_doc = {
            "filename": filename,
            "raw_text": "\n\n--- Page Break ---\n\n".join(raw_pages),
            "extracted_count": len(observations),
        }

        store.add_observations(observations, source_doc=source_doc)
        bundle = store.export_bundle()

        return {
            "message": f"Successfully parsed {len(observations)} observations from {filename}",
            "filename": filename,
            "observations_count": len(observations),
            "raw_text": source_doc["raw_text"],
            "bundle": bundle,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Multimodal extraction processing error: {str(e)}"
        )


@app.post("/api/load-sample/{sample_name}")
def load_sample_report(sample_name: str):
    """
    Loads pre-configured clinical scenario datasets:
    - 'thyroid': High TSH with Levothyroxine intake and no thyroid history (Demonstrates Inconsistency).
    - 'cmp': Comprehensive Metabolic Panel with high glucose, creatinine, low eGFR.
    - 'cbc': Complete Blood Count with low hemoglobin & unspecified factor.
    """
    store = get_clinical_store()
    name_clean = sample_name.lower().strip()

    # Pre-generate sample files if missing
    from backend.sample_data.generate_samples import generate_all_samples
    generate_all_samples()

    if name_clean == "thyroid":
        store.current_patient = FHIRPatientIntake(
            id="pt-thyroid-401",
            age=45,
            sex="Female",
            symptoms=["Persistent fatigue", "Cold intolerance", "Unexplained sluggishness"],
            conditions=["Mild seasonal allergies"],
            allergies=["Penicillin"],
            medications=["Levothyroxine 50 mcg daily", "Vitamin D3 2000 IU"],
            provenance=ProvenanceRecord(
                source_type=ProvenanceSourceType.USER_PROVIDED,
                raw_snippet="Patient intake for Jane Doe",
                confidence_score=1.0,
            ),
        )
        sample_file = SAMPLE_DIR / "sample_thyroid_panel.txt"
        pdf_file = SAMPLE_DIR / "sample_thyroid_panel.pdf"
        file_to_read = pdf_file if pdf_file.exists() else sample_file
        filename = file_to_read.name
        content = file_to_read.read_bytes()

    elif name_clean == "cmp":
        store.current_patient = FHIRPatientIntake(
            id="pt-cmp-502",
            age=57,
            sex="Male",
            symptoms=["Increased thirst", "Frequent nighttime urination", "Bilateral leg cramps"],
            conditions=["Essential hypertension"],
            allergies=["Sulfa drugs"],
            medications=["Lisinopril 20 mg", "Metformin 500 mg BID"],
            provenance=ProvenanceRecord(
                source_type=ProvenanceSourceType.USER_PROVIDED,
                raw_snippet="Patient intake for Johnathan Smith",
                confidence_score=1.0,
            ),
        )
        sample_file = SAMPLE_DIR / "sample_cmp_panel.txt"
        pdf_file = SAMPLE_DIR / "sample_cmp_panel.pdf"
        file_to_read = pdf_file if pdf_file.exists() else sample_file
        filename = file_to_read.name
        content = file_to_read.read_bytes()

    elif name_clean == "cbc":
        store.current_patient = FHIRPatientIntake(
            id="pt-cbc-603",
            age=33,
            sex="Female",
            symptoms=["Exertional shortness of breath", "Lightheadedness", "Brittle nails"],
            conditions=["None documented"],
            allergies=["None known"],
            medications=["None reported"],
            provenance=ProvenanceRecord(
                source_type=ProvenanceSourceType.USER_PROVIDED,
                raw_snippet="Patient intake for Emily Davis",
                confidence_score=1.0,
            ),
        )
        sample_file = SAMPLE_DIR / "sample_cbc_panel.txt"
        pdf_file = SAMPLE_DIR / "sample_cbc_panel.pdf"
        file_to_read = pdf_file if pdf_file.exists() else sample_file
        filename = file_to_read.name
        content = file_to_read.read_bytes()

    else:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown sample scenario '{sample_name}'. Available: 'thyroid', 'cmp', 'cbc'",
        )

    observations, raw_pages = extract_report_from_file(content, filename)
    source_doc = {
        "filename": filename,
        "raw_text": "\n\n--- Page Break ---\n\n".join(raw_pages),
        "extracted_count": len(observations),
    }

    # Reset active observation pool for clear scenario presentation
    store.observations = []
    store.raw_documents = []
    store.add_observations(observations, source_doc=source_doc)
    bundle = store.export_bundle()

    return {
        "message": f"Successfully loaded sample scenario: {sample_name.upper()}",
        "filename": filename,
        "observations_count": len(observations),
        "raw_text": source_doc["raw_text"],
        "bundle": bundle,
    }


@app.patch("/api/observation/{obs_id}", response_model=FHIRObservation)
def update_observation(obs_id: str, payload: ObservationUpdateRequest):
    store = get_clinical_store()
    obs = store.update_observation(
        obs_id=obs_id,
        updated_val=payload.value,
        updated_range=payload.reference_range_text,
    )
    if not obs:
        raise HTTPException(status_code=404, detail=f"Observation '{obs_id}' not found")
    return obs


@app.post("/api/inconsistency/{inc_id}/acknowledge")
def acknowledge_inconsistency(inc_id: str, payload: InconsistencyReviewRequest):
    store = get_clinical_store()
    ok = store.acknowledge_inconsistency(inc_id, notes=payload.notes)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Inconsistency '{inc_id}' not found")
    return {"message": "Inconsistency reviewed and acknowledged", "id": inc_id}


@app.get("/api/bundle", response_model=FHIRClinicalBundle)
def get_fhir_bundle():
    store = get_clinical_store()
    return store.export_bundle()


@app.post("/api/reset")
def reset_session():
    store = get_clinical_store()
    store.clear_all()
    return {"message": "Active clinical session reset successfully", "bundle": store.export_bundle()}


# Mount Static Files (CSS, JS, assets)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "MedLens API running. Frontend index.html not yet built."})
