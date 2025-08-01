"""
Validator service for analyzing and validating API responses.
Uses LLM analysis and rule-based validation.
"""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from models.mock_request import MockResponse
from models.report import (
    ValidationReport, ValidationIssue, ValidationSummary, 
    ValidationLevel, ReportStatus
)
from storage.report_storage import ReportStorage
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ValidatorService:
    """Service for validating API responses against documentation."""
    
    def __init__(self, storage_dir: str = "data/reports"):
        """
        Initialize validator service.
        
        Args:
            storage_dir: Report storage directory
        """
        self.report_storage = ReportStorage(storage_dir)
        self.llm_service = LLMService()
    
    # PUBLIC_INTERFACE
    def validate_response(self, response: MockResponse, 
                         context_chunks: List[str],
                         llm_provider: str = "mock") -> ValidationReport:
        """
        Validate a mock response and generate validation report.
        
        Args:
            response: Mock response to validate
            context_chunks: Documentation context
            llm_provider: LLM provider for validation
            
        Returns:
            Validation report
        """
        start_time = datetime.utcnow()
        
        try:
            # Create initial report
            report = ValidationReport(
                request_id=response.request_id,
                response_id=response.request_id,  # Using request_id as response doesn't have separate ID
                title=f"Validation Report - {response.status_code}",
                description=f"Validation of response for request {response.request_id}",
                validated_response=response.body or {},
                validation_rules=self._get_validation_rules(),
                llm_provider=llm_provider,
                summary=ValidationSummary(
                    total_issues=0,
                    critical_count=0,
                    error_count=0,
                    warning_count=0,
                    info_count=0,
                    overall_score=1.0,
                    compliance_percentage=100.0
                ),
                validation_time_ms=0,
                confidence_score=0.0,
            )
            
            # Store initial report
            report = self.report_storage.create(report)
            self.report_storage.update_status(report.id, ReportStatus.GENERATING)
            
            # Perform validation
            issues = []
            
            # Rule-based validation
            rule_issues = self._validate_with_rules(response, context_chunks)
            issues.extend(rule_issues)
            
            # LLM-based validation
            llm_issues = self._validate_with_llm(response, context_chunks, llm_provider)
            issues.extend(llm_issues)
            
            # Calculate summary
            summary = self._calculate_summary(issues)
            
            # Update report
            validation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            report.issues = issues
            report.summary = summary
            report.validation_time_ms = validation_time
            report.confidence_score = self._calculate_confidence_score(issues, len(context_chunks))
            report.improvement_suggestions = self._generate_suggestions(issues)
            
            # Update storage
            report = self.report_storage.update(report)
            self.report_storage.update_status(report.id, ReportStatus.COMPLETED)
            
            logger.info(f"Validation completed for response {response.request_id}")
            return report
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            if 'report' in locals():
                error_msg = f"Validation failed: {str(e)}"
                self.report_storage.update_status(report.id, ReportStatus.FAILED, error_message=error_msg)
            raise
    
    def _get_validation_rules(self) -> List[str]:
        """Get list of validation rules applied."""
        return [
            "HTTP status code validation",
            "Response structure validation",
            "Data type validation",
            "Required field validation",
            "Header validation",
            "Content-Type validation",
            "JSON schema compliance",
            "API documentation compliance"
        ]
    
    def _validate_with_rules(self, response: MockResponse, 
                           context_chunks: List[str]) -> List[ValidationIssue]:
        """
        Perform rule-based validation.
        
        Args:
            response: Response to validate
            context_chunks: Documentation context
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # HTTP status code validation
        issues.extend(self._validate_status_code(response))
        
        # Header validation
        issues.extend(self._validate_headers(response))
        
        # Body validation
        if response.body:
            issues.extend(self._validate_body_structure(response.body))
            issues.extend(self._validate_data_types(response.body))
        
        # Context compliance
        issues.extend(self._validate_context_compliance(response, context_chunks))
        
        return issues
    
    def _validate_status_code(self, response: MockResponse) -> List[ValidationIssue]:
        """Validate HTTP status code."""
        issues = []
        
        if not (100 <= response.status_code <= 599):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="status_code",
                message=f"Invalid HTTP status code: {response.status_code}",
                expected_value="100-599",
                actual_value=response.status_code,
                suggestion="Use a valid HTTP status code"
            ))
        elif response.status_code >= 500:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="status_code",
                message=f"Server error status code: {response.status_code}",
                actual_value=response.status_code,
                suggestion="Consider if server error is appropriate for this endpoint"
            ))
        
        return issues
    
    def _validate_headers(self, response: MockResponse) -> List[ValidationIssue]:
        """Validate response headers."""
        issues = []
        
        # Check for Content-Type header
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        if response.body and "content-type" not in headers_lower:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="header",
                message="Missing Content-Type header",
                expected_value="application/json or appropriate MIME type",
                actual_value=None,
                suggestion="Add Content-Type header to response"
            ))
        
        # Validate Content-Type for JSON responses
        content_type = headers_lower.get("content-type", "")
        if response.body and isinstance(response.body, dict):
            if "application/json" not in content_type:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="header",
                    message="Content-Type mismatch for JSON response",
                    expected_value="application/json",
                    actual_value=content_type,
                    suggestion="Set Content-Type to application/json for JSON responses"
                ))
        
        return issues
    
    def _validate_body_structure(self, body: Any) -> List[ValidationIssue]:
        """Validate response body structure."""
        issues = []
        
        if body is None:
            return issues
        
        if isinstance(body, dict):
            # Check for common API response patterns
            if "error" in body and "message" not in body:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="schema",
                    message="Error response missing descriptive message",
                    field_path="$.message",
                    suggestion="Include a descriptive error message"
                ))
            
            # Check for pagination in list responses
            if "data" in body and isinstance(body["data"], list):
                if len(body["data"]) > 10 and "pagination" not in body:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.INFO,
                        category="schema",
                        message="Large data array without pagination info",
                        field_path="$.pagination",
                        suggestion="Consider adding pagination metadata for large datasets"
                    ))
        
        return issues
    
    def _validate_data_types(self, body: Any, path: str = "$") -> List[ValidationIssue]:
        """Validate data types in response body."""
        issues = []
        
        if isinstance(body, dict):
            for key, value in body.items():
                field_path = f"{path}.{key}"
                
                # Recursive validation for nested objects
                if isinstance(value, (dict, list)):
                    issues.extend(self._validate_data_types(value, field_path))
                
                # Common field validations
                if key.endswith("_id") and not isinstance(value, (int, str)):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="data_type",
                        message="ID field should be string or number",
                        field_path=field_path,
                        expected_value="string or number",
                        actual_value=type(value).__name__,
                        suggestion="Use string or number for ID fields"
                    ))
                
                if key.endswith("_at") and isinstance(value, str):
                    # Basic timestamp format check
                    if "T" not in value and ":" not in value:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.WARNING,
                            category="value",
                            message="Timestamp format may not be ISO 8601",
                            field_path=field_path,
                            actual_value=value,
                            suggestion="Use ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)"
                        ))
        
        elif isinstance(body, list):
            for i, item in enumerate(body):
                item_path = f"{path}[{i}]"
                issues.extend(self._validate_data_types(item, item_path))
        
        return issues
    
    def _validate_context_compliance(self, response: MockResponse, 
                                   context_chunks: List[str]) -> List[ValidationIssue]:
        """Validate response compliance with documentation context."""
        issues = []
        
        if not context_chunks:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="schema_validation",
                message="No documentation context available for validation",
                suggestion="Ensure relevant documentation is uploaded and indexed"
            ))
            return issues
        
        # Simple keyword matching for context relevance
        context_text = " ".join(context_chunks).lower()
        
        # Check if response mentions fields documented in context
        response_fields = set()
        if response.body and isinstance(response.body, dict):
            def extract_fields(obj, prefix=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        field_name = f"{prefix}.{key}" if prefix else key
                        response_fields.add(key)
                        if isinstance(value, dict):
                            extract_fields(value, field_name)
            extract_fields(response.body)
        
        # Check for undocumented fields
        for field in response_fields:
            if field not in context_text and len(field) > 2:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="schema",
                    message=f"Field '{field}' not found in documentation",
                    field_path=f"$.{field}",
                    suggestion="Verify if field is documented or should be removed"
                ))
        
        return issues
    
    def _validate_with_llm(self, response: MockResponse, 
                          context_chunks: List[str],
                          llm_provider: str) -> List[ValidationIssue]:
        """
        Perform LLM-based validation.
        
        Args:
            response: Response to validate
            context_chunks: Documentation context
            llm_provider: LLM provider to use
            
        Returns:
            List of validation issues from LLM analysis
        """
        try:
            # Create response data for LLM analysis
            response_data = {
                "status_code": response.status_code,
                "headers": response.headers,
                "body": response.body
            }
            
            # Get LLM validation
            llm_response = self.llm_service.validate_response(
                response_data, context_chunks, llm_provider
            )
            
            if not llm_response:
                return []
            
            # Parse LLM response
            try:
                validation_result = json.loads(llm_response.content)
                issues = []
                
                for issue_data in validation_result.get("issues", []):
                    issue = ValidationIssue(
                        level=ValidationLevel(issue_data.get("level", "info")),
                        category=issue_data.get("category", "general"),
                        message=issue_data.get("message", ""),
                        field_path=issue_data.get("field_path"),
                        expected_value=issue_data.get("expected_value"),
                        actual_value=issue_data.get("actual_value"),
                        suggestion=issue_data.get("suggestion")
                    )
                    issues.append(issue)
                
                return issues
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse LLM validation response: {str(e)}")
                return []
            
        except Exception as e:
            logger.warning(f"LLM validation failed: {str(e)}")
            return []
    
    def _calculate_summary(self, issues: List[ValidationIssue]) -> ValidationSummary:
        """Calculate validation summary from issues."""
        counts = {
            ValidationLevel.CRITICAL: 0,
            ValidationLevel.ERROR: 0,
            ValidationLevel.WARNING: 0,
            ValidationLevel.INFO: 0
        }
        
        for issue in issues:
            if issue.level in counts:
                counts[issue.level] += 1
        
        total_issues = sum(counts.values())
        
        # Calculate overall score (0-1)
        # Critical issues: -0.3, Errors: -0.2, Warnings: -0.1, Info: -0.05
        score_deduction = (
            counts[ValidationLevel.CRITICAL] * 0.3 +
            counts[ValidationLevel.ERROR] * 0.2 +
            counts[ValidationLevel.WARNING] * 0.1 +
            counts[ValidationLevel.INFO] * 0.05
        )
        
        overall_score = max(0.0, 1.0 - score_deduction)
        compliance_percentage = overall_score * 100
        
        return ValidationSummary(
            total_issues=total_issues,
            critical_count=counts[ValidationLevel.CRITICAL],
            error_count=counts[ValidationLevel.ERROR],
            warning_count=counts[ValidationLevel.WARNING],
            info_count=counts[ValidationLevel.INFO],
            overall_score=overall_score,
            compliance_percentage=compliance_percentage
        )
    
    def _calculate_confidence_score(self, issues: List[ValidationIssue], 
                                  context_count: int) -> float:
        """Calculate confidence score for validation."""
        base_confidence = 0.7
        
        # Increase confidence with more context
        context_bonus = min(0.2, context_count * 0.02)
        
        # Decrease confidence with more critical issues
        critical_penalty = len([i for i in issues if i.level == ValidationLevel.CRITICAL]) * 0.1
        
        confidence = base_confidence + context_bonus - critical_penalty
        return max(0.1, min(1.0, confidence))
    
    def _generate_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate improvement suggestions from issues."""
        suggestions = []
        
        # Group issues by category
        categories = {}
        for issue in issues:
            if issue.level in [ValidationLevel.CRITICAL, ValidationLevel.ERROR]:
                category = issue.category
                if category not in categories:
                    categories[category] = []
                categories[category].append(issue)
        
        # Generate category-specific suggestions
        for category, category_issues in categories.items():
            if category == "status_code":
                suggestions.append("Review HTTP status codes and ensure they match the API operation results")
            elif category == "schema":
                suggestions.append("Validate response schema against API documentation and specifications")
            elif category == "data_type":
                suggestions.append("Ensure all fields use appropriate data types as defined in the API schema")
            elif category == "header":
                suggestions.append("Add or correct HTTP headers, especially Content-Type for proper response formatting")
        
        # General suggestions
        if len(issues) > 5:
            suggestions.append("Consider comprehensive API documentation review to address multiple validation issues")
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    # PUBLIC_INTERFACE
    def get_validation_report(self, report_id: UUID) -> Optional[ValidationReport]:
        """
        Get validation report by ID.
        
        Args:
            report_id: Report identifier
            
        Returns:
            Validation report if found
        """
        return self.report_storage.get(report_id)
    
    # PUBLIC_INTERFACE
    def list_reports(self, request_id: Optional[UUID] = None) -> List[ValidationReport]:
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
