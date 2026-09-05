"""
Clinical Inconsistency Detection Engine for MedLens.
Cross-checks patient intake (conditions, allergies, medications, symptoms)
against extracted lab observations and reference-range classifications.
"""

from __future__ import annotations
import re
from typing import List, Set
from backend.models.fhir import (
    FHIRPatientIntake,
    FHIRObservation,
    InterpretationCode,
    FHIRInconsistency,
    InconsistencySeverity,
)


class InconsistencyEngine:
    """Clinical rule-based inconsistency and discrepancy detector."""

    # Medication keyword mappings for clinical classes
    THYROID_MEDS = {
        "levothyroxine",
        "synthroid",
        "armour thyroid",
        "methimazole",
        "propylthiouracil",
        "euthyrox",
        "tirosint",
        "cytomel",
        "liothyronine",
    }
    DIABETES_MEDS = {
        "metformin",
        "glipizide",
        "glyburide",
        "glimepiride",
        "insulin",
        "lantus",
        "humalog",
        "novolog",
        "ozempic",
        "semaglutide",
        "mounjaro",
        "tirzepatide",
        "jardiance",
        "empagliflozin",
        "januvia",
        "sitagliptin",
        "farxiga",
        "dapagliflozin",
        "trulicity",
    }
    HYPERTENSION_MEDS = {
        "lisinopril",
        "losartan",
        "amlodipine",
        "metoprolol",
        "atenolol",
        "hydrochlorothiazide",
        "hctz",
        "valsartan",
        "ramipril",
        "enalapril",
        "carvedilol",
        "diltiazem",
        "nifedipine",
        "spironolactone",
    }
    LIPID_MEDS = {
        "atorvastatin",
        "lipitor",
        "rosuvastatin",
        "crestor",
        "simvastatin",
        "pravastatin",
        "ezetimibe",
        "fenofibrate",
    }

    # Allergy to drug cross-reactivity mapping
    ALLERGY_DRUG_MAP = {
        "penicillin": [
            "amoxicillin",
            "augmentin",
            "ampicillin",
            "penicillin",
            "piperacillin",
            "oxacillin",
            "dicloxacillin",
        ],
        "sulfa": [
            "bactrim",
            "septra",
            "sulfamethoxazole",
            "sulfasalazine",
            "sulfadiazine",
        ],
        "nsaid": [
            "ibuprofen",
            "advil",
            "motrin",
            "aleve",
            "naproxen",
            "meloxicam",
            "celecoxib",
            "aspirin",
            "ketorolac",
        ],
        "aspirin": ["aspirin", "bayer", "ecotrin", "excedrin"],
        "statin": [
            "atorvastatin",
            "simvastatin",
            "rosuvastatin",
            "pravastatin",
        ],
    }

    @staticmethod
    def _normalize_tokens(items: List[str]) -> Set[str]:
        tokens = set()
        for item in items:
            for word in re.split(r"[,\s/;\-]+", item.lower()):
                cleaned = re.sub(r"[^a-z0-9]", "", word)
                if len(cleaned) >= 2:
                    tokens.add(cleaned)
        return tokens

    @staticmethod
    def _text_contains_any(source_list: List[str], target_keywords: Set[str]) -> bool:
        full_text = " ".join(source_list).lower()
        for kw in target_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", full_text):
                return True
        return False

    @staticmethod
    def _find_observation(
        observations: List[FHIRObservation], test_keywords: List[str]
    ) -> List[FHIRObservation]:
        matches = []
        for obs in observations:
            name = (obs.code.text or "").lower()
            if any(kw.lower() in name for kw in test_keywords):
                matches.append(obs)
        return matches

    @classmethod
    def check_inconsistencies(
        cls,
        patient: FHIRPatientIntake,
        observations: List[FHIRObservation],
    ) -> List[FHIRInconsistency]:
        """
        Executes multi-axial inconsistency detection across patient intake,
        medication schedule, documented allergies, and extracted lab observations.
        """
        inconsistencies: List[FHIRInconsistency] = []
        conditions = patient.conditions
        meds = patient.medications
        allergies = patient.allergies

        # 1. THYROID DISCREPANCY CHECK
        has_thyroid_condition = cls._text_contains_any(
            conditions,
            {"thyroid", "hypothyroidism", "hyperthyroidism", "hashimoto", "goiter", "graves"},
        )
        has_thyroid_med = cls._text_contains_any(meds, cls.THYROID_MEDS)
        tsh_obs = cls._find_observation(observations, ["tsh", "thyroid stimulating hormone"])
        t4_obs = cls._find_observation(observations, ["free t4", "ft4", "thyroxine"])

        abnormal_tsh = any(
            obs.interpretation in {InterpretationCode.HIGH, InterpretationCode.LOW}
            for obs in tsh_obs
        )
        abnormal_t4 = any(
            obs.interpretation in {InterpretationCode.HIGH, InterpretationCode.LOW}
            for obs in t4_obs
        )

        if (has_thyroid_med or abnormal_tsh or abnormal_t4) and not has_thyroid_condition:
            conflicts = []
            conflicts.append("Intake History: Patient has no documented thyroid conditions.")
            if has_thyroid_med:
                matched_meds = [
                    m for m in meds if any(tm in m.lower() for tm in cls.THYROID_MEDS)
                ]
                conflicts.append(f"Active Medication: Listed {', '.join(matched_meds)}.")
            for obs in tsh_obs:
                val = f"{obs.valueQuantity.value} {obs.valueQuantity.unit}" if obs.valueQuantity else obs.valueString
                conflicts.append(f"Lab Finding: {obs.code.text} is {val} ({obs.interpretation.value}).")

            inconsistencies.append(
                FHIRInconsistency(
                    id="inc-thyroid-01",
                    severity=InconsistencySeverity.WARNING,
                    category="Endocrine & Thyroid Discrepancy",
                    title="Undocumented Thyroid Pathology or Treatment",
                    description=(
                        "Patient intake lists active thyroid medication or lab results demonstrate "
                        "abnormal thyroid markers (TSH/FT4), yet no personal history of thyroid disease is recorded."
                    ),
                    conflicting_elements=conflicts,
                    clinician_action=(
                        "Reconcile patient problem list with medication profile. Verify whether "
                        "patient has an active diagnosis of hypothyroidism/hyperthyroidism or is "
                        "taking replacement therapy unrecorded."
                    ),
                )
            )

        # 2. GLYCEMIC / DIABETES DISCREPANCY CHECK
        has_diabetes_condition = cls._text_contains_any(
            conditions,
            {"diabetes", "diabetic", "t2d", "t1d", "hyperglycemia", "prediabetes", "insulin resistance"},
        )
        has_diabetes_med = cls._text_contains_any(meds, cls.DIABETES_MEDS)
        glucose_obs = cls._find_observation(observations, ["glucose", "fasting blood sugar", "blood sugar"])
        a1c_obs = cls._find_observation(observations, ["hba1c", "hemoglobin a1c", "glycated hemoglobin", "a1c"])

        elevated_glucose = any(
            obs.interpretation == InterpretationCode.HIGH or (obs.valueQuantity and obs.valueQuantity.value >= 126)
            for obs in glucose_obs
        )
        elevated_a1c = any(
            obs.interpretation == InterpretationCode.HIGH or (obs.valueQuantity and obs.valueQuantity.value >= 6.5)
            for obs in a1c_obs
        )

        if (has_diabetes_med or elevated_glucose or elevated_a1c) and not has_diabetes_condition:
            conflicts = []
            conflicts.append("Intake History: Patient has no documented diabetes or prediabetes.")
            if has_diabetes_med:
                matched_meds = [
                    m for m in meds if any(dm in m.lower() for dm in cls.DIABETES_MEDS)
                ]
                conflicts.append(f"Active Medication: Listed {', '.join(matched_meds)}.")
            for obs in a1c_obs:
                val = f"{obs.valueQuantity.value} {obs.valueQuantity.unit}" if obs.valueQuantity else obs.valueString
                conflicts.append(f"Lab Finding: {obs.code.text} is {val} ({obs.interpretation.value}).")
            for obs in glucose_obs:
                val = f"{obs.valueQuantity.value} {obs.valueQuantity.unit}" if obs.valueQuantity else obs.valueString
                conflicts.append(f"Lab Finding: {obs.code.text} is {val} ({obs.interpretation.value}).")

            inconsistencies.append(
                FHIRInconsistency(
                    id="inc-diabetes-01",
                    severity=InconsistencySeverity.WARNING if not elevated_a1c else InconsistencySeverity.CRITICAL,
                    category="Metabolic / Glycemic Discrepancy",
                    title="Elevated Glycemic Markers / Antidiabetic Therapy Without Stated Diagnosis",
                    description=(
                        "Lab records indicate elevated plasma glucose or HbA1c, and/or patient is taking antidiabetic "
                        "pharmacotherapy, but medical history does not include diabetes mellitus."
                    ),
                    conflicting_elements=conflicts,
                    clinician_action=(
                        "Evaluate patient for unconfirmed diabetes mellitus or prediabetes; review fasting status "
                        "and confirm if antidiabetic agents are used for off-label metabolic management."
                    ),
                )
            )

        # 3. HYPERTENSION MEDICATION WITHOUT REPORTED HYPERTENSION
        has_htn_condition = cls._text_contains_any(
            conditions,
            {"hypertension", "high blood pressure", "htn", "elevated bp"},
        )
        has_htn_med = cls._text_contains_any(meds, cls.HYPERTENSION_MEDS)

        if has_htn_med and not has_htn_condition:
            matched_meds = [
                m for m in meds if any(hm in m.lower() for hm in cls.HYPERTENSION_MEDS)
            ]
            inconsistencies.append(
                FHIRInconsistency(
                    id="inc-htn-01",
                    severity=InconsistencySeverity.INFO,
                    category="Cardiovascular History Discrepancy",
                    title="Antihypertensive Medication Without Recorded Hypertension",
                    description=(
                        f"Patient is actively taking antihypertensive medication ({', '.join(matched_meds)}), "
                        "but hypertension is absent from known conditions."
                    ),
                    conflicting_elements=[
                        "Intake Conditions: No hypertension or cardiovascular disorder listed.",
                        f"Active Medication: Listed {', '.join(matched_meds)}.",
                    ],
                    clinician_action=(
                        "Verify clinical indication for antihypertensive therapy (e.g., essential hypertension, "
                        "renal protection, migraine prophylaxis, or heart failure)."
                    ),
                )
            )

        # 4. LIPID LOWERING THERAPY / DYSLIPIDEMIA
        has_lipid_condition = cls._text_contains_any(
            conditions,
            {"hyperlipidemia", "high cholesterol", "dyslipidemia", "hypercholesterolemia"},
        )
        has_lipid_med = cls._text_contains_any(meds, cls.LIPID_MEDS)
        chol_obs = cls._find_observation(observations, ["cholesterol", "ldl", "triglycerides"])
        high_chol = any(obs.interpretation == InterpretationCode.HIGH for obs in chol_obs)

        if (has_lipid_med or high_chol) and not has_lipid_condition:
            conflicts = ["Intake Conditions: No hyperlipidemia or dyslipidemia recorded."]
            if has_lipid_med:
                matched_meds = [
                    m for m in meds if any(lm in m.lower() for lm in cls.LIPID_MEDS)
                ]
                conflicts.append(f"Active Medication: Listed {', '.join(matched_meds)}.")
            for obs in chol_obs:
                if obs.interpretation == InterpretationCode.HIGH:
                    val = f"{obs.valueQuantity.value} {obs.valueQuantity.unit}" if obs.valueQuantity else obs.valueString
                    conflicts.append(f"Lab Finding: {obs.code.text} is {val} (HIGH).")

            inconsistencies.append(
                FHIRInconsistency(
                    id="inc-lipid-01",
                    severity=InconsistencySeverity.INFO,
                    category="Lipid Profile Discrepancy",
                    title="Unrecorded Dyslipidemia with Active Lipid Findings/Therapy",
                    description=(
                        "Lipid-lowering pharmacotherapy or elevated serum lipid panels detected without "
                        "documented hyperlipidemia on patient record."
                    ),
                    conflicting_elements=conflicts,
                    clinician_action="Update electronic problem list to document dyslipidemia or primary prevention indication.",
                )
            )

        # 5. DRUG-ALLERGY DIRECT CONFLICT (CRITICAL SAFETY)
        for allergy in allergies:
            allergy_clean = allergy.lower().strip()
            for drug_class, triggers in cls.ALLERGY_DRUG_MAP.items():
                if drug_class in allergy_clean or any(t in allergy_clean for t in triggers):
                    for med in meds:
                        med_clean = med.lower().strip()
                        if any(t in med_clean for t in triggers):
                            inconsistencies.append(
                                FHIRInconsistency(
                                    id=f"inc-allergy-{drug_class}",
                                    severity=InconsistencySeverity.CRITICAL,
                                    category="Allergy-Medication Cross-Reaction",
                                    title=f"Potential Severe Drug-Allergy Interaction ({drug_class.upper()})",
                                    description=(
                                        f"Patient reports allergy to '{allergy}', but is currently taking '{med}'. "
                                        "This presents a high risk of adverse immune reaction or anaphylaxis."
                                    ),
                                    conflicting_elements=[
                                        f"Documented Allergy: {allergy}",
                                        f"Prescribed/Active Medication: {med}",
                                    ],
                                    clinician_action=(
                                        "URGENT: Verify allergy severity, historical reaction, and hold/switch "
                                        "medication if confirmed true IgE-mediated hypersensitivity."
                                    ),
                                )
                            )

        # 6. RENAL DYSFUNCTION / ELEVATED CREATININE
        creat_obs = cls._find_observation(observations, ["creatinine", "serum creatinine", "egfr", "bun"])
        high_creat = any(
            obs.interpretation == InterpretationCode.HIGH and "creatinine" in (obs.code.text or "").lower()
            for obs in creat_obs
        )
        has_renal_condition = cls._text_contains_any(
            conditions, {"ckd", "kidney", "renal", "nephropathy"}
        )
        if high_creat and not has_renal_condition:
            conflicts = [
                "Intake Conditions: No documented kidney disease or renal insufficiency.",
            ]
            for obs in creat_obs:
                if obs.interpretation in {InterpretationCode.HIGH, InterpretationCode.LOW}:
                    val = f"{obs.valueQuantity.value} {obs.valueQuantity.unit}" if obs.valueQuantity else obs.valueString
                    conflicts.append(f"Lab Finding: {obs.code.text} is {val} ({obs.interpretation.value}).")

            inconsistencies.append(
                FHIRInconsistency(
                    id="inc-renal-01",
                    severity=InconsistencySeverity.WARNING,
                    category="Renal Function Alert",
                    title="Elevated Serum Creatinine Without Renal History",
                    description=(
                        "Lab observations show elevated serum creatinine or abnormal kidney markers, "
                        "without prior documented renal dysfunction in patient intake."
                    ),
                    conflicting_elements=conflicts,
                    clinician_action="Evaluate eGFR trajectory, repeat chemistry panel, and review nephrotoxic medications.",
                )
            )

        return inconsistencies


def detect_inconsistencies(
    patient: FHIRPatientIntake, observations: List[FHIRObservation]
) -> List[FHIRInconsistency]:
    """Helper wrapper for the inconsistency engine."""
    return InconsistencyEngine.check_inconsistencies(patient, observations)
