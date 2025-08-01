"""
Report management and export API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from models.report import ValidationReport, ReportExportRequest, ReportType
from services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])
report_service = ReportService()


@router.get("/",
            response_model=List[ValidationReport],
            summary="List reports",
            description="Get list of validation reports")
async def list_reports(request_id: Optional[UUID] = None):
    """
    List all validation reports with optional filtering by request ID.
    """
    try:
        reports = report_service.list_reports(request_id=request_id)
        return reports
        
    except Exception as e:
        logger.error(f"Failed to list reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.get("/{report_id}",
            response_model=ValidationReport,
            summary="Get report",
            description="Retrieve a specific validation report")
async def get_report(report_id: UUID):
    """
    Get detailed validation report by ID.
    """
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    return report


@router.post("/{report_id}/export",
             summary="Export report",
             description="Export validation report in specified format")
async def export_report(report_id: UUID, export_request: ReportExportRequest):
    """
    Export validation report in the specified format.
    
    Supports JSON, HTML, PDF, and Excel formats.
    Returns the file path for download.
    """
    try:
        # Validate that report exists
        report = report_service.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Ensure export request has correct report ID
        export_request.report_id = report_id
        
        # Export report
        file_path = report_service.export_report(export_request)
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export report"
            )
        
        logger.info(f"Report exported: {report_id} -> {file_path}")
        return {"file_path": file_path, "message": "Report exported successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/{report_id}/download/{format}",
            summary="Download report",
            description="Download exported report file")
async def download_report(report_id: UUID, format: ReportType):
    """
    Download exported report file.
    
    If the report hasn't been exported in the requested format,
    it will be exported automatically.
    """
    try:
        # Check if report exists
        report = report_service.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Create export request
        export_request = ReportExportRequest(
            report_id=report_id,
            format=format,
            include_raw_data=True,
            include_suggestions=True
        )
        
        # Export if needed
        file_path = report_service.export_report(export_request)
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate report file"
            )
        
        # Determine filename and media type
        filename = f"validation_report_{str(report_id)[:8]}.{format.value}"
        
        media_type_map = {
            ReportType.JSON: "application/json",
            ReportType.HTML: "text/html",
            ReportType.PDF: "application/pdf",
            ReportType.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        media_type = media_type_map.get(format, "application/octet-stream")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report download failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )


@router.delete("/{report_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete report",
               description="Delete a validation report")
async def delete_report(report_id: UUID):
    """
    Delete a validation report and its associated files.
    """
    success = report_service.delete_report(report_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    logger.info(f"Report deleted: {report_id}")


@router.post("/cleanup",
             summary="Cleanup old reports",
             description="Clean up old reports and export files")
async def cleanup_old_reports(days: int = 30):
    """
    Clean up old reports and export files older than specified days.
    """
    try:
        if days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be at least 1"
            )
        
        cleaned_count = report_service.cleanup_old_reports(days)
        
        logger.info(f"Cleaned up {cleaned_count} old report files")
        return {
            "message": f"Cleaned up {cleaned_count} old files",
            "days": days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )
