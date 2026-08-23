from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import pandas as pd
import os
from datetime import datetime

class SupplyChainReportGenerator:
    """
    Generates a PDF report for the Supply Chain ESG metrics using ReportLab.
    """

    def __init__(self, data: pd.DataFrame, summary_metrics: dict, output_path: str = "supply_chain_report.pdf"):
        self.data = data
        self.summary_metrics = summary_metrics
        self.output_path = output_path
        self.styles = getSampleStyleSheet()

    def generate_report(self):
        """Builds and saves the PDF report."""
        doc = SimpleDocTemplate(self.output_path, pagesize=letter)
        elements = []

        # Title
        title_style = self.styles["Title"]
        elements.append(Paragraph("Enterprise Supply Chain ESG Report", title_style))
        elements.append(Spacer(1, 20))

        # Date
        date_style = self.styles["Normal"]
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style))
        elements.append(Spacer(1, 20))

        # Executive Summary
        h2_style = self.styles["Heading2"]
        elements.append(Paragraph("Executive Summary", h2_style))
        
        summary_text = f"""
        Total Suppliers Assessed: {self.summary_metrics.get('total_suppliers', 0)}<br/>
        Average ESG Score: {self.summary_metrics.get('avg_esg_score', 0):.1f} / 100<br/>
        Compliant Suppliers: {self.summary_metrics.get('compliant_suppliers', 0)}<br/>
        At-Risk Suppliers: {self.summary_metrics.get('at_risk_suppliers', 0)}<br/>
        Total Scope 3 Emissions: {self.summary_metrics.get('total_scope3_emissions', 0):,.2f} MT CO2e<br/>
        Average Renewable Energy %: {self.summary_metrics.get('avg_renewable_energy', 0):.1f}%
        """
        elements.append(Paragraph(summary_text, self.styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Top Emitters Table
        elements.append(Paragraph("Top 10 Emitters (Suppliers)", h2_style))
        
        top_emitters = self.data.sort_values(by="total_scope3_emissions_mt", ascending=False).head(10)
        
        table_data = [["Supplier Name", "Tier", "ESG Score", "Emissions (MT CO2e)", "Status"]]
        for _, row in top_emitters.iterrows():
            table_data.append([
                row["name"],
                str(row["tier"]),
                f"{row['esg_score']:.0f}",
                f"{row['total_scope3_emissions_mt']:,.1f}",
                row["compliance_status"]
            ])

        table = Table(table_data, colWidths=[180, 50, 70, 120, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F9F9F9")),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#D3D3D3"))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))

        # Conclusion
        elements.append(Paragraph("Recommendations", h2_style))
        rec_text = """
        Based on the current analysis, it is recommended to engage with suppliers labeled as 'At Risk' 
        to improve their ESG scores and renewable energy utilization. Supply chain logistics optimization 
        should focus on transitioning from high-emission transport modes (e.g., Air) to lower-emission 
        alternatives where feasible.
        """
        elements.append(Paragraph(rec_text, self.styles["Normal"]))

        # Build PDF
        doc.build(elements)
        return self.output_path

if __name__ == "__main__":
    from supply_chain_data import SupplyChainDataGenerator
    from supply_chain_logic import SupplyChainLogic
    
    print("Generating demo pdf...")
    gen = SupplyChainDataGenerator(15)
    data = gen.get_full_dataset()
    logic = SupplyChainLogic(data)
    
    scorecard = logic.generate_supplier_scorecard()
    metrics = logic.get_summary_metrics()
    
    report_maker = SupplyChainReportGenerator(scorecard, metrics)
    pdf_path = report_maker.generate_report()
    print(f"Generated PDF at {pdf_path}")
