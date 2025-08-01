"""
Validation API endpoints for response analysis and validation.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from models.report import ValidationReport
from services.validator_service import ValidatorService
from services.mock_service import MockService
from services.vector_service import VectorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["Validation"])
validator_service = ValidatorService()
mock_service = MockService()
vector_service = VectorService()


@router.post("/validate/{response_id}",
             response_model=ValidationReport,
             status_code=status.HTTP_201_CREATED,
             summary="Validate mock response",
             description="Validate a generated mock response against documentation")
async def validate_response(
    response_id: UUID,
    llm_provider: str = "mock"
):
    """
    Validate a generated mock response against documentation.
    
    Analyzes the response for compliance with API documentation,
    schema validation, data type correctness, and best practices.
    """
    try:
        # Get the mock response
        mock_response = mock_service.get_mock_response(response_id)
        if not mock_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mock response not found"
            )
        
        # Get context for validation
        context_chunks = vector_service.get_context_for_request(
            "VALIDATION", f"/validate/{response_id}", 
            mock_response.context_documents
        )
        
        # Validate response
        report = validator_service.validate_response(
            mock_response, context_chunks, llm_provider
        )
        
        logger.info(f"Validation completed for response {response_id}")
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed for response {response_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/reports",
            response_model=List[ValidationReport],
            summary="List validation reports",
            description="Get list of validation reports with optional filtering")
async def list_validation_reports(request_id: Optional[UUID] = None):
    """
    List validation reports with optional filtering by request ID.
    """
    try:
        reports = validator_service.list_reports(request_id=request_id)
        return reports
        
    except Exception as e:
        logger.error(f"Failed to list validation reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.get("/reports/{report_id}",
            response_model=ValidationReport,
            summary="Get validation report",
            description="Retrieve a specific validation report")
async def get_validation_report(report_id: UUID):
    """
    Get detailed validation report by ID.
    """
    report = validator_service.get_validation_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation report not found"
        )
    
    return report


# Convenience endpoint for request validation
@router.post("/validate-request/{request_id}",
             response_model=ValidationReport,
             summary="Validate request response",
             description="Validate the response for a specific mock request")
async def validate_request_response(
    request_id: UUID,
    llm_provider: str = "mock"
):
    """
    Validate the response for a specific mock request.
    
    This is a convenience endpoint that finds the response for a request
    and validates it in one step.
    """
    try:
        # Get the mock response for this request
        mock_response = mock_service.get_response_by_request(request_id)
        if not mock_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No response found for this request"
            )
        
        # Get context for validation
        context_chunks = vector_service.get_context_for_request(
            "VALIDATION", f"/validate-request/{request_id}", 
            mock_response.context_documents
        )
        
        # Validate response
        report = validator_service.validate_response(
            mock_response, context_chunks, llm_provider
        )
        
        logger.info(f"Validation completed for request {request_id}")
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed for request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )
