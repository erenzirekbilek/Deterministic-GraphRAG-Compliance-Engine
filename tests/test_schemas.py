import pytest
from app.models.schemas import (
    QuestionRequest,
    RuleExtractionRequest,
    RuleReviewUpdate,
    BulkRuleReview,
    RuleApplicationRequest,
    RuleManualCreate,
    ExtractedRule,
    PendingRulesResponse,
    RuleListResponse
)


class TestSchemas:
    def test_question_request_valid(self):
        req = QuestionRequest(question="Can an intern approve a $500 expense?")
        assert req.question == "Can an intern approve a $500 expense?"
        assert req.topic == "approval"

    def test_question_request_custom_topic(self):
        req = QuestionRequest(question="Test question", topic="deletion")
        assert req.topic == "deletion"

    def test_rule_extraction_request(self):
        req = RuleExtractionRequest(text="The manager can approve up to $10,000")
        assert req.text == "The manager can approve up to $10,000"
        assert req.document_id is None

    def test_rule_review_update(self):
        review = RuleReviewUpdate(rule_id="RULE-123", status="approved")
        assert review.rule_id == "RULE-123"
        assert review.status == "approved"

    def test_bulk_rule_review(self):
        bulk = BulkRuleReview(reviews=[
            RuleReviewUpdate(rule_id="RULE-1", status="approved"),
            RuleReviewUpdate(rule_id="RULE-2", status="rejected")
        ])
        assert len(bulk.reviews) == 2

    def test_rule_application_request_empty(self):
        req = RuleApplicationRequest()
        assert req.document_id is None
        assert req.rule_ids is None

    def test_rule_application_request_with_document(self):
        req = RuleApplicationRequest(document_id="doc-123")
        assert req.document_id == "doc-123"

    def test_rule_manual_create(self):
        rule = RuleManualCreate(
            rule_type="HAS_AUTHORITY",
            source_entity="manager",
            target_entity="approve_expense",
            description="Manager can approve expenses"
        )
        assert rule.rule_type == "HAS_AUTHORITY"
        assert rule.source_entity == "manager"
        assert rule.limit is None

    def test_rule_manual_create_with_limit(self):
        rule = RuleManualCreate(
            rule_type="HAS_AUTHORITY",
            source_entity="manager",
            target_entity="approve_expense",
            description="Manager can approve expenses up to $5000",
            limit=5000.0
        )
        assert rule.limit == 5000.0

    def test_extracted_rule_defaults(self):
        rule = ExtractedRule(
            id="RULE-123",
            rule_type="HAS_AUTHORITY",
            source_entity="manager",
            target_entity="approve_expense",
            description="Test rule",
            confidence=0.95,
            source_text="Manager can approve expenses",
            source_document="policy.pdf"
        )
        assert rule.status == "pending"

    def test_pending_rules_response(self):
        response = PendingRulesResponse(
            document_id="doc-123",
            document_name="test.pdf",
            rules=[],
            stats={"total": 0, "pending": 0, "approved": 0, "rejected": 0}
        )
        assert response.stats["total"] == 0

    def test_rule_list_response(self):
        response = RuleListResponse(rules=[{"id": 1}, {"id": 2}], count=2)
        assert response.count == 2
