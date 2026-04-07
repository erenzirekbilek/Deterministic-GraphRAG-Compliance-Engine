from pydantic import BaseModel, Field
from typing import Optional, List


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


class ConflictItem(BaseModel):
    type: str
    severity: str
    message: str
    details: dict


class ConflictDetectionResponse(BaseModel):
    total_conflicts: int
    critical: int
    warning: int
    conflicts: list[ConflictItem]


class ExtractedRule(BaseModel):
    id: str
    rule_type: str = Field(..., description="HAS_AUTHORITY, REQUIRES_PRECONDITION, MUST_FULFILL, IS_PROHIBITED, DEPENDS_ON, APPLIES_TO")
    source_entity: str = Field(..., description="Source party/entity name")
    target_entity: str = Field(..., description="Target action/obligation name")
    description: str
    limit: Optional[float] = None
    confidence: float
    source_text: str = Field(..., description="Original text excerpt from the document")
    source_document: str
    source_page: Optional[int] = None
    status: str = Field(default="pending", description="pending, approved, rejected, edited")


class RuleExtractionRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Policy text to extract rules from")
    document_id: Optional[str] = None
    document_name: Optional[str] = None


class RuleReviewUpdate(BaseModel):
    rule_id: str
    status: str = Field(..., description="approved or rejected")
    edits: Optional[dict] = Field(default=None, description="Optional edits to rule fields")


class BulkRuleReview(BaseModel):
    reviews: List[RuleReviewUpdate]


class RuleApplicationRequest(BaseModel):
    document_id: Optional[str] = None
    rule_ids: Optional[List[str]] = None


class RuleApplicationResponse(BaseModel):
    applied: int
    skipped: int
    errors: List[str]


class PendingRulesResponse(BaseModel):
    document_id: str
    document_name: Optional[str]
    rules: List[ExtractedRule]
    stats: dict


class RuleManualCreate(BaseModel):
    rule_type: str
    source_entity: str
    target_entity: str
    description: str
    limit: Optional[float] = None


class RuleListResponse(BaseModel):
    rules: List[dict]
    count: int
