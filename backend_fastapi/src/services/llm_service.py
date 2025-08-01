"""
LLM service for integrating with AI providers like Gemini, OpenAI, etc.
Handles request generation, validation, and response processing.
"""

import json
import logging
import time
from typing import List, Optional

from models.llm import LLMProvider, LLMRequest, LLMResponse
from models.mock_request import MockRequest

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM provider integration."""
    
    def __init__(self):
        """Initialize LLM service."""
        self.providers = {
            LLMProvider.MOCK: MockLLMProvider(),
            # Add other providers here when API keys are available
        }
    
    # PUBLIC_INTERFACE
    def generate_mock_response(self, request: MockRequest, 
                             context_chunks: List[str]) -> Optional[LLMResponse]:
        """
        Generate mock API response using LLM.
        
        Args:
            request: Mock request to generate response for
            context_chunks: Relevant documentation context
            
        Returns:
            LLM response if successful
        """
        try:
            # Create LLM request
            prompt = self._build_mock_response_prompt(request, context_chunks)
            
            llm_request = LLMRequest(
                provider=LLMProvider(request.llm_provider),
                model=request.llm_config.get("model", "default"),
                prompt=prompt,
                context=context_chunks,
                temperature=request.llm_config.get("temperature", 0.7),
                max_tokens=request.llm_config.get("max_tokens", 1000),
                user_id=request.user_id,
                session_id=request.session_id,
            )
            
            # Get provider and generate response
            provider = self.providers.get(llm_request.provider)
            if not provider:
                logger.error(f"Provider {llm_request.provider} not available")
                return None
            
            return provider.generate(llm_request)
            
        except Exception as e:
            logger.error(f"Failed to generate mock response: {str(e)}")
            return None
    
    # PUBLIC_INTERFACE
    def validate_response(self, response_data: dict, context_chunks: List[str],
                         provider: str = "mock") -> Optional[LLMResponse]:
        """
        Validate a generated response against documentation.
        
        Args:
            response_data: Response data to validate
            context_chunks: Documentation context
            provider: LLM provider to use
            
        Returns:
            Validation analysis response
        """
        try:
            prompt = self._build_validation_prompt(response_data, context_chunks)
            
            llm_request = LLMRequest(
                provider=LLMProvider(provider),
                model="default",
                prompt=prompt,
                context=context_chunks,
                temperature=0.3,  # Lower temperature for validation
                max_tokens=1500,
            )
            
            provider_instance = self.providers.get(LLMProvider(provider))
            if not provider_instance:
                logger.error(f"Provider {provider} not available")
                return None
            
            return provider_instance.generate(llm_request)
            
        except Exception as e:
            logger.error(f"Failed to validate response: {str(e)}")
            return None
    
    def _build_mock_response_prompt(self, request: MockRequest, 
                                  context_chunks: List[str]) -> str:
        """
        Build prompt for mock response generation.
        
        Args:
            request: Mock request
            context_chunks: Documentation context
            
        Returns:
            Formatted prompt
        """
        context_text = "\n".join(context_chunks) if context_chunks else "No specific documentation available."
        
        prompt = f"""You are an AI assistant that generates realistic API responses based on documentation.

API REQUEST:
Method: {request.method.value}
Path: {request.path}
Headers: {json.dumps(request.headers, indent=2)}
Query Parameters: {json.dumps(request.query_params, indent=2)}
Request Body: {json.dumps(request.body, indent=2) if request.body else "None"}

DOCUMENTATION CONTEXT:
{context_text}

INSTRUCTIONS:
1. Generate a realistic JSON response that matches the API documentation
2. Include appropriate HTTP status code (200, 201, 400, 404, etc.)
3. Include relevant response headers
4. Make the response data consistent with the request and documentation
5. For POST requests, include created resource with ID
6. For GET requests, return appropriate data structure
7. For error cases, include proper error messages

Response format should be:
{{
  "status_code": <HTTP status code>,
  "headers": {{
    "content-type": "application/json",
    ...
  }},
  "body": {{
    <response data>
  }}
}}

Generate the response:"""
        
        return prompt
    
    def _build_validation_prompt(self, response_data: dict, 
                               context_chunks: List[str]) -> str:
        """
        Build prompt for response validation.
        
        Args:
            response_data: Response to validate
            context_chunks: Documentation context
            
        Returns:
            Validation prompt
        """
        context_text = "\n".join(context_chunks) if context_chunks else "No documentation available."
        
        prompt = f"""You are an AI assistant that validates API responses against documentation.

RESPONSE TO VALIDATE:
{json.dumps(response_data, indent=2)}

DOCUMENTATION CONTEXT:
{context_text}

INSTRUCTIONS:
Analyze the response and provide validation feedback including:
1. Schema compliance - does the response match expected structure?
2. Data type validation - are field types correct?
3. Required field validation - are all required fields present?
4. Value validation - are field values reasonable and consistent?
5. HTTP status code appropriateness
6. Header validation

Provide your analysis in this JSON format:
{{
  "overall_score": <0.0-1.0>,
  "issues": [
    {{
      "level": "error|warning|info",
      "category": "schema|data_type|required_field|value|status_code|header",
      "message": "Description of the issue",
      "field_path": "JSON path to problematic field (if applicable)",
      "suggestion": "How to fix the issue"
    }}
  ],
  "summary": "Overall assessment of the response quality and compliance"
}}

Validation analysis:"""
        
        return prompt


class MockLLMProvider:
    """Mock LLM provider for testing and fallback."""
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate mock response.
        
        Args:
            request: LLM request
            
        Returns:
            Mock LLM response
        """
        start_time = time.time()
        
        # Simple mock response generation
        if "validate" in request.prompt.lower():
            content = self._generate_mock_validation(request)
        else:
            content = self._generate_mock_api_response(request)
        
        response_time = int((time.time() - start_time) * 1000)
        
        return LLMResponse(
            request_id=request.id,
            content=content,
            finish_reason="stop",
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(request.prompt.split()) + len(content.split()),
            response_time_ms=response_time,
            provider=request.provider,
            model=request.model,
            confidence_score=0.8,
        )
    
    def _generate_mock_api_response(self, request: LLMRequest) -> str:
        """Generate mock API response content."""
        # Extract method and path from prompt
        lines = request.prompt.split('\n')
        method = "GET"
        path = "/api/resource"
        
        for line in lines:
            if line.startswith("Method:"):
                method = line.split(":")[1].strip()
            elif line.startswith("Path:"):
                path = line.split(":")[1].strip()
        
        # Generate appropriate response based on method
        if method == "POST":
            response = {
                "status_code": 201,
                "headers": {
                    "content-type": "application/json",
                    "location": f"{path}/123"
                },
                "body": {
                    "id": 123,
                    "message": "Resource created successfully",
                    "created_at": "2024-01-01T12:00:00Z"
                }
            }
        elif method == "GET":
            if "{id}" in path or path.endswith("/123"):
                response = {
                    "status_code": 200,
                    "headers": {"content-type": "application/json"},
                    "body": {
                        "id": 123,
                        "name": "Sample Resource",
                        "status": "active",
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                }
            else:
                response = {
                    "status_code": 200,
                    "headers": {"content-type": "application/json"},
                    "body": {
                        "data": [
                            {"id": 1, "name": "Resource 1"},
                            {"id": 2, "name": "Resource 2"}
                        ],
                        "pagination": {
                            "page": 1,
                            "per_page": 10,
                            "total": 2
                        }
                    }
                }
        elif method == "PUT":
            response = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {
                    "id": 123,
                    "message": "Resource updated successfully",
                    "updated_at": "2024-01-01T12:00:00Z"
                }
            }
        elif method == "DELETE":
            response = {
                "status_code": 204,
                "headers": {},
                "body": None
            }
        else:
            response = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {"message": "Operation completed successfully"}
            }
        
        return json.dumps(response, indent=2)
    
    def _generate_mock_validation(self, request: LLMRequest) -> str:
        """Generate mock validation response."""
        validation_result = {
            "overall_score": 0.85,
            "issues": [
                {
                    "level": "warning",
                    "category": "schema",
                    "message": "Response includes additional fields not in documentation",
                    "field_path": "$.extra_field",
                    "suggestion": "Remove undocumented fields or update documentation"
                },
                {
                    "level": "info",
                    "category": "value",
                    "message": "Timestamp format is consistent with ISO 8601",
                    "field_path": "$.created_at",
                    "suggestion": "No action needed"
                }
            ],
            "summary": "Response is mostly compliant with documentation. Minor schema discrepancies found but overall structure and data types are correct."
        }
        
        return json.dumps(validation_result, indent=2)
