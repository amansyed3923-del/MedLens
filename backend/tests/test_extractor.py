"""
Unit tests for Medical Report Extractor.
"""

import pytest
from backend.models.fhir import InterpretationCode, ProvenanceSourceType
from backend.services.extractor import MedicalReportExtractor


def test_parse_line_standard_table_flag():
    line = "TSH                     6.20     H    0.40 - 4.50        mIU/L"
    obs = MedicalReportExtractor.parse_line(line, page_number=1, source_file="quest.pdf")
    assert obs is not None
    assert obs.code.text == "TSH"
    assert obs.valueQuantity.value == 6.20
    assert obs.valueQuantity.unit == "mIU/L"
    assert obs.interpretation == InterpretationCode.HIGH
    assert obs.provenance.source_file == "quest.pdf"
    assert obs.provenance.page_number == 1


def test_parse_line_without_reference_range_unspecified():
    """Confirms that tests without reference ranges receive UNSPECIFIED."""
    line = "Blood Group             O Positive"
    obs = MedicalReportExtractor.parse_line(line, page_number=1, source_file="blood_type.txt")
    assert obs is not None
    assert obs.code.text == "Blood Group"
    assert obs.interpretation == InterpretationCode.UNSPECIFIED
    assert obs.referenceRange == []


def test_parse_line_less_than_range():
    line = "Thyroid Peroxidase Ab                 48.0     H      < 35.0             IU/mL"
    obs = MedicalReportExtractor.parse_line(line, page_number=1)
    assert obs is not None
    assert obs.valueQuantity.value == 48.0
    assert obs.interpretation == InterpretationCode.HIGH
