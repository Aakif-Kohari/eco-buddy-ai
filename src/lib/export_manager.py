"""
CSV Export Manager for EcoBuddy AI
Handles exporting assessment data to CSV, Excel, and other formats.
"""

import pandas as pd
import io
import csv
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import streamlit as st
import os
import zipfile
from pathlib import Path
import re
import hashlib
import base64
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for data export."""
    format: str = "csv"  # csv, excel, json
    include_all_columns: bool = True
    columns_to_include: List[str] = field(default_factory=list)
    date_format: str = "%Y-%m-%d %H:%M:%S"
    include_metadata: bool = True
    separator: str = ","
    decimal: str = "."
    encoding: str = "utf-8"
    include_summary: bool = True
    compress: bool = False
    password: Optional[str] = None
    sheet_name: str = "Assessments"
    max_rows_per_file: int = 10000
    use_quotes: bool = True
    quote_char: str = '"'
    escape_char: str = '\\'
    line_terminator: str = '\n'
    na_rep: str = ""
    float_format: str = "%.2f"


@dataclass
class ExportResult:
    """Result of export operation."""
    success: bool
    message: str
    data: Optional[bytes] = None
    filename: str = ""
    format: str = "csv"
    row_count: int = 0
    file_size_kb: float = 0.0
    summary: Optional[Dict[str, Any]] = None
    export_time_ms: float = 0.0
    columns_exported: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ExportManager:
    """
    Handles exporting assessment data to various formats.
    Supports CSV, Excel, JSON, and more.
    """
    
    def __init__(self):
        self.config = ExportConfig()
        self._export_history: List[Dict[str, Any]] = []
        self._cache: Dict[str, bytes] = {}
        
    def export_assessments(
        self,
        assessments: List[Dict[str, Any]],
        format: str = "csv",
        config: Optional[ExportConfig] = None
    ) -> ExportResult:
        """
        Export assessments to specified format.
        
        Args:
            assessments: List of assessment dictionaries
            format: Export format ('csv', 'excel', 'json')
            config: Export configuration
        
        Returns:
            ExportResult object
        """
        start_time = datetime.now()
        
        if config:
            self.config = config
        
        if not assessments:
            return ExportResult(
                success=False,
                message="No data to export",
                row_count=0
            )
        
        try:
            # Convert to DataFrame
            df = self._prepare_dataframe(assessments)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"assessment_export_{timestamp}"
            
            # Determine format
            format_lower = format.lower()
            
            if format_lower == "csv":
                result = self._export_csv(df, filename)
            elif format_lower == "excel":
                result = self._export_excel(df, filename)
            elif format_lower == "json":
                result = self._export_json(df, filename)
            elif format_lower == "html":
                result = self._export_html(df, filename)
            elif format_lower == "markdown":
                result = self._export_markdown(df, filename)
            elif format_lower == "parquet":
                result = self._export_parquet(df, filename)
            elif format_lower == "feather":
                result = self._export_feather(df, filename)
            elif format_lower == "pickle":
                result = self._export_pickle(df, filename)
            elif format_lower == "tsv":
                result = self._export_tsv(df, filename)
            elif format_lower == "multi":
                result = self._export_multi_format(df, filename)
            else:
                return ExportResult(
                    success=False,
                    message=f"Unsupported format: {format}"
                )
            
            # Add summary if requested
            if self.config.include_summary and result.success:
                result.summary = self.export_summary(assessments)
            
            # Add columns exported
            result.columns_exported = df.columns.tolist()
            
            # Record export time
            result.export_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Save to history
            self._export_history.append({
                "timestamp": datetime.now(),
                "format": result.format,
                "row_count": result.row_count,
                "filename": result.filename,
                "file_size_kb": result.file_size_kb,
                "success": result.success
            })
            
            return result
                
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                message=f"Export failed: {str(e)}",
                warnings=[str(e)]
            )
    
    def _prepare_dataframe(self, assessments: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare DataFrame from assessments with proper formatting."""
        if not assessments:
            return pd.DataFrame()
        
        df = pd.DataFrame(assessments)
        
        # Format datetime columns
        datetime_columns = ["date", "created_at", "updated_at", "assessment_date"]
        for col in datetime_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col]).dt.strftime(self.config.date_format)
                except:
                    pass
        
        # Format numeric columns
        numeric_columns = ["footprint", "eco_score", "distance", "electricity", 
                          "flights", "kg_co2", "score", "rating"]
        for col in numeric_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
                except:
                    pass
        
        # Rename columns for better readability
        column_rename = {
            "id": "ID",
            "user_id": "User ID",
            "user_name": "User Name",
            "user_email": "User Email",
            "date": "Date",
            "created_at": "Created At",
            "updated_at": "Updated At",
            "assessment_date": "Assessment Date",
            "transport": "Transport Mode",
            "transport_mode": "Transport Mode",
            "distance": "Distance (km)",
            "electricity": "Electricity (kWh)",
            "electricity_usage": "Electricity (kWh)",
            "diet": "Diet Type",
            "diet_type": "Diet Type",
            "flights": "Flights (per year)",
            "flight_hours": "Flight Hours",
            "footprint": "Carbon Footprint (kg CO₂)",
            "carbon_footprint": "Carbon Footprint (kg CO₂)",
            "eco_score": "Eco Score",
            "eco_score": "Eco Score",
            "energy_efficiency": "Energy Efficiency",
            "waste_management": "Waste Management",
            "water_usage": "Water Usage",
            "recycling": "Recycling",
            "green_energy": "Green Energy",
            "sustainability": "Sustainability Score",
            "environmental_impact": "Environmental Impact",
            "carbon_offset": "Carbon Offset",
            "renewable_energy": "Renewable Energy %",
            "energy_savings": "Energy Savings",
            "co2_reduction": "CO₂ Reduction",
            "trees_planted": "Trees Planted",
            "total_score": "Total Score",
            "category": "Category",
            "subcategory": "Subcategory",
            "status": "Status",
            "priority": "Priority",
            "assignment": "Assignment",
            "project": "Project Name",
            "department": "Department",
            "location": "Location",
            "region": "Region",
            "country": "Country",
        }
        
        existing_cols = {k: v for k, v in column_rename.items() if k in df.columns}
        df = df.rename(columns=existing_cols)
        
        # Reorder columns - prioritize common fields
        preferred_order = [
            "ID", "Date", "Created At", "Updated At",
            "User ID", "User Name", "User Email",
            "Transport Mode", "Distance (km)",
            "Electricity (kWh)", "Diet Type",
            "Flights (per year)", "Flight Hours",
            "Carbon Footprint (kg CO₂)", "Eco Score",
            "Total Score", "Sustainability Score",
            "Category", "Status", "Priority"
        ]
        
        # Keep only columns that exist
        existing_order = [col for col in preferred_order if col in df.columns]
        
        # Add any remaining columns not in preferred order
        remaining_cols = [col for col in df.columns if col not in existing_order]
        existing_order.extend(remaining_cols)
        
        df = df[existing_order]
        
        # Round numeric columns
        for col in df.select_dtypes(include=['float64', 'float32']).columns:
            try:
                df[col] = df[col].round(2)
            except:
                pass
        
        # Handle missing values
        df = df.fillna("")
        
        # Remove duplicate columns if any
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    
    def _export_csv(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to CSV with advanced options."""
        try:
            # Create CSV options
            csv_kwargs = {
                'index': False,
                'sep': self.config.separator,
                'decimal': self.config.decimal,
                'encoding': self.config.encoding,
                'na_rep': self.config.na_rep,
                'float_format': self.config.float_format,
                'line_terminator': self.config.line_terminator,
                'quotechar': self.config.quote_char,
                'quoting': csv.QUOTE_MINIMAL if self.config.use_quotes else csv.QUOTE_NONE,
                'escapechar': self.config.escape_char if self.config.use_quotes else None,
                'date_format': self.config.date_format
            }
            
            output = io.StringIO()
            df.to_csv(output, **csv_kwargs)
            csv_data = output.getvalue().encode(self.config.encoding)
            file_size = len(csv_data) / 1024
            
            # Validate CSV
            try:
                # Test reading back
                test_df = pd.read_csv(io.StringIO(csv_data.decode(self.config.encoding)))
                row_count = len(test_df)
            except:
                row_count = len(df)
            
            # Compress if requested
            if self.config.compress:
                import gzip
                compressed_data = gzip.compress(csv_data, compresslevel=9)
                filename = f"{filename}.csv.gz"
                data = compressed_data
            else:
                filename = f"{filename}.csv"
                data = csv_data
            
            return ExportResult(
                success=True,
                message="CSV exported successfully",
                data=data,
                filename=filename,
                format="csv" if not self.config.compress else "csv.gz",
                row_count=row_count,
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"CSV export failed: {str(e)}"
            )
    
    def _export_tsv(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to TSV (Tab-Separated Values)."""
        original_sep = self.config.separator
        self.config.separator = '\t'
        result = self._export_csv(df, filename)
        self.config.separator = original_sep
        result.format = "tsv"
        return result
    
    def _export_excel(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to Excel with formatting."""
        try:
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name=self.config.sheet_name, index=False)
                
                # Get the worksheet
                worksheet = writer.sheets[self.config.sheet_name]
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value is not None:
                                cell_length = len(str(cell.value))
                                if cell_length > max_length:
                                    max_length = cell_length
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 60)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Add some styling
                from openpyxl.styles import Font, PatternFill, Alignment
                
                # Style the header row
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Add summary sheet if requested
                if self.config.include_summary and len(df) > 0:
                    summary_df = pd.DataFrame([{
                        "Total Rows": len(df),
                        "Total Columns": len(df.columns),
                        "Export Date": datetime.now().strftime(self.config.date_format),
                        "Format": "Excel",
                        "Columns": ", ".join(df.columns[:10]) + ("..." if len(df.columns) > 10 else "")
                    }])
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)
            
            output.seek(0)
            excel_data = output.getvalue()
            file_size = len(excel_data) / 1024
            
            # Compress if requested
            if self.config.compress:
                import gzip
                compressed_data = gzip.compress(excel_data, compresslevel=9)
                filename = f"{filename}.xlsx.gz"
                data = compressed_data
            else:
                filename = f"{filename}.xlsx"
                data = excel_data
            
            return ExportResult(
                success=True,
                message="Excel exported successfully",
                data=data,
                filename=filename,
                format="excel" if not self.config.compress else "excel.gz",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Excel export failed: {str(e)}"
            )
    
    def _export_json(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to JSON with options."""
        try:
            # Convert to dict
            data = df.to_dict(orient='records')
            
            # Create JSON structure with metadata
            export_data = {
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "row_count": len(data),
                    "columns": df.columns.tolist(),
                    "format_version": "1.0"
                },
                "data": data
            }
            
            if self.config.include_summary:
                export_data["summary"] = {
                    "total_rows": len(data),
                    "total_columns": len(df.columns),
                    "numeric_columns": len(df.select_dtypes(include=['number']).columns),
                    "string_columns": len(df.select_dtypes(include=['object']).columns),
                    "date_columns": len(df.select_dtypes(include=['datetime64']).columns)
                }
            
            json_str = json.dumps(export_data, indent=2, default=str, ensure_ascii=False)
            json_data = json_str.encode(self.config.encoding)
            file_size = len(json_data) / 1024
            
            # Compress if requested
            if self.config.compress:
                import gzip
                compressed_data = gzip.compress(json_data, compresslevel=9)
                filename = f"{filename}.json.gz"
                data = compressed_data
            else:
                filename = f"{filename}.json"
                data = json_data
            
            return ExportResult(
                success=True,
                message="JSON exported successfully",
                data=data,
                filename=filename,
                format="json" if not self.config.compress else "json.gz",
                row_count=len(data),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"JSON export failed: {str(e)}"
            )
    
    def _export_html(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to HTML with styling."""
        try:
            # Create styled HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="{self.config.encoding}">
                <title>Assessment Data Export</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; }}
                    .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
                    th {{ background-color: #4F81BD; color: white; padding: 12px; text-align: left; }}
                    td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    .even {{ background-color: #f9f9f9; }}
                    .odd {{ background-color: #ffffff; }}
                    .footer {{ margin-top: 20px; color: #7f8c8d; font-size: 12px; }}
                </style>
            </head>
            <body>
                <h1>📊 Assessment Data Export</h1>
                <div class="summary">
                    <p><strong>Export Date:</strong> {datetime.now().strftime(self.config.date_format)}</p>
                    <p><strong>Total Records:</strong> {len(df)}</p>
                    <p><strong>Total Columns:</strong> {len(df.columns)}</p>
                </div>
                <table>
                    <thead>
                        <tr>
                            {''.join(f'<th>{col}</th>' for col in df.columns)}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(
                            f'<tr class="{"even" if i % 2 == 0 else "odd"}">'
                            + ''.join(f'<td>{str(row[col])[:100]}</td>' for col in df.columns)
                            + '</tr>'
                            for i, row in enumerate(df.to_dict('records'))
                        )}
                    </tbody>
                </table>
                <div class="footer">
                    <p>Generated by EcoBuddy AI Export Manager</p>
                </div>
            </body>
            </html>
            """
            
            html_data = html_content.encode(self.config.encoding)
            file_size = len(html_data) / 1024
            
            return ExportResult(
                success=True,
                message="HTML exported successfully",
                data=html_data,
                filename=f"{filename}.html",
                format="html",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"HTML export failed: {str(e)}"
            )
    
    def _export_markdown(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to Markdown table format."""
        try:
            # Create markdown table
            headers = "| " + " | ".join(df.columns) + " |"
            separator = "| " + " | ".join(["---"] * len(df.columns)) + " |"
            
            rows = []
            for _, row in df.iterrows():
                row_values = []
                for col in df.columns:
                    value = str(row[col])[:50]  # Truncate long values
                    row_values.append(value)
                rows.append("| " + " | ".join(row_values) + " |")
            
            markdown_content = f"""# Assessment Data Export

**Export Date:** {datetime.now().strftime(self.config.date_format)}
**Total Records:** {len(df)}
**Total Columns:** {len(df.columns)}

## Data Table

{headers}
{separator}
{chr(10).join(rows)}

---
*Generated by EcoBuddy AI Export Manager*
"""
            
            markdown_data = markdown_content.encode(self.config.encoding)
            file_size = len(markdown_data) / 1024
            
            return ExportResult(
                success=True,
                message="Markdown exported successfully",
                data=markdown_data,
                filename=f"{filename}.md",
                format="markdown",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Markdown export failed: {str(e)}"
            )
    
    def _export_parquet(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to Parquet format."""
        try:
            output = io.BytesIO()
            df.to_parquet(output, index=False, engine='pyarrow')
            output.seek(0)
            parquet_data = output.getvalue()
            file_size = len(parquet_data) / 1024
            
            return ExportResult(
                success=True,
                message="Parquet exported successfully",
                data=parquet_data,
                filename=f"{filename}.parquet",
                format="parquet",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Parquet export failed: {str(e)}"
            )
    
    def _export_feather(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to Feather format."""
        try:
            output = io.BytesIO()
            df.to_feather(output)
            output.seek(0)
            feather_data = output.getvalue()
            file_size = len(feather_data) / 1024
            
            return ExportResult(
                success=True,
                message="Feather exported successfully",
                data=feather_data,
                filename=f"{filename}.feather",
                format="feather",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Feather export failed: {str(e)}"
            )
    
    def _export_pickle(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to Pickle format."""
        try:
            import pickle
            output = io.BytesIO()
            pickle.dump(df, output)
            output.seek(0)
            pickle_data = output.getvalue()
            file_size = len(pickle_data) / 1024
            
            return ExportResult(
                success=True,
                message="Pickle exported successfully",
                data=pickle_data,
                filename=f"{filename}.pkl",
                format="pickle",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Pickle export failed: {str(e)}"
            )
    
    def _export_multi_format(self, df: pd.DataFrame, filename: str) -> ExportResult:
        """Export to multiple formats as a ZIP file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add CSV
                csv_result = self._export_csv(df, f"{filename}_csv")
                if csv_result.success:
                    zipf.writestr(f"data_{timestamp}.csv", csv_result.data)
                
                # Add Excel
                excel_result = self._export_excel(df, f"{filename}_excel")
                if excel_result.success:
                    zipf.writestr(f"data_{timestamp}.xlsx", excel_result.data)
                
                # Add JSON
                json_result = self._export_json(df, f"{filename}_json")
                if json_result.success:
                    zipf.writestr(f"data_{timestamp}.json", json_result.data)
                
                # Add summary
                summary = self.export_summary(df.to_dict('records'))
                summary_json = json.dumps(summary, indent=2, default=str)
                zipf.writestr(f"summary_{timestamp}.json", summary_json)
            
            zip_buffer.seek(0)
            zip_data = zip_buffer.getvalue()
            file_size = len(zip_data) / 1024
            
            return ExportResult(
                success=True,
                message=f"Multi-format export successful ({len(zipf.namelist())} files)",
                data=zip_data,
                filename=f"{filename}_multi.zip",
                format="multi",
                row_count=len(df),
                file_size_kb=file_size
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Multi-format export failed: {str(e)}"
            )
    
    def export_summary(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics for export."""
        if not assessments:
            return {
                "total_assessments": 0,
                "average_footprint": 0,
                "average_eco_score": 0,
                "best_eco_score": 0,
                "worst_eco_score": 0,
                "total_footprint": 0,
                "start_date": None,
                "end_date": None,
                "date_range_days": 0,
                "unique_users": 0,
                "transport_modes": {},
                "diet_types": {},
                "avg_distance": 0,
                "avg_electricity": 0,
                "avg_flights": 0,
                "carbon_ranking": "N/A",
                "eco_ranking": "N/A",
                "percentile_25": 0,
                "percentile_50": 0,
                "percentile_75": 0,
                "standard_deviation": 0,
                "variance": 0,
                "range": 0,
                "median": 0,
                "mode": 0
            }
        
        # Extract values
        footprints = [a.get("footprint", 0) for a in assessments if a.get("footprint") is not None]
        eco_scores = [a.get("eco_score", 0) for a in assessments if a.get("eco_score") is not None]
        distances = [a.get("distance", 0) for a in assessments if a.get("distance") is not None]
        electricity = [a.get("electricity", 0) for a in assessments if a.get("electricity") is not None]
        flights = [a.get("flights", 0) for a in assessments if a.get("flights") is not None]
        dates = [a.get("date") for a in assessments if a.get("date")]
        
        # User IDs
        user_ids = [a.get("user_id") for a in assessments if a.get("user_id")]
        unique_users = len(set(user_ids)) if user_ids else 0
        
        # Transport modes
        transport_modes = {}
        for a in assessments:
            mode = a.get("transport", a.get("transport_mode", "unknown"))
            transport_modes[mode] = transport_modes.get(mode, 0) + 1
        
        # Diet types
        diet_types = {}
        for a in assessments:
            diet = a.get("diet", a.get("diet_type", "unknown"))
            diet_types[diet] = diet_types.get(diet, 0) + 1
        
        # Statistical calculations
        footprints_sorted = sorted(footprints)
        eco_scores_sorted = sorted(eco_scores)
        
        def percentile(data, p):
            if not data:
                return 0
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]
        
        def calculate_stats(values):
            if not values:
                return {"mean": 0, "median": 0, "mode": 0, "std": 0, "variance": 0, 
                        "min": 0, "max": 0, "range": 0}
            
            import statistics
            return {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "mode": statistics.mode(values) if len(values) > 1 else values[0],
                "std": statistics.stdev(values) if len(values) > 1 else 0,
                "variance": statistics.variance(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values)
            }
        
        footprint_stats = calculate_stats(footprints)
        eco_stats = calculate_stats(eco_scores)
        
        # Carbon ranking
        avg_footprint = footprint_stats["mean"]
        if avg_footprint < 100:
            carbon_ranking = "Low Carbon"
        elif avg_footprint < 300:
            carbon_ranking = "Moderate Carbon"
        elif avg_footprint < 500:
            carbon_ranking = "High Carbon"
        else:
            carbon_ranking = "Very High Carbon"
        
        # Eco ranking
        avg_eco_score = eco_stats["mean"]
        if avg_eco_score >= 80:
            eco_ranking = "Excellent"
        elif avg_eco_score >= 60:
            eco_ranking = "Good"
        elif avg_eco_score >= 40:
            eco_ranking = "Fair"
        else:
            eco_ranking = "Needs Improvement"
        
        return {
            "total_assessments": len(assessments),
            "average_footprint": round(avg_footprint, 2),
            "average_eco_score": round(avg_eco_score, 2),
            "best_eco_score": max(eco_scores) if eco_scores else 0,
            "worst_eco_score": min(eco_scores) if eco_scores else 0,
            "total_footprint": sum(footprints) if footprints else 0,
            "start_date": min(dates) if dates else None,
            "end_date": max(dates) if dates else None,
            "date_range_days": (max(dates) - min(dates)).days if dates and len(dates) > 1 else 0,
            "unique_users": unique_users,
            "transport_modes": transport_modes,
            "diet_types": diet_types,
            "avg_distance": round(sum(distances) / len(distances), 2) if distances else 0,
            "avg_electricity": round(sum(electricity) / len(electricity), 2) if electricity else 0,
            "avg_flights": round(sum(flights) / len(flights), 2) if flights else 0,
            "carbon_ranking": carbon_ranking,
            "eco_ranking": eco_ranking,
            "percentile_25": percentile(footprints_sorted, 25),
            "percentile_50": percentile(footprints_sorted, 50),
            "percentile_75": percentile(footprints_sorted, 75),
            "standard_deviation": footprint_stats["std"],
            "variance": footprint_stats["variance"],
            "range": footprint_stats["range"],
            "median": footprint_stats["median"],
            "mode": footprint_stats["mode"],
            "eco_percentile_25": percentile(eco_scores_sorted, 25),
            "eco_percentile_50": percentile(eco_scores_sorted, 50),
            "eco_percentile_75": percentile(eco_scores_sorted, 75),
            "eco_std": eco_stats["std"],
            "eco_variance": eco_stats["variance"],
            "eco_range": eco_stats["range"],
            "eco_median": eco_stats["median"],
            "eco_mode": eco_stats["mode"]
        }
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """Get export history."""
        return self._export_history
    
    def clear_cache(self) -> None:
        """Clear export cache."""
        self._cache.clear()
        
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return ["csv", "excel", "json", "html", "markdown", "parquet", "feather", "pickle", "tsv", "multi"]
    
    def get_format_info(self, format_name: str) -> Dict[str, Any]:
        """Get information about a specific format."""
        format_info = {
            "csv": {
                "name": "CSV",
                "extension": ".csv",
                "mime_type": "text/csv",
                "description": "Comma-separated values, widely compatible",
                "size_efficiency": "medium",
                "human_readable": True
            },
            "excel": {
                "name": "Excel",
                "extension": ".xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "description": "Microsoft Excel format with formatting",
                "size_efficiency": "medium",
                "human_readable": True
            },
            "json": {
                "name": "JSON",
                "extension": ".json",
                "mime_type": "application/json",
                "description": "JavaScript Object Notation, structured data",
                "size_efficiency": "medium",
                "human_readable": True
            },
            "html": {
                "name": "HTML",
                "extension": ".html",
                "mime_type": "text/html",
                "description": "Web page with styled table",
                "size_efficiency": "large",
                "human_readable": True
            },
            "markdown": {
                "name": "Markdown",
                "extension": ".md",
                "mime_type": "text/markdown",
                "description": "Markdown table format",
                "size_efficiency": "small",
                "human_readable": True
            },
            "parquet": {
                "name": "Parquet",
                "extension": ".parquet",
                "mime_type": "application/octet-stream",
                "description": "Columnar storage, efficient for large datasets",
                "size_efficiency": "very_small",
                "human_readable": False
            },
            "feather": {
                "name": "Feather",
                "extension": ".feather",
                "mime_type": "application/octet-stream",
                "description": "Fast binary format for DataFrames",
                "size_efficiency": "very_small",
                "human_readable": False
            },
            "pickle": {
                "name": "Pickle",
                "extension": ".pkl",
                "mime_type": "application/octet-stream",
                "description": "Python pickle format",
                "size_efficiency": "small",
                "human_readable": False
            }
        }
        return format_info.get(format_name, {})


# Global export manager instance
_export_manager: Optional[ExportManager] = None


def get_export_manager() -> ExportManager:
    """Get global export manager instance."""
    global _export_manager
    if _export_manager is None:
        _export_manager = ExportManager()
    return _export_manager


def export_assessments(
    assessments: List[Dict[str, Any]],
    format: str = "csv",
    config: Optional[ExportConfig] = None
) -> ExportResult:
    """
    Convenience function to export assessments.
    
    Args:
        assessments: List of assessment dictionaries
        format: Export format ('csv', 'excel', 'json', 'html', 'markdown', 'parquet', 'feather', 'pickle', 'tsv', 'multi')
        config: Export configuration
    
    Returns:
        ExportResult object
    """
    manager = get_export_manager()
    return manager.export_assessments(assessments, format, config)


def export_summary(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to get summary statistics.
    
    Args:
        assessments: List of assessment dictionaries
    
    Returns:
        Summary statistics dictionary
    """
    manager = get_export_manager()
    return manager.export_summary(assessments)


def get_supported_formats() -> List[str]:
    """Get list of supported export formats."""
    manager = get_export_manager()
    return manager.get_supported_formats()