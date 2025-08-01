"""
Report service for generating and exporting validation reports.
Supports PDF, Excel, JSON, and HTML formats.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from models.report import ValidationReport, ReportType, ReportExportRequest, ReportStatus
from storage.report_storage import ReportStorage

logger = logging.getLogger(__name__)


class ReportService:
    """Service for report generation and export."""
    
    def __init__(self, storage_dir: str = "data/reports"):
        """
        Initialize report service.
        
        Args:
            storage_dir: Report storage directory
        """
        self.report_storage = ReportStorage(storage_dir)
    
    # PUBLIC_INTERFACE
    def export_report(self, export_request: ReportExportRequest) -> Optional[str]:
        """
        Export validation report to specified format.
        
        Args:
            export_request: Export configuration
            
        Returns:
            File path of exported report if successful
        """
        try:
            # Get report
            report = self.report_storage.get(export_request.report_id)
            if not report:
                logger.error(f"Report {export_request.report_id} not found")
                return None
            
            # Generate export file path
            export_path = self.report_storage.get_export_path(
                export_request.report_id, export_request.format
            )
            
            # Export based on format
            success = False
            if export_request.format == ReportType.JSON:
                success = self._export_json(report, export_path, export_request)
            elif export_request.format == ReportType.HTML:
                success = self._export_html(report, export_path, export_request)
            elif export_request.format == ReportType.PDF:
                success = self._export_pdf(report, export_path, export_request)
            elif export_request.format == ReportType.EXCEL:
                success = self._export_excel(report, export_path, export_request)
            
            if success:
                # Update report with export file info
                self.report_storage.update_status(
                    report.id, ReportStatus.COMPLETED, str(export_path)
                )
                logger.info(f"Report exported to {export_path}")
                return str(export_path)
            else:
                logger.error(f"Failed to export report {export_request.report_id}")
                return None
                
        except Exception as e:
            logger.error(f"Report export failed: {str(e)}")
            return None
    
    def _export_json(self, report: ValidationReport, export_path: Path,
                    export_request: ReportExportRequest) -> bool:
        """Export report as JSON."""
        try:
            # Prepare export data
            export_data = {
                "report_metadata": {
                    "id": str(report.id),
                    "title": report.title,
                    "description": report.description,
                    "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                    "validation_time_ms": report.validation_time_ms,
                    "llm_provider": report.llm_provider,
                    "confidence_score": report.confidence_score,
                },
                "validation_summary": {
                    "overall_score": report.summary.overall_score,
                    "compliance_percentage": report.summary.compliance_percentage,
                    "total_issues": report.summary.total_issues,
                    "critical_count": report.summary.critical_count,
                    "error_count": report.summary.error_count,
                    "warning_count": report.summary.warning_count,
                    "info_count": report.summary.info_count,
                },
                "issues": [
                    {
                        "level": issue.level.value,
                        "category": issue.category,
                        "message": issue.message,
                        "field_path": issue.field_path,
                        "expected_value": issue.expected_value,
                        "actual_value": issue.actual_value,
                        "suggestion": issue.suggestion,
                    }
                    for issue in report.issues
                ],
                "improvement_suggestions": report.improvement_suggestions,
            }
            
            # Include raw data if requested
            if export_request.include_raw_data:
                export_data["raw_response"] = report.validated_response
                export_data["reference_schema"] = report.reference_schema
                export_data["validation_rules"] = report.validation_rules
            
            # Include LLM analysis if available and requested
            if export_request.include_suggestions and report.llm_analysis:
                export_data["llm_analysis"] = report.llm_analysis
            
            # Write JSON file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            return False
    
    def _export_html(self, report: ValidationReport, export_path: Path,
                    export_request: ReportExportRequest) -> bool:
        """Export report as HTML."""
        try:
            # Generate HTML content
            html_content = self._generate_html_report(report, export_request)
            
            # Write HTML file
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
            
        except Exception as e:
            logger.error(f"HTML export failed: {str(e)}")
            return False
    
    def _export_pdf(self, report: ValidationReport, export_path: Path,
                   export_request: ReportExportRequest) -> bool:
        """Export report as PDF (placeholder implementation)."""
        try:
            # For now, export as HTML and note that PDF conversion would need additional library
            html_path = export_path.with_suffix('.html')
            html_success = self._export_html(report, html_path, export_request)
            
            if html_success:
                # Create a simple text-based PDF placeholder
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(f"PDF Export Placeholder - Report {report.id}\n")
                    f.write(f"Title: {report.title}\n")
                    f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
                    f.write(f"Overall Score: {report.summary.overall_score:.2f}\n")
                    f.write(f"Total Issues: {report.summary.total_issues}\n\n")
                    f.write("Issues:\n")
                    for issue in report.issues:
                        f.write(f"- [{issue.level.value}] {issue.message}\n")
                    f.write(f"\nHTML version available at: {html_path}\n")
                    f.write("Note: Full PDF generation requires additional libraries.\n")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}")
            return False
    
    def _export_excel(self, report: ValidationReport, export_path: Path,
                     export_request: ReportExportRequest) -> bool:
        """Export report as Excel (placeholder implementation)."""
        try:
            # Create CSV-like format for now (Excel would need openpyxl or xlswriter)
            csv_content = []
            csv_content.append("Level,Category,Message,Field Path,Expected,Actual,Suggestion")
            
            for issue in report.issues:
                row = [
                    issue.level.value,
                    issue.category,
                    f'"{issue.message}"',
                    issue.field_path or "",
                    f'"{issue.expected_value}"' if issue.expected_value else "",
                    f'"{issue.actual_value}"' if issue.actual_value else "",
                    f'"{issue.suggestion}"' if issue.suggestion else "",
                ]
                csv_content.append(",".join(row))
            
            # Write CSV file (with .xlsx extension for placeholder)
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(csv_content))
                f.write(f"\n\n# Report Summary\n")
                f.write(f"# Overall Score: {report.summary.overall_score:.2f}\n")
                f.write(f"# Total Issues: {report.summary.total_issues}\n")
                f.write("# Note: Full Excel export requires openpyxl library\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Excel export failed: {str(e)}")
            return False
    
    def _generate_html_report(self, report: ValidationReport,
                            export_request: ReportExportRequest) -> str:
        """Generate HTML report content."""
        # Issue level colors
        level_colors = {
            "critical": "#dc2626",
            "error": "#ea580c", 
            "warning": "#d97706",
            "info": "#0891b2"
        }
        
        # Generate issues HTML
        issues_html = ""
        for issue in report.issues:
            color = level_colors.get(issue.level.value, "#6b7280")
            issues_html += f"""
            <div class="issue" style="border-left: 4px solid {color}; padding: 12px; margin: 8px 0; background: #f9fafb;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase;">
                        {issue.level.value}
                    </span>
                    <span style="margin-left: 12px; font-weight: 600; color: #374151;">
                        {issue.category}
                    </span>
                </div>
                <p style="margin: 4px 0; color: #1f2937;">{issue.message}</p>
                {f'<p style="margin: 4px 0; font-family: monospace; color: #6b7280; font-size: 14px;">Path: {issue.field_path}</p>' if issue.field_path else ''}
                {f'<p style="margin: 4px 0; color: #059669;"><strong>Expected:</strong> {issue.expected_value}</p>' if issue.expected_value else ''}
                {f'<p style="margin: 4px 0; color: #dc2626;"><strong>Actual:</strong> {issue.actual_value}</p>' if issue.actual_value else ''}
                {f'<p style="margin: 8px 0; padding: 8px; background: #ecfdf5; border-radius: 4px; color: #065f46;"><strong>Suggestion:</strong> {issue.suggestion}</p>' if issue.suggestion else ''}
            </div>
            """
        
        # Score color
        score = report.summary.overall_score
        if score >= 0.8:
            score_color = "#059669"
        elif score >= 0.6:
            score_color = "#d97706"
        else:
            score_color = "#dc2626"
        
        # Generate suggestions HTML
        suggestions_html = ""
        if export_request.include_suggestions and report.improvement_suggestions:
            suggestions_html = """
            <div style="margin-top: 24px; padding: 16px; background: #eff6ff; border-radius: 8px;">
                <h3 style="color: #1e40af; margin: 0 0 12px 0;">💡 Improvement Suggestions</h3>
                <ul style="margin: 0; padding-left: 20px;">
            """
            for suggestion in report.improvement_suggestions:
                suggestions_html += f"<li style='margin: 4px 0; color: #1f2937;'>{suggestion}</li>"
            suggestions_html += "</ul></div>"
        
        # Main HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report.title}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #1f2937; max-width: 1000px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 100%); color: white; padding: 24px; border-radius: 8px; margin-bottom: 24px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }}
                .metric {{ background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; margin-bottom: 4px; }}
                .metric-label {{ font-size: 14px; color: #6b7280; }}
                .section {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0 0 8px 0;">{report.title}</h1>
                <p style="margin: 0; opacity: 0.9;">{report.description or 'API Response Validation Report'}</p>
                <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.8;">
                    Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if report.generated_at else 'N/A'} | 
                    Validation Time: {report.validation_time_ms}ms | 
                    Provider: {report.llm_provider}
                </p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <div class="metric-value" style="color: {score_color};">{score:.1%}</div>
                    <div class="metric-label">Overall Score</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #dc2626;">{report.summary.critical_count}</div>
                    <div class="metric-label">Critical</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #ea580c;">{report.summary.error_count}</div>
                    <div class="metric-label">Errors</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #d97706;">{report.summary.warning_count}</div>
                    <div class="metric-label">Warnings</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #0891b2;">{report.summary.info_count}</div>
                    <div class="metric-label">Info</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{report.summary.total_issues}</div>
                    <div class="metric-label">Total Issues</div>
                </div>
            </div>
            
            <div class="section">
                <h2 style="margin: 0 0 16px 0; color: #1f2937;">🔍 Validation Issues</h2>
                {issues_html if issues_html.strip() else '<p style="color: #059669; font-weight: 600;">✅ No issues found! Your API response looks great.</p>'}
            </div>
            
            {suggestions_html}
            
            <div style="margin-top: 32px; padding: 16px; background: #f9fafb; border-radius: 8px; font-size: 14px; color: #6b7280; text-align: center;">
                Generated by IntelliMock API Response Validator
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    # PUBLIC_INTERFACE
    def get_report(self, report_id: UUID) -> Optional[ValidationReport]:
        """
        Get validation report by ID.
        
        Args:
            report_id: Report identifier
            
        Returns:
            Validation report if found
        """
        return self.report_storage.get(report_id)
    
    # PUBLIC_INTERFACE
    def list_reports(self, request_id: Optional[UUID] = None) -> list:
        """
        List validation reports.
        
        Args:
            request_id: Filter by request ID
            
        Returns:
            List of validation reports
        """
        if request_id:
            return self.report_storage.get_by_request(request_id)
        else:
            return self.report_storage.list_all()
    
    # PUBLIC_INTERFACE
    def delete_report(self, report_id: UUID) -> bool:
        """
        Delete validation report.
        
        Args:
            report_id: Report identifier
            
        Returns:
            True if deleted successfully
        """
        return self.report_storage.delete(report_id)
    
    # PUBLIC_INTERFACE
    def cleanup_old_reports(self, days: int = 30) -> int:
        """
        Clean up old reports and export files.
        
        Args:
            days: Number of days to keep reports
            
        Returns:
            Number of items cleaned up
        """
        return self.report_storage.cleanup_old_exports(days)
