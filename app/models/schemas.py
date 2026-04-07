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
