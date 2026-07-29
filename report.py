"""PDF report generation for EcoBuddy AI."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

from report_validation import validate_report_data


logger = logging.getLogger(__name__)


def generate_pdf(total, eco_score, insight):
    """Generate a PDF only when assessment data passes validation."""
    validation = validate_report_data(total, eco_score, insight)
    if not validation.is_valid:
        logger.warning(
            "PDF generation blocked by invalid assessment data: %s",
            "; ".join(validation.errors),
        )
        return None

    cleaned = validation.cleaned_data

    try:
        file_name = os.path.join(
            tempfile.gettempdir(),
            f"eco_report_{uuid.uuid4().hex}.pdf",
        )
        doc = SimpleDocTemplate(
            file_name,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()

        content = [
            Paragraph("EcoBuddy AI Report", styles["Title"]),
            Paragraph(
                f"Carbon Footprint: {cleaned['total']:.2f} kg CO₂",
                styles["Normal"],
            ),
            Paragraph(
                f"Eco Score: {cleaned['eco_score']:.0f}/100",
                styles["Normal"],
            ),
            Paragraph("Key Insight:", styles["Heading2"]),
            Paragraph(str(cleaned["insight"]), styles["Normal"]),
        ]

        doc.build(content)
        return file_name
    except Exception as exc:
        logger.warning("Could not generate PDF report: %s", exc)
        return None
