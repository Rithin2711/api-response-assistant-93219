import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import documents_router, mock_router, validation_router, reports_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("IntelliMock Backend starting up...")
    yield
    # Shutdown
    logger.info("IntelliMock Backend shutting down...")


# FastAPI app with comprehensive metadata
app = FastAPI(
    title="IntelliMock API",
    description="""
# IntelliMock - Intelligent API Response Assistant

IntelliMock is a powerful backend service that simulates, validates, and generates API responses using 
Retrieval-Augmented Generation (RAG) technology. It helps developers and QA teams test APIs with 
intelligent, documentation-aware mock responses.

## Key Features

### 📄 Document Management
- Upload and process OpenAPI specifications, JSON samples, and Postman collections
- Automatic content parsing and indexing for semantic search
- Support for YAML, JSON, and various API documentation formats

### 🤖 Intelligent Mock Generation  
- AI-powered response generation using LLM providers (Gemini, OpenAI, etc.)
- Context-aware responses based on uploaded documentation
- Realistic data generation following API schemas and patterns

### ✅ Response Validation
- Comprehensive validation against API documentation
- Schema compliance checking and data type validation
- LLM-powered analysis for advanced validation insights

### 📊 Detailed Reporting
- Validation reports with issue categorization and scoring
- Multiple export formats (JSON, HTML, PDF, Excel)
- Improvement suggestions and compliance metrics

### 🔍 Vector-Based Search
- RAG-powered document retrieval for context-aware responses
- Semantic search across uploaded documentation
- Intelligent chunking and embedding generation

## API Workflow

1. **Upload Documentation**: Submit OpenAPI specs, Postman collections, or JSON samples
2. **Create Mock Requests**: Define API requests with method, path, headers, and body
3. **Generate Responses**: AI generates realistic responses using documentation context
4. **Validate Results**: Comprehensive validation against documentation and best practices
5. **Export Reports**: Download detailed validation reports in multiple formats

## Authentication & Configuration

- **LLM Provider Setup**: Configure API keys for Gemini, OpenAI, or other providers
- **Document Context**: Specify which documents to use for each mock request
- **Validation Rules**: Customize validation criteria and scoring

## Use Cases

- **API Development**: Generate realistic mock responses during development
- **QA Testing**: Validate API responses against specifications  
- **Documentation Testing**: Ensure API docs match actual implementation
- **Integration Testing**: Simulate third-party API responses
- **API Design**: Prototype and validate API designs before implementation
""",
    version="1.0.0",
    contact={
        "name": "IntelliMock Support",
        "email": "support@intellimock.dev",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "Documents", 
            "description": "Document upload, processing, and management operations. Upload OpenAPI specs, JSON samples, Postman collections, and other API documentation for processing and indexing.",
        },
        {
            "name": "Mock API",
            "description": "Mock API request creation and response generation. Create realistic API responses using AI and uploaded documentation context.",
        },
        {
            "name": "Validation",
            "description": "Response validation and compliance checking. Validate generated responses against documentation and API best practices.",
        },
        {
            "name": "Reports",
            "description": "Validation report management and export. Generate, view, and download detailed validation reports in multiple formats.",
        },
    ],
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents_router)
app.include_router(mock_router)
app.include_router(validation_router)
app.include_router(reports_router)


@app.get("/", 
         tags=["Health"],
         summary="Health check",
         description="Check if the API is running and healthy")
def health_check():
    """
    Health check endpoint.
    
    Returns basic system information and confirms the API is operational.
    """
    return {
        "message": "IntelliMock API is healthy",
        "status": "operational",
        "version": "1.0.0",
        "services": {
            "document_service": "ready",
            "mock_service": "ready", 
            "validation_service": "ready",
            "report_service": "ready"
        }
    }


@app.get("/info",
         tags=["Health"], 
         summary="System information",
         description="Get detailed system information and capabilities")
def system_info():
    """
    Get system information and capabilities.
    """
    return {
        "name": "IntelliMock API",
        "version": "1.0.0",
        "description": "Intelligent API Response Assistant powered by RAG",
        "features": [
            "Document upload and processing",
            "AI-powered mock response generation", 
            "Response validation and analysis",
            "Multi-format report export",
            "Vector-based document search"
        ],
        "supported_formats": [
            "OpenAPI 3.x (JSON/YAML)",
            "Swagger 2.x (JSON/YAML)", 
            "JSON samples",
            "Postman collections",
            "Generic YAML files"
        ],
        "export_formats": [
            "JSON",
            "HTML", 
            "PDF",
            "Excel"
        ],
        "llm_providers": [
            "Mock (for testing)",
            "Gemini (with API key)",
            "OpenAI (with API key)",
            "Anthropic (with API key)"
        ]
    }
