# MedLens — AI-Powered Clinical Information Intelligence

MedLens consolidates fragmented medical inputs (patient intake questionnaires, laboratory report PDFs, scanned test slips) into a structured, HL7 FHIR-aligned, reviewable clinical dashboard governed by strict non-diagnostic safety boundaries and deterministic provenance tracking.

---

## Key Clinical Features & Safety Architecture

1. **Patient Intake Interface & API**:
   - Structured capture of biological age, sex, reported symptoms, known chronic conditions, drug allergies, and active medications.
   - Immediate cross-referencing with extracted clinical biomarkers.

2. **Multimodal Medical Report Extraction**:
   - Multi-tiered document parsing engine (`pypdf` + regex table extraction + OCR fallback).
   - High-precision extraction of test names, values, units, observation dates, and source reference intervals.

3. **Zero-Hallucination Reference-Range & Provenance Engine**:
   - Strict classification of reported values into `LOW`, `NORMAL`, or `HIGH` **strictly** using boundaries present in the source report.
   - If a lab report omits a reference range, MedLens assigns `UNSPECIFIED` rather than assuming or inventing textbook defaults.
   - Every single observation is tagged with immutable provenance metadata:
     - Source Type: `[User Provided]`, `[Extracted from Lab PDF]`, `[Extracted from Image]`, `[Clinician Edited]`
     - File name & page number
     - Exact verbatim raw text snippet from source
     - Confidence score (0.0 to 1.0)

4. **Non-Diagnostic AI Summary & Safety Guardrails**:
   - Calibrated, patient-friendly summary detailing flagged results.
   - Strict non-diagnostic filter: never diagnoses disease states, never prescribes medications, and never recommends dosages.
   - Formulates constructive consultation questions for the patient's upcoming medical visit.
   - Enforces mandatory clinical review disclaimers on all outputs.

5. **Multi-Axial Clinical Inconsistency Detection**:
   - Cross-checks user intake against lab findings and pharmacotherapy.
   - Highlights discrepancies such as:
     - **Thyroid Mismatch**: Active Levothyroxine therapy or abnormal TSH/FT4 with no documented thyroid disease on intake.
     - **Metabolic Mismatch**: Elevated blood glucose / HbA1c or antidiabetic medication without documented diabetes.
     - **Drug-Allergy Conflict**: Prescribed medication matching a documented allergy (e.g., Penicillin allergy vs Amoxicillin).
     - **Cardiovascular & Renal Alerts**: Antihypertensives without recorded hypertension; elevated serum creatinine without kidney disease history.

6. **HL7 FHIR R4 Alignment & Export**:
   - Native compliance with FHIR resources: `Patient`, `Observation` (LOINC mapped), `ReferenceRange`, `Provenance`, and `Bundle`.
   - 1-click export of complete clinical records as FHIR R4 JSON documents.

---

## Directory Structure

```
MedLens
├── backend/
│   ├── main.py                  # FastAPI server & REST API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── fhir.py              # HL7 FHIR R4 Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── evaluator.py         # Deterministic reference range & provenance engine
│   │   ├── extractor.py         # Multimodal document parsing module
│   │   ├── inconsistency.py     # Rule-based clinical cross-check detector
│   │   └── summarizer.py        # Non-diagnostic clinical summarizer with guardrails
│   ├── storage/
│   │   ├── __init__.py
│   │   └── store.py             # Session repository & JSON persistence
│   ├── sample_data/             # Pre-generated realistic lab PDF & text reports
│   │   ├── generate_samples.py  # Sample generator utility
│   │   ├── sample_thyroid_panel.pdf
│   │   ├── sample_cmp_panel.pdf
│   │   └── sample_cbc_panel.pdf
│   └── tests/
│       ├── test_evaluator.py    # Reference range & provenance unit tests
│       ├── test_extractor.py    # Parsing & unspecified range tests
│       ├── test_inconsistency.py# Clinical inconsistency matrix tests
│       └── test_summarizer.py   # Guardrails & safety disclaimer tests
├── frontend/
│   ├── index.html               # Responsive side-by-side dashboard UI
│   ├── css/
│   │   └── style.css            # Sleek dark clinical glassmorphism design system
│   └── js/
│       └── app.js               # Reactive state manager & FHIR visualizer
├── data/                        # Uploaded reports & persistent clinical bundles
├── requirements.txt             # Python dependencies (FastAPI, Uvicorn, Pydantic, etc.)
└── pytest.ini                   # Pytest test suite configuration
```

---

## Running the Application Locally

1. **Activate Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Run Unit Tests**:
   ```powershell
   python -m pytest backend/tests
   ```

3. **Start the FastAPI Server**:
   ```powershell
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Access the Dashboard**:
   Open your browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```
