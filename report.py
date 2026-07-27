import os
import tempfile
import uuid
import logging
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

logger = logging.getLogger(__name__)

def generate_pdf(total, eco_score, insight):
    """
    Generates a PDF report summarizing carbon footprint and eco score.
    Thread-safe implementation returning the file path of the generated PDF.
    """
    try:
        file_name = os.path.join(tempfile.gettempdir(), f"eco_report_{uuid.uuid4().hex}.pdf")
        doc = SimpleDocTemplate(file_name)
        styles = getSampleStyleSheet()

        content = [
            Paragraph("EcoBuddy AI Report", styles["Title"]),
            Paragraph(f"Carbon Footprint: {total:.2f} kg CO₂", styles["Normal"]),
            Paragraph(f"Eco Score: {eco_score}/100", styles["Normal"]),
            Paragraph("Key Insight:", styles["Heading2"]),
            Paragraph(insight, styles["Normal"])
        ]

        doc.build(content)
        return file_name
    except Exception as e:
        logger.exception("Could not generate PDF report.")
        raise RuntimeError(f"PDF generation failed: {e}")
