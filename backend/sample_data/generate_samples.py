"""
Sample Clinical Lab Report Generator for MedLens.
Generates realistic PDF and text lab reports for clinical testing.
"""

from __future__ import annotations
import os
from pathlib import Path


def generate_all_samples():
    sample_dir = Path(__file__).parent
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Thyroid Panel Text
    thyroid_text = """QUEST DIAGNOSTICS - CLINICAL REPORT
PATIENT: Jane Doe          DOB: 1979-04-12    AGE: 45    SEX: Female
COLLECTED: 2026-08-28 08:30    RECEIVED: 2026-08-28 11:15    REPORTED: 2026-08-29 09:00
ORDERING PHYSICIAN: Dr. Robert Vance, MD

TEST NAME                       IN RANGE    OUT OF RANGE    REFERENCE RANGE    UNITS
-------------------------------------------------------------------------------------
TSH                                         6.20     H      0.40 - 4.50        mIU/L
Free T4                         1.15                        0.80 - 1.80        ng/dL
Total T3                        112                         76 - 181           ng/dL
Thyroid Peroxidase Ab                       48.0     H      < 35.0             IU/mL
Thyroglobulin Antibody                      < 1.0           < 1.0              IU/mL
Thyroid Status Note             Euthyroid with elevated TSH
"""
    (sample_dir / "sample_thyroid_panel.txt").write_text(thyroid_text, encoding="utf-8")

    # 2. Comprehensive Metabolic Panel (CMP) Text
    cmp_text = """LABCORP INTEGRATED REPORTING
PATIENT: Johnathan Smith    DOB: 1968-11-03    AGE: 57    SEX: Male
SPECIMEN ID: LC-889210      FASTING: YES
COLLECTED: 2026-08-30 07:45    REPORTED: 2026-08-31 06:10

TEST NAME                       IN RANGE    OUT OF RANGE    REFERENCE RANGE    UNITS
-------------------------------------------------------------------------------------
Glucose, Serum                              148      H      70 - 99            mg/dL
BUN                             18                          7 - 20             mg/dL
Creatinine, Serum                           1.45     H      0.60 - 1.20        mg/dL
eGFR                                        52       L      > 60               mL/min/1.73m2
Sodium                          139                         135 - 145          mmol/L
Potassium                       4.6                         3.5 - 5.1          mmol/L
Chloride                        102                         96 - 106           mmol/L
Carbon Dioxide                  24                          20 - 29            mmol/L
Calcium                         9.4                         8.6 - 10.2         mg/dL
Total Protein                   7.2                         6.0 - 8.5          g/dL
Albumin                         4.1                         3.5 - 5.0          g/dL
Total Bilirubin                 0.7                         0.2 - 1.2          mg/dL
Alkaline Phosphatase            68                          44 - 121           U/L
AST (SGOT)                      26                          10 - 40            U/L
ALT (SGPT)                      32                          7 - 56             U/L
Hemoglobin A1c                              7.1      H      < 5.7              %
Serum Osmolality                292                         275 - 295          mOsm/kg
Unspecified Research Marker     14.2
"""
    (sample_dir / "sample_cmp_panel.txt").write_text(cmp_text, encoding="utf-8")

    # 3. Complete Blood Count (CBC) Text
    cbc_text = """METROPOLITAN HOSPITAL LABORATORY
PATIENT: Emily Davis        DOB: 1993-02-17    AGE: 33    SEX: Female
ORDER: CBC with Differential

TEST NAME                       IN RANGE    OUT OF RANGE    REFERENCE RANGE    UNITS
-------------------------------------------------------------------------------------
White Blood Cell                6.4                         3.8 - 10.8         x10E3/uL
Red Blood Cell                              3.82     L      4.20 - 5.40        x10E6/uL
Hemoglobin                                  10.6     L      12.0 - 16.0        g/dL
Hematocrit                                  32.8     L      37.0 - 47.0        %
MCV                             85.8                        80.0 - 100.0       fL
MCH                             27.7                        27.0 - 33.0        pg
MCHC                            32.3                        32.0 - 36.0        g/dL
Platelet Count                  248                         140 - 400          x10E3/uL
Neutrophils %                   58.2                        40.0 - 74.0        %
Lymphocytes %                   32.1                        19.0 - 48.0        %
Monocytes %                     6.5                         4.0 - 12.0         %
Eosinophils %                   2.6                         0.0 - 7.0          %
Basophils %                     0.6                         0.0 - 2.0          %
Reticulocyte Count              1.2                         0.5 - 2.5          %
Blood Type                      A Positive
"""
    (sample_dir / "sample_cbc_panel.txt").write_text(cbc_text, encoding="utf-8")

    # Attempt to build PDFs using ReportLab if installed
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        def build_pdf(filename: str, title: str, patient_info: str, rows: list):
            doc = SimpleDocTemplate(
                str(sample_dir / filename),
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=36,
                bottomMargin=36,
            )
            styles = getSampleStyleSheet()
            elements = []

            title_style = ParagraphStyle(
                "TitleStyle",
                parent=styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=16,
                textColor=colors.HexColor("#0f172a"),
                spaceAfter=6,
            )
            patient_style = ParagraphStyle(
                "PatientStyle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                textColor=colors.HexColor("#475569"),
                spaceAfter=14,
            )

            elements.append(Paragraph(f"MedLens Clinical Test Data: {title}", title_style))
            elements.append(Paragraph(patient_info, patient_style))
            elements.append(Spacer(1, 10))

            t = Table(rows, colWidths=[180, 80, 70, 110, 80])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                        ("TOPPADDING", (0, 0), (-1, 0), 6),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(t)
            doc.build(elements)

        # Build Thyroid PDF
        thyroid_table = [
            ["Test Name", "In Range", "Out Range", "Reference Range", "Units"],
            ["TSH", "", "6.20 H", "0.40 - 4.50", "mIU/L"],
            ["Free T4", "1.15", "", "0.80 - 1.80", "ng/dL"],
            ["Total T3", "112", "", "76 - 181", "ng/dL"],
            ["Thyroid Peroxidase Ab", "", "48.0 H", "< 35.0", "IU/mL"],
            ["Thyroglobulin Antibody", "< 1.0", "", "< 1.0", "IU/mL"],
        ]
        build_pdf(
            "sample_thyroid_panel.pdf",
            "Thyroid Diagnostic Panel",
            "Patient: Jane Doe | DOB: 1979-04-12 | Age: 45 | Sex: Female | Specimen: Serum | Date: 2026-08-28",
            thyroid_table,
        )

        # Build CMP PDF
        cmp_table = [
            ["Test Name", "In Range", "Out Range", "Reference Range", "Units"],
            ["Glucose, Serum", "", "148 H", "70 - 99", "mg/dL"],
            ["BUN", "18", "", "7 - 20", "mg/dL"],
            ["Creatinine, Serum", "", "1.45 H", "0.60 - 1.20", "mg/dL"],
            ["eGFR", "", "52 L", "> 60", "mL/min/1.73m2"],
            ["Sodium", "139", "", "135 - 145", "mmol/L"],
            ["Potassium", "4.6", "", "3.5 - 5.1", "mmol/L"],
            ["Chloride", "102", "", "96 - 106", "mmol/L"],
            ["Carbon Dioxide", "24", "", "20 - 29", "mmol/L"],
            ["Calcium", "9.4", "", "8.6 - 10.2", "mg/dL"],
            ["Total Protein", "7.2", "", "6.0 - 8.5", "g/dL"],
            ["Albumin", "4.1", "", "3.5 - 5.0", "g/dL"],
            ["Total Bilirubin", "0.7", "", "0.2 - 1.2", "mg/dL"],
            ["Alkaline Phosphatase", "68", "", "44 - 121", "U/L"],
            ["AST (SGOT)", "26", "", "10 - 40", "U/L"],
            ["ALT (SGPT)", "32", "", "7 - 56", "U/L"],
            ["Hemoglobin A1c", "", "7.1 H", "< 5.7", "%"],
        ]
        build_pdf(
            "sample_cmp_panel.pdf",
            "Comprehensive Metabolic Panel (CMP)",
            "Patient: Johnathan Smith | DOB: 1968-11-03 | Age: 57 | Sex: Male | Specimen: Serum | Date: 2026-08-30",
            cmp_table,
        )

        # Build CBC PDF
        cbc_table = [
            ["Test Name", "In Range", "Out Range", "Reference Range", "Units"],
            ["White Blood Cell", "6.4", "", "3.8 - 10.8", "x10E3/uL"],
            ["Red Blood Cell", "", "3.82 L", "4.20 - 5.40", "x10E6/uL"],
            ["Hemoglobin", "", "10.6 L", "12.0 - 16.0", "g/dL"],
            ["Hematocrit", "", "32.8 L", "37.0 - 47.0", "%"],
            ["MCV", "85.8", "", "80.0 - 100.0", "fL"],
            ["Platelet Count", "248", "", "140 - 400", "x10E3/uL"],
            ["Unspecified Factor", "12.5", "", "", ""],
        ]
        build_pdf(
            "sample_cbc_panel.pdf",
            "Complete Blood Count (CBC) with Differential",
            "Patient: Emily Davis | DOB: 1993-02-17 | Age: 33 | Sex: Female | Specimen: Whole Blood | Date: 2026-08-31",
            cbc_table,
        )

    except ImportError:
        pass


if __name__ == "__main__":
    generate_all_samples()
    print("Sample clinical data generated successfully.")
