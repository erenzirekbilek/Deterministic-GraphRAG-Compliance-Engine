import io
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from app.models.schemas import (
    TextExtractionRequest, OntologyExtractionResponse, 
    OntologySchemaResponse, PDFExtractionResponse
)
from app.services.ontology_extraction_service import OntologyExtractionService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_ontology_service() -> OntologyExtractionService:
    from app.main import ontology_service
    return ontology_service


def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract text from uploaded PDF file."""
    try:
        import pypdf
        pdf_reader = pypdf.PdfReader(file.file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error("Failed to extract PDF text: %s", str(e))
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {str(e)}")


@router.post("/extract/pdf", response_model=PDFExtractionResponse, tags=["Ontology"])
async def extract_from_pdf(
    file: UploadFile = File(...),
    service: OntologyExtractionService = Depends(get_ontology_service)
):
    """
    Upload a PDF file to extract ontology entities and relationships.
    
    The system will:
    1. Extract text from the PDF
    2. Use LLM to extract entities and relationships from the text
    3. Validate each relationship against the ontology schema
    4. Reject any invalid relationships with "This violates the rule."
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    logger.info("Processing PDF file: %s", file.filename)
    
    try:
        text = extract_text_from_pdf(file)
        
        if not text or len(text) < 10:
            raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")
        
        logger.info("Extracted %d characters from PDF", len(text))
        
        result = service.extract_from_text(text)
        
        status = "partial" if result.get("rejected") else "success"
        if result.get("rejected"):
            status = "rejected" if not result.get("relationships") else "partial"
        
        return PDFExtractionResponse(
            document_id=result["document_id"],
            filename=file.filename,
            text_preview=text[:500] + "..." if len(text) > 500 else text,
            entities=result["entities"],
            relationships=result["relationships"],
            validation=result["validation"],
            rejected=result["rejected"],
            status=status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing PDF: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
