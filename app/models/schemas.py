from pydantic import BaseModel, Field
from typing import Optional


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500,
                          example="Can an intern approve a $500 expense?")
    topic: Optional[str] = Field(default="approval",
                                example="approval")


class LLMRawOutput(BaseModel):
    decision: str
    reason: str


class ComplianceResponse(BaseModel):
    question: str
    topic: str
    llm_raw_output: dict
    approved: bool
    validation_reason: str
    graph_rules_applied: list[str]
    llm_provider: str


class HealthResponse(BaseModel):
    status: str
    neo4j: str
    llm_provider: str


class TextExtractionRequest(BaseModel):
    text: str = Field(..., min_length=10, example="The Manager has authority to approve requests up to $10,000. However, an Intern requires Manager approval for any request.")
    document_id: Optional[str] = None


class EntityExtraction(BaseModel):
    name: str
    entity_type: str
    mention: str
    confidence: float


class RelationshipExtraction(BaseModel):
    source: str
    target: str
    relationship: str
    justification: str


class ValidationResult(BaseModel):
    source: str
    target: str
    relationship: str
    is_valid: bool
    reason: str


class RejectedExtraction(BaseModel):
    type: str
    name: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    relationship: Optional[str] = None
    reason: str


class OntologyExtractionResponse(BaseModel):
    document_id: str
    entities: list[EntityExtraction]
    relationships: list[RelationshipExtraction]
    validation: list[ValidationResult]
    rejected: list[RejectedExtraction]
    status: str


class OntologySchemaResponse(BaseModel):
    entity_types: list[dict]
    relationship_types: list[dict]


class PDFExtractionResponse(BaseModel):
    document_id: str
    filename: str
    text_preview: str
    entities: list[EntityExtraction]
    relationships: list[RelationshipExtraction]
    validation: list[ValidationResult]
    rejected: list[RejectedExtraction]
    status: str
