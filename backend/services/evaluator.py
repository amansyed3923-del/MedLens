"""
Reference-Range & Provenance Engine for MedLens.

STRICT CLINICAL RULES:
1. Strictly evaluates LOW, NORMAL, or HIGH using ONLY reference ranges present in the source report.
2. If no reference range is provided or found, explicitly assigns UNSPECIFIED.
   NEVER defaults to external textbook ranges or unverified assumptions.
3. Tags every single observation with provenance metadata: source type, source file,
   page number, raw extracted snippet, and confidence score.
"""

from __future__ import annotations
import re
from typing import Optional, Tuple
from backend.models.fhir import (
    InterpretationCode,
    ProvenanceSourceType,
    ProvenanceRecord,
    FHIRReferenceRange,
    FHIRObservation,
    FHIRCodeableConcept,
    FHIRCoding,
    FHIRQuantity,
)


class ReferenceRangeEngine:
    """Deterministic parser and evaluator for laboratory reference ranges."""

    # Regex patterns for range parsing
    RANGE_BETWEEN_PATTERN = re.compile(
        r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|—|to)\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        re.IGNORECASE,
    )
    LESS_THAN_PATTERN = re.compile(
        r"^\s*(?:<|<=|less\s+than)\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        re.IGNORECASE,
    )
    GREATER_THAN_PATTERN = re.compile(
        r"^\s*(?:>|>=|greater\s+than)\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        re.IGNORECASE,
    )

    @classmethod
    def parse_reference_range(
        cls, range_text: Optional[str], unit: Optional[str] = None
    ) -> Optional[FHIRReferenceRange]:
        """
        Parses raw text into numeric boundaries (low, high).
        Returns None if text is absent or denotes an unestablished range.
        """
        if not range_text:
            return None

        clean_text = range_text.strip()
        if not clean_text or clean_text.upper() in {
            "NONE",
            "N/A",
            "NA",
            "UNSPECIFIED",
            "NOT ESTABLISHED",
            "-",
            "--",
            "SEE NOTE",
            "UNKNOWN",
        }:
            return None

        # Try "low - high" (e.g. 3.5 - 5.0)
        m_between = cls.RANGE_BETWEEN_PATTERN.match(clean_text)
        if m_between:
            try:
                low = float(m_between.group(1))
                high = float(m_between.group(2))
                return FHIRReferenceRange(low=low, high=high, text=clean_text, unit=unit)
            except ValueError:
                pass

        # Try "< high" (e.g. < 100)
        m_less = cls.LESS_THAN_PATTERN.match(clean_text)
        if m_less:
            try:
                high = float(m_less.group(1))
                return FHIRReferenceRange(low=None, high=high, text=clean_text, unit=unit)
            except ValueError:
                pass

        # Try "> low" (e.g. > 60)
        m_greater = cls.GREATER_THAN_PATTERN.match(clean_text)
        if m_greater:
            try:
                low = float(m_greater.group(1))
                return FHIRReferenceRange(low=low, high=None, text=clean_text, unit=unit)
            except ValueError:
                pass

        # Textual range (e.g., "Negative", "Non-Reactive")
        return FHIRReferenceRange(low=None, high=None, text=clean_text, unit=unit)

    @classmethod
    def evaluate_value(
        cls, value: Optional[float], ref_range: Optional[FHIRReferenceRange]
    ) -> InterpretationCode:
        """
        Deterministically evaluates numeric value against reference range.
        STRICT REQUIREMENT: If ref_range is missing or has no bounds, return UNSPECIFIED.
        """
        if value is None or ref_range is None:
            return InterpretationCode.UNSPECIFIED

        # Low and high bound range
        if ref_range.low is not None and ref_range.high is not None:
            if value < ref_range.low:
                return InterpretationCode.LOW
            elif value > ref_range.high:
                return InterpretationCode.HIGH
            else:
                return InterpretationCode.NORMAL

        # Upper bound only (< X)
        if ref_range.high is not None and ref_range.low is None:
            if value > ref_range.high:
                return InterpretationCode.HIGH
            else:
                return InterpretationCode.NORMAL

        # Lower bound only (> X)
        if ref_range.low is not None and ref_range.high is None:
            if value < ref_range.low:
                return InterpretationCode.LOW
            else:
                return InterpretationCode.NORMAL

        # Range was present as text only without numeric limits
        return InterpretationCode.UNSPECIFIED


def evaluate_observation(
    test_id: str,
    test_name: str,
    value: Optional[float],
    unit: str,
    range_text: Optional[str],
    source_type: ProvenanceSourceType = ProvenanceSourceType.EXTRACTED_FROM_LAB_PDF,
    source_file: Optional[str] = None,
    page_number: Optional[int] = 1,
    raw_snippet: Optional[str] = None,
    confidence_score: float = 1.0,
    loinc_code: Optional[str] = None,
    effective_date: Optional[str] = None,
) -> FHIRObservation:
    """
    Constructs a complete FHIRObservation with strictly verified provenance
    and deterministic interpretation.
    """
    ref_range = ReferenceRangeEngine.parse_reference_range(range_text, unit=unit)
    interpretation = ReferenceRangeEngine.evaluate_value(value, ref_range)

    provenance = ProvenanceRecord(
        source_type=source_type,
        source_file=source_file,
        page_number=page_number,
        raw_snippet=raw_snippet or f"{test_name}: {value} {unit} (Ref: {range_text or 'None'})",
        confidence_score=confidence_score,
    )

    coding_list = []
    if loinc_code:
        coding_list.append(
            FHIRCoding(system="http://loinc.org", code=loinc_code, display=test_name)
        )
    else:
        coding_list.append(
            FHIRCoding(system="http://medlens.internal", code=test_id, display=test_name)
        )

    val_qty = FHIRQuantity(value=value, unit=unit) if value is not None else None

    return FHIRObservation(
        id=test_id,
        resourceType="Observation",
        status="final",
        code=FHIRCodeableConcept(coding=coding_list, text=test_name),
        valueQuantity=val_qty,
        valueString=str(value) if value is not None else None,
        referenceRange=[ref_range] if ref_range else [],
        interpretation=interpretation,
        effectiveDateTime=effective_date,
        provenance=provenance,
    )
