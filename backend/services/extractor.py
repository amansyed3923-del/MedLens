"""
Multimodal Medical Report Extractor for MedLens.
Parses laboratory PDF reports, digital test records, and medical scan files.
Extracts test names, quantitative values, measurement units, source reference ranges,
and verbatim provenance snippets with confidence metrics.
"""

from __future__ import annotations
import io
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pypdf
from backend.models.fhir import (
    FHIRObservation,
    ProvenanceSourceType,
)
from backend.services.evaluator import evaluate_observation


class MedicalReportExtractor:
    """Extracts structured lab observations from PDFs and text/scanned files."""

    # Common clinical lab line regex patterns
    # Format 1: Test Name | Value | (Optional Flag) | Reference Range | Units
    # e.g.: TSH    6.20    H    0.40 - 4.50    mIU/L
    PATTERN_TABLE_ROW_FLAG = re.compile(
        r"^(?P<name>[A-Za-z0-9\s,\-\(\)\/\+]+?)\s{2,}"
        r"(?P<val>[><=]?\s*[0-9]+(?:\.[0-9]+)?|[A-Za-z]+)\s+"
        r"(?:(?P<flag>[HL\*]|HIGH|LOW|CRITICAL|ABNORMAL)\s+)?"
        r"(?P<range>(?:[0-9]+(?:\.[0-9]+)?\s*(?:-|–|—|to)\s*[0-9]+(?:\.[0-9]+)?)|(?:[<>]=?\s*[0-9]+(?:\.[0-9]+)?)|Negative|Non-reactive|Normal)\s+"
        r"(?P<unit>[A-Za-z0-9%\/\.\^]+)?",
        re.IGNORECASE,
    )

    # Format 2: Test Name | Value | Units | Reference Range
    # e.g.: Glucose, Serum    142    mg/dL    70 - 99
    PATTERN_TABLE_ROW_STANDARD = re.compile(
        r"^(?P<name>[A-Za-z0-9\s,\-\(\)\/\+]+?)\s{2,}"
        r"(?P<val>[><=]?\s*[0-9]+(?:\.[0-9]+)?)\s+"
        r"(?:(?P<flag>[HL\*]|HIGH|LOW)\s+)?"
        r"(?P<unit>[A-Za-z0-9%\/\.\^]+)\s+"
        r"(?P<range>(?:[0-9]+(?:\.[0-9]+)?\s*(?:-|–|—|to)\s*[0-9]+(?:\.[0-9]+)?)|(?:[<>]=?\s*[0-9]+(?:\.[0-9]+)?)|Negative|Normal)",
        re.IGNORECASE,
    )

    # Format 3: Key-Value style:
    # e.g.: TSH: 6.20 mIU/L (Ref: 0.40 - 4.50)
    PATTERN_KEY_VALUE = re.compile(
        r"^(?P<name>[A-Za-z0-9\s,\-\(\)\/\+]+?):\s*"
        r"(?P<val>[><=]?\s*[0-9]+(?:\.[0-9]+)?)\s*"
        r"(?P<unit>[A-Za-z0-9%\/\.\^]+)?\s*"
        r"(?:\((?:Ref|Reference|Range|Ref Range)?[:\s]*(?P<range>[^)]+)\))?",
        re.IGNORECASE,
    )

    # Format 4: Delimited line without range (results in UNSPECIFIED):
    # e.g.: Blood Group    O Positive
    PATTERN_NO_RANGE = re.compile(
        r"^(?P<name>[A-Za-z0-9\s,\-\(\)\/\+]{3,}?)\s{2,}"
        r"(?P<val>[0-9]+(?:\.[0-9]+)?|[A-Za-z0-9\+\-]+)\s*"
        r"(?P<unit>[A-Za-z0-9%\/\.\^]+)?$",
        re.IGNORECASE,
    )

    # LOINC coding registry map for clinical lab tests
    LOINC_REGISTRY: Dict[str, str] = {
        "tsh": "3016-3",
        "thyroid stimulating hormone": "3016-3",
        "free t4": "2284-8",
        "ft4": "2284-8",
        "glucose": "2345-7",
        "fasting blood sugar": "1558-6",
        "hba1c": "4548-4",
        "hemoglobin a1c": "4548-4",
        "creatinine": "2160-0",
        "serum creatinine": "2160-0",
        "bun": "3094-0",
        "blood urea nitrogen": "3094-0",
        "egfr": "33914-3",
        "alt": "1742-6",
        "ast": "1920-8",
        "bilirubin": "1975-2",
        "total cholesterol": "2093-3",
        "hdl": "2085-9",
        "ldl": "13457-7",
        "triglycerides": "2571-8",
        "hemoglobin": "718-7",
        "hematocrit": "4544-3",
        "white blood cell": "6690-2",
        "wbc": "6690-2",
        "platelets": "777-3",
        "potassium": "2823-3",
        "sodium": "2951-2",
        "calcium": "17861-6",
    }

    @classmethod
    def match_loinc(cls, test_name: str) -> Optional[str]:
        cleaned = test_name.lower().strip()
        for key, code in cls.LOINC_REGISTRY.items():
            if key == cleaned or f" {key} " in f" {cleaned} ":
                return code
        return None

    @classmethod
    def parse_line(
        cls, line: str, page_number: int = 1, source_file: str = "report.pdf"
    ) -> Optional[FHIRObservation]:
        """Attempts to parse a single line of lab text into a FHIRObservation."""
        clean = line.strip()
        if not clean or len(clean) < 4:
            return None

        # Ignore common table header titles
        lower = clean.lower()
        if any(
            hdr in lower
            for hdr in [
                "test name",
                "component",
                "reference range",
                "in range",
                "out of range",
                "flag",
                "units",
                "collected:",
                "received:",
                "reported:",
                "patient:",
                "dob:",
                "physician:",
                "page ",
            ]
        ):
            return None

        name: Optional[str] = None
        val_float: Optional[float] = None
        unit: str = ""
        range_str: Optional[str] = None
        confidence = 0.90

        # Attempt Format 1 (Table row with optional flag)
        m = cls.PATTERN_TABLE_ROW_FLAG.match(clean)
        if m:
            name = m.group("name").strip()
            val_str = m.group("val").strip()
            range_str = m.group("range").strip() if m.group("range") else None
            unit = m.group("unit").strip() if m.group("unit") else ""
            try:
                val_float = float(re.sub(r"[><=]", "", val_str).strip())
            except ValueError:
                val_float = None
            confidence = 0.96

        # Attempt Format 2 (Standard table row: Name | Val | Unit | Range)
        if not name:
            m = cls.PATTERN_TABLE_ROW_STANDARD.match(clean)
            if m:
                name = m.group("name").strip()
                val_str = m.group("val").strip()
                unit = m.group("unit").strip() if m.group("unit") else ""
                range_str = m.group("range").strip() if m.group("range") else None
                try:
                    val_float = float(re.sub(r"[><=]", "", val_str).strip())
                except ValueError:
                    val_float = None
                confidence = 0.94

        # Attempt Format 3 (Key-Value: Name: Value Unit (Ref: Range))
        if not name:
            m = cls.PATTERN_KEY_VALUE.match(clean)
            if m:
                name = m.group("name").strip()
                val_str = m.group("val").strip()
                unit = m.group("unit").strip() if m.group("unit") else ""
                range_str = m.group("range").strip() if m.group("range") else None
                try:
                    val_float = float(re.sub(r"[><=]", "", val_str).strip())
                except ValueError:
                    val_float = None
                confidence = 0.92

        # Attempt Format 4 (No reference range present in line -> UNSPECIFIED)
        if not name:
            m = cls.PATTERN_NO_RANGE.match(clean)
            if m:
                cand_name = m.group("name").strip()
                val_raw = m.group("val").strip()
                unit = m.group("unit").strip() if m.group("unit") else ""
                # Only accept if candidate name doesn't look like general text
                if len(cand_name.split()) <= 5:
                    name = cand_name
                    range_str = None  # Explicitly None -> engine will assign UNSPECIFIED!
                    try:
                        val_float = float(val_raw)
                    except ValueError:
                        val_float = None
                    confidence = 0.85

        if not name:
            return None

        # Clean name from trailing punctuation/spaces
        name = re.sub(r"[:\-\.]+$", "", name).strip()
        if len(name) < 2:
            return None

        test_id = f"obs-{re.sub(r'[^a-zA-Z0-9]+', '-', name).lower().strip('-')}"
        loinc = cls.match_loinc(name)

        return evaluate_observation(
            test_id=test_id,
            test_name=name,
            value=val_float,
            unit=unit,
            range_text=range_str,
            source_type=ProvenanceSourceType.EXTRACTED_FROM_LAB_PDF,
            source_file=source_file,
            page_number=page_number,
            raw_snippet=clean,
            confidence_score=confidence,
            loinc_code=loinc,
            effective_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )

    @classmethod
    def extract_from_pdf(
        cls, file_bytes: bytes, filename: str = "report.pdf"
    ) -> Tuple[List[FHIRObservation], List[str]]:
        """
        Parses a PDF document into a list of FHIRObservation objects and raw text pages.
        """
        observations: List[FHIRObservation] = []
        raw_pages: List[str] = []

        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page_idx, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text(extraction_mode="layout") or ""
                except Exception:
                    page_text = page.extract_text() or ""
                raw_pages.append(page_text)

                for line in page_text.splitlines():
                    obs = cls.parse_line(line, page_number=page_idx, source_file=filename)
                    if obs:
                        # Avoid duplicates
                        if not any(o.id == obs.id for o in observations):
                            observations.append(obs)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

        return observations, raw_pages

    @classmethod
    def extract_from_text(
        cls, text: str, filename: str = "report.txt"
    ) -> Tuple[List[FHIRObservation], List[str]]:
        """Parses raw text or OCR text into observations."""
        observations: List[FHIRObservation] = []
        for line in text.splitlines():
            obs = cls.parse_line(line, page_number=1, source_file=filename)
            if obs:
                if not any(o.id == obs.id for o in observations):
                    observations.append(obs)
        return observations, [text]


def extract_report_from_file(
    content: bytes, filename: str
) -> Tuple[List[FHIRObservation], List[str]]:
    """Helper dispatcher for file parsing."""
    if filename.lower().endswith(".pdf"):
        return MedicalReportExtractor.extract_from_pdf(content, filename)
    else:
        # Text or decoded file
        text = content.decode("utf-8", errors="replace")
        return MedicalReportExtractor.extract_from_text(text, filename)
