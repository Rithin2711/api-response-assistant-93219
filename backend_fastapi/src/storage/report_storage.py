"""
Validation report storage implementation.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from models.report import ValidationReport, ReportStatus, ReportType
from storage.base import BaseStorage


class ReportStorage(BaseStorage[ValidationReport]):
    """File-based storage for validation reports."""
    
    def __init__(self, storage_dir: str = "data/reports"):
        """Initialize report storage."""
        super().__init__(storage_dir, ValidationReport)
        self.exports_dir = self.storage_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)
    
    def _update_index_entry(self, entry: Dict[str, Any], item: ValidationReport) -> None:
        """Update index entry with report-specific fields."""
        entry.update({
            "title": item.title,
            "request_id": str(item.request_id),
            "response_id": str(item.response_id),
            "report_type": item.report_type.value,
            "status": item.status.value,
            "overall_score": item.summary.overall_score,
            "total_issues": item.summary.total_issues,
            "llm_provider": item.llm_provider,
        })
    
    # PUBLIC_INTERFACE
    def get_by_request(self, request_id: UUID) -> List[ValidationReport]:
        """
        Get reports by request ID.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Associated reports
        """
        return self.search({"request_id": str(request_id)})
    
    # PUBLIC_INTERFACE
    def get_by_response(self, response_id: UUID) -> Optional[ValidationReport]:
        """
        Get report by response ID.
        
        Args:
            response_id: Response identifier
            
        Returns:
            Associated report if found
        """
        reports = self.search({"response_id": str(response_id)})
        return reports[0] if reports else None
    
    # PUBLIC_INTERFACE
    def search_by_score_range(self, min_score: float, max_score: float) -> List[ValidationReport]:
        """
        Search reports by score range.
        
        Args:
            min_score: Minimum score (0.0-1.0)
            max_score: Maximum score (0.0-1.0)
            
        Returns:
            Reports within score range
        """
        reports = self.list_all()
        return [
            report for report in reports
            if min_score <= report.summary.overall_score <= max_score
        ]
    
    # PUBLIC_INTERFACE
    def get_failed_validations(self) -> List[ValidationReport]:
        """
        Get reports with validation failures.
        
        Returns:
            Reports with critical or error issues
        """
        reports = self.list_all()
        return [
            report for report in reports
            if report.summary.critical_count > 0 or report.summary.error_count > 0
        ]
    
    # PUBLIC_INTERFACE
    def update_status(self, report_id: UUID, status: ReportStatus,
                     file_path: Optional[str] = None,
                     error_message: Optional[str] = None) -> Optional[ValidationReport]:
        """
        Update report status.
        
        Args:
            report_id: Report identifier
            status: New status
            file_path: Generated file path (for completed reports)
            error_message: Error message (for failed reports)
            
        Returns:
            Updated report if found
        """
        report = self.get(report_id)
        if not report:
            return None
        
        report.status = status
        report.updated_at = datetime.utcnow()
        
        if status == ReportStatus.COMPLETED:
            report.generated_at = datetime.utcnow()
            if file_path:
                report.file_path = file_path
                # Calculate file size if file exists
                file_obj = Path(file_path)
                if file_obj.exists():
                    report.file_size = file_obj.stat().st_size
        elif status == ReportStatus.FAILED and error_message:
            report.error_message = error_message
        
        return self.update(report)
    
    # PUBLIC_INTERFACE
    def get_export_path(self, report_id: UUID, format: ReportType) -> Path:
        """
        Get export file path for a report.
        
        Args:
            report_id: Report identifier
            format: Export format
            
        Returns:
            Export file path
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{str(report_id)[:8]}_{timestamp}.{format.value}"
        return self.exports_dir / filename
    
    # PUBLIC_INTERFACE
    def cleanup_old_exports(self, days: int = 30) -> int:
        """
        Clean up old export files.
        
        Args:
            days: Number of days to keep files
            
        Returns:
            Number of files deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        deleted_count = 0
        
        for file_path in self.exports_dir.iterdir():
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass  # Continue with other files
        
        return deleted_count
    
    # PUBLIC_INTERFACE
    def get_report_stats(self) -> Dict[str, Any]:
        """
        Get report statistics.
        
        Returns:
            Report statistics
        """
        reports = self.list_all()
        if not reports:
            return {"total_reports": 0}
        
        scores = [r.summary.overall_score for r in reports]
        total_issues = sum(r.summary.total_issues for r in reports)
        
        status_counts = {}
        for report in reports:
            status = report.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_reports": len(reports),
            "avg_score": sum(scores) / len(scores),
            "total_issues_found": total_issues,
            "reports_with_errors": len([r for r in reports if r.summary.error_count > 0]),
            "reports_with_warnings": len([r for r in reports if r.summary.warning_count > 0]),
            "by_status": status_counts,
        }
