"""
Non-Diagnostic Clinical Summarizer for MedLens.
Generates patient-friendly, objective, educational overviews of flagged laboratory results.

SAFETY GUARDRAILS:
1. STRICT NON-DIAGNOSTIC POLICY: Never diagnoses conditions, never prescribes medication,
   never recommends dosages or changes in therapeutic regimens.
2. Explains *what* each test measures and *how* the value compares to the source reference range.
3. Provides constructive questions the patient can discuss with their physician.
4. Enforces the mandatory clinical disclaimer on all summaries.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from backend.models.fhir import (
    FHIRObservation,
    FHIRPatientIntake,
    InterpretationCode,
    FHIRClinicalSummary,
    FlaggedFindingDetail,
)


class ClinicalSummarizer:
    """Generates strictly non-diagnostic clinical summaries with safety guardrails."""

    # Educational descriptions of standard clinical tests (purely informative, non-diagnostic)
    TEST_DESCRIPTIONS: Dict[str, str] = {
        "tsh": "Thyroid-Stimulating Hormone regulates your body's energy and metabolic rate.",
        "free t4": "Free Thyroxine is a key active hormone produced by the thyroid gland.",
        "glucose": "Blood glucose reflects how your body regulates and utilizes sugar for energy.",
        "fasting blood sugar": "Measures circulating glucose levels after an overnight fast.",
        "hba1c": "Reflects your average blood glucose levels over the preceding 2 to 3 months.",
        "creatinine": "A natural metabolic byproduct filtered by your kidneys; used to assess renal clearance.",
        "bun": "Blood Urea Nitrogen measures nitrogen waste cleared by the kidneys.",
        "egfr": "Estimated Glomerular Filtration Rate calculates kidney filtration efficiency.",
        "alt": "Alanine Aminotransferase is an enzyme primarily found in liver cells.",
        "ast": "Aspartate Aminotransferase is an enzyme present in liver and muscle tissue.",
        "bilirubin": "A pigment formed during normal breakdown of red blood cells, processed by the liver.",
        "hemoglobin": "The iron-rich protein in red blood cells that transports oxygen to your organs.",
        "hematocrit": "The percentage of your total blood volume made up of red blood cells.",
        "platelet count": "Cell fragments essential for normal blood clotting and vessel repair.",
        "white blood cell": "Cells of the immune system that defend against infections and inflammation.",
        "total cholesterol": "An overall measure of circulating blood lipids (fats).",
        "ldl": "Low-Density Lipoprotein cholesterol, often monitored as part of cardiovascular wellness.",
        "hdl": "High-Density Lipoprotein cholesterol, involved in transporting lipids back to the liver.",
        "triglycerides": "A type of fat found in blood that stores unused calories for energy.",
        "potassium": "An essential electrolyte vital for cardiac rhythm, muscle contraction, and nerve signals.",
        "sodium": "A major mineral that maintains fluid balance, blood pressure, and cell function.",
        "calcium": "An essential mineral involved in bone structure, nerve signaling, and muscle function.",
        "vitamin d": "A fat-soluble hormone precursor that aids calcium absorption and immune health.",
    }

    FORBIDDEN_DIAGNOSTIC_PATTERNS = [
        re.compile(r"\byou have (hypothyroidism|hyperthyroidism|diabetes|kidney failure|cancer|anemia|disease|hypertension)\b", re.IGNORECASE),
        re.compile(r"\bwe diagnose\b", re.IGNORECASE),
        re.compile(r"\bthe diagnosis is\b", re.IGNORECASE),
        re.compile(r"\btake (a dose of|\d+\s*(?:mg|mcg|ml))\b", re.IGNORECASE),
        re.compile(r"\bincrease your dose\b", re.IGNORECASE),
        re.compile(r"\bdecrease your dose\b", re.IGNORECASE),
        re.compile(r"\bstop taking\b", re.IGNORECASE),
        re.compile(r"\bprescribe\b", re.IGNORECASE),
    ]

    MANDATORY_DISCLAIMER = (
        "MANDATORY SAFETY DISCLAIMER: MedLens is an informational and educational clinical intelligence "
        "utility. It does NOT provide medical diagnoses, treatment instructions, medication regimens, "
        "or clinical recommendations. All data points, evaluations, and extracted findings must be "
        "independently verified by a licensed physician or healthcare provider before any clinical action."
    )

    @classmethod
    def get_test_context(cls, test_name: str) -> str:
        name_lower = test_name.lower()
        for key, description in cls.TEST_DESCRIPTIONS.items():
            if key in name_lower:
                return description
        return "A clinical laboratory biomarker evaluated against the reporting facility's reference interval."

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Enforces non-diagnostic compliance by stripping any accidental prescriptive language."""
        sanitized = text
        for pattern in cls.FORBIDDEN_DIAGNOSTIC_PATTERNS:
            sanitized = pattern.sub("[Consult your clinician for diagnosis]", sanitized)
        return sanitized

    @classmethod
    def summarize(
        cls,
        patient: FHIRPatientIntake,
        observations: List[FHIRObservation],
    ) -> FHIRClinicalSummary:
        """
        Generates a transparent, non-diagnostic synthesis of observations.
        """
        flagged_list: List[FlaggedFindingDetail] = []
        normal_count = 0
        unspecified_count = 0

        for obs in observations:
            test_name = obs.code.text
            val_str = (
                f"{obs.valueQuantity.value}"
                if obs.valueQuantity
                else (obs.valueString or "Not specified")
            )
            unit_str = obs.valueQuantity.unit if obs.valueQuantity else ""
            range_str = (
                obs.referenceRange[0].text
                if obs.referenceRange and obs.referenceRange[0].text
                else (
                    f"{obs.referenceRange[0].low} - {obs.referenceRange[0].high}"
                    if obs.referenceRange and obs.referenceRange[0].low is not None
                    else "None provided in source report"
                )
            )

            context = cls.get_test_context(test_name)

            if obs.interpretation in {InterpretationCode.LOW, InterpretationCode.HIGH}:
                flagged_list.append(
                    FlaggedFindingDetail(
                        test_name=test_name,
                        value=val_str,
                        unit=unit_str,
                        interpretation=obs.interpretation,
                        reference_range=range_str,
                        clinical_context=context,
                        provenance_tag=obs.provenance.source_type.value,
                    )
                )
            elif obs.interpretation == InterpretationCode.NORMAL:
                normal_count += 1
            else:
                unspecified_count += 1

        total_obs = len(observations)
        flagged_count = len(flagged_list)

        # Build patient overview
        if total_obs == 0:
            headline = "No Lab Observations Available"
            overview = "No laboratory observations have been uploaded or parsed yet. Please upload a lab report to generate insights."
        elif flagged_count == 0:
            headline = f"All {total_obs} Evaluated Tests Are Within Source Reference Ranges"
            overview = (
                f"We reviewed {total_obs} laboratory observations from your submitted report. "
                f"All evaluated values fall within the specific reference intervals established by your testing laboratory."
            )
        else:
            headline = f"Clinical Overview: {flagged_count} Out-of-Range Observation{'s' if flagged_count > 1 else ''} Flagged"
            overview = (
                f"Of {total_obs} reported tests, {flagged_count} value{'s are' if flagged_count > 1 else ' is'} outside "
                f"the reference boundaries documented in your laboratory report. {normal_count} test{'s are' if normal_count != 1 else ' is'} "
                f"within standard limits"
                + (f", and {unspecified_count} had no reference range provided." if unspecified_count > 0 else ".")
            )

        # Prepare clinician consultation discussion points
        discussion_points = []
        if flagged_count > 0:
            discussion_points.append(
                "Review the flagged values above with your doctor to discuss whether any follow-up retesting is advised."
            )
            discussion_points.append(
                "Inquire if your current symptoms, dietary patterns, or current medications could have influenced these laboratory levels."
            )
        if any("tsh" in f.test_name.lower() or "t4" in f.test_name.lower() for f in flagged_list):
            discussion_points.append(
                "Discuss your thyroid hormone panel results in relation to any fatigue, weight changes, or temperature sensitivity you may be experiencing."
            )
        if any("glucose" in f.test_name.lower() or "a1c" in f.test_name.lower() for f in flagged_list):
            discussion_points.append(
                "Ask your physician whether repeat fasting blood work or dietary modifications are recommended for glycemic health."
            )
        if any("creatinine" in f.test_name.lower() or "egfr" in f.test_name.lower() for f in flagged_list):
            discussion_points.append(
                "Confirm whether adequate hydration was maintained prior to testing, and review current kidney filtration indicators."
            )
        if not discussion_points:
            discussion_points.append(
                "Bring these lab results to your upcoming routine checkup to confirm your baseline health metrics."
            )

        # Sanitize overview and discussion points
        clean_overview = cls.sanitize_text(overview)
        clean_discussions = [cls.sanitize_text(dp) for dp in discussion_points]

        return FHIRClinicalSummary(
            headline=headline,
            overview=clean_overview,
            flagged_findings=flagged_list,
            discussion_points=clean_discussions,
            safety_disclaimer=cls.MANDATORY_DISCLAIMER,
        )


def generate_clinical_summary(
    patient: FHIRPatientIntake, observations: List[FHIRObservation]
) -> FHIRClinicalSummary:
    """Helper wrapper to generate non-diagnostic summary."""
    return ClinicalSummarizer.summarize(patient, observations)
