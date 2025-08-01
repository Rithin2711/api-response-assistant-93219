"""
Validation report models for response analysis and reporting.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(str, Enum):
    """Report output formats."""
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Individual validation issue."""
    
    level: ValidationLevel = Field(..., description="Issue severity level")
    category: str = Field(..., description="Issue category")
    message: str = Field(..., description="Issue description")
    field_path: Optional[str] = Field(None, description="JSON path to problematic field")
    expected_value: Optional[Any] = Field(None, description="Expected value")
    actual_value: Optional[Any] = Field(None, description="Actual value")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    
    class Config:
        schema_extra = {
            "example": {
                "level": "error",
                "category": "schema_validation",
                "message": "Required field 'email' is missing",
                "field_path": "$.email",
                "expected_value": "string",
                "actual_value": None,
                "suggestion": "Add email field to the response"
            }
        }


class ValidationSummary(BaseModel):
    """Summary of validation results."""
    
    total_issues: int = Field(..., ge=0, description="Total number of issues")
    critical_count: int = Field(..., ge=0, description="Number of critical issues")
    error_count: int = Field(..., ge=0, description="Number of error issues")
    warning_count: int = Field(..., ge=0, description="Number of warning issues")
    info_count: int = Field(..., ge=0, description="Number of info issues")
    
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall validation score (0-1)")
    compliance_percentage: float = Field(..., ge=0.0, le=100.0, description="Compliance percentage")
    
    class Config:
        schema_extra = {
            "example": {
                "total_issues": 5,
                "critical_count": 0,
                "error_count": 2,
                "warning_count": 2,
                "info_count": 1,
                "overall_score": 0.75,
                "compliance_percentage": 75.0
            }
        }


class ValidationReport(BaseModel):
    """Complete validation report for mock responses."""
    
    id: UUID = Field(default_factory=uuid4, description="Report identifier")
    request_id: UUID = Field(..., description="Associated mock request ID")
    response_id: UUID = Field(..., description="Associated mock response ID")
    
    # Report metadata
    title: str = Field(..., description="Report title")
    description: Optional[str] = Field(None, description="Report description")
    report_type: ReportType = Field(default=ReportType.JSON, description="Report format")
    status: ReportStatus = Field(default=ReportStatus.PENDING, description="Generation status")
    
    # Validation results
    summary: ValidationSummary = Field(..., description="Validation summary")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Detailed issues")
    
    # Context information
    validated_response: Dict[str, Any] = Field(..., description="Response that was validated")
    reference_schema: Optional[Dict[str, Any]] = Field(None, description="Reference schema used")
    validation_rules: List[str] = Field(default_factory=list, description="Applied validation rules")
    
    # LLM analysis
    llm_analysis: Optional[str] = Field(None, description="LLM-generated analysis")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    
    # Metrics
    validation_time_ms: int = Field(..., ge=0, description="Validation time in milliseconds")
    llm_provider: str = Field(..., description="LLM provider used for validation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Validation confidence")
    
    # File information
    file_path: Optional[str] = Field(None, description="Generated report file path")
    file_size: Optional[int] = Field(None, ge=0, description="Report file size in bytes")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    generated_at: Optional[datetime] = Field(None, description="Generation completion timestamp")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

    @validator('issues')
    def validate_issue_counts(cls, v, values):
        """Ensure issue counts match the summary."""
        if 'summary' in values:
            summary = values['summary']
            actual_counts = {
                ValidationLevel.CRITICAL: 0,
                ValidationLevel.ERROR: 0,
                ValidationLevel.WARNING: 0,
                ValidationLevel.INFO: 0
            }
            
            for issue in v:
                if issue.level in actual_counts:
                    actual_counts[issue.level] += 1
            
            # Update summary if counts don't match
            if (actual_counts[ValidationLevel.CRITICAL] != summary.critical_count or
                actual_counts[ValidationLevel.ERROR] != summary.error_count or
                actual_counts[ValidationLevel.WARNING] != summary.warning_count or
                actual_counts[ValidationLevel.INFO] != summary.info_count):
                
                summary.critical_count = actual_counts[ValidationLevel.CRITICAL]
                summary.error_count = actual_counts[ValidationLevel.ERROR]
                summary.warning_count = actual_counts[ValidationLevel.WARNING]
                summary.info_count = actual_counts[ValidationLevel.INFO]
                summary.total_issues = sum(actual_counts.values())
        
        return v


class ReportExportRequest(BaseModel):
    """Request model for report export."""
    
    report_id: UUID = Field(..., description="Report to export")
    format: ReportType = Field(..., description="Export format")
    include_raw_data: bool = Field(default=False, description="Include raw response data")
    include_suggestions: bool = Field(default=True, description="Include improvement suggestions")
    
    class Config:
        schema_extra = {
            "example": {
                "report_id": "123e4567-e89b-12d3-a456-426614174000",
                "format": "pdf",
                "include_raw_data": True,
                "include_suggestions": True
            }
        }
