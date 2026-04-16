import json
import csv
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Response
from typing import Optional
from app.models.schemas import (
    RuleExtractionRequest,
    RuleReviewUpdate,
    BulkRuleReview,
    RuleApplicationRequest,
    RuleApplicationResponse,
    PendingRulesResponse,
    RuleManualCreate,
    RuleListResponse,
)

router = APIRouter(tags=["Rule Management"])

rule_service = None


def get_rule_service():
    from app.main import rule_extraction_service

    return rule_extraction_service


def get_neo4j():
    from app.main import neo4j

    return neo4j


@router.post("/rules/extract", response_model=PendingRulesResponse)
async def extract_rules_from_text(
    request: RuleExtractionRequest,
    service=Depends(get_rule_service),
):
    result = service.extract_rules_from_text(
        text=request.text,
        document_id=request.document_id,
        document_name=request.document_name,
    )
    return {
        "document_id": result["document_id"],
        "document_name": result["document_name"],
        "rules": result["rules"],
        "stats": {
            "extracted": result["rules_extracted"],
            "saved": result["rules_saved"],
            "latency_ms": result["latency_ms"],
        },
    }


@router.post("/rules/extract/pdf")
async def extract_rules_from_pdf(
    file: UploadFile = File(...),
    service=Depends(get_rule_service),
):
    if file.filename is None or not file.filename.lower().endswith(
        (".pdf", ".txt", ".md", ".docx")
    ):
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Use PDF, TXT, MD, or DOCX."
        )

    content = await file.read()
    text = ""

    filename = file.filename or ""
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise HTTPException(status_code=500, detail="pypdf not installed")
    elif filename.lower().endswith(".docx"):
        try:
            from docx import Document
            import io

            doc = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise HTTPException(status_code=500, detail="python-docx not installed")
    else:
        text = content.decode("utf-8")

    if not text.strip():
        raise HTTPException(
            status_code=400, detail="File is empty or contains no text."
        )

    result = service.extract_rules_from_text(
        text=text,
        document_name=file.filename,
    )
    return {
        "document_id": result["document_id"],
        "document_name": result["document_name"],
        "filename": file.filename,
        "text_preview": text[:500],
        "rules": result["rules"],
        "stats": {
            "extracted": result["rules_extracted"],
            "saved": result["rules_saved"],
            "latency_ms": result["latency_ms"],
        },
    }


@router.get("/pending", response_model=PendingRulesResponse)
async def get_pending_rules(
    document_id: str = None,
    service=Depends(get_rule_service),
):
    rules = service.neo4j.get_pending_rules(document_id)
    stats = service.neo4j.get_pending_rules_stats()
    return {
        "document_id": document_id or "all",
        "document_name": None,
        "rules": rules,
        "stats": stats,
    }


@router.post("/review")
async def review_rule(
    review: RuleReviewUpdate,
    service=Depends(get_rule_service),
):
    result = service.review_rule(
        rule_id=review.rule_id,
        status=review.status,
        edits=review.edits,
    )
    return result


@router.post("/review/bulk")
async def bulk_review_rules(
    bulk: BulkRuleReview,
    service=Depends(get_rule_service),
):
    results = []
    for review in bulk.reviews:
        result = service.review_rule(
            rule_id=review.rule_id,
            status=review.status,
            edits=review.edits,
        )
        results.append(result)
    return {"reviewed": len(results), "results": results}


@router.post("/apply", response_model=RuleApplicationResponse)
async def apply_rules(
    request: RuleApplicationRequest = None,
    service=Depends(get_rule_service),
    neo4j=Depends(get_neo4j),
):
    doc_id = request.document_id if request else None
    result = service.apply_approved_rules(document_id=doc_id)
    return {
        "applied": result["applied"],
        "skipped": result["total_approved"] - result["applied"],
        "errors": result["errors"],
    }


@router.get("/applied", response_model=RuleListResponse)
async def get_applied_rules(neo4j=Depends(get_neo4j)):
    rules = neo4j.get_all_applied_rules()
    return {"rules": rules, "count": len(rules)}


@router.post("/manual")
async def create_manual_rule(
    rule: RuleManualCreate,
    neo4j=Depends(get_neo4j),
):
    rule_id = neo4j.generate_rule_id()
    neo4j.save_pending_rule(
        rule_id=rule_id,
        rule_type=rule.rule_type,
        source_entity=rule.source_entity,
        target_entity=rule.target_entity,
        description=rule.description,
        limit=rule.limit,
        confidence=1.0,
        source_text="Manually created",
        source_document="manual",
        source_page=None,
    )
    return {"rule_id": rule_id, "status": "pending"}


@router.delete("/pending/{rule_id}")
async def delete_pending_rule(rule_id: str, neo4j=Depends(get_neo4j)):
    neo4j.delete_pending_rule(rule_id)
    return {"deleted": rule_id}


@router.get("/stats")
async def get_rule_stats(neo4j=Depends(get_neo4j)):
    return neo4j.get_pending_rules_stats()


@router.get("/export")
async def export_rules(
    format: str = "json",
    status: Optional[str] = None,
    neo4j=Depends(get_neo4j),
):
    """Export rules as JSON or CSV."""
    rules = neo4j.get_pending_rules()

    if status:
        rules = [r for r in rules if r.get("status") == status]

    if format == "csv":
        if not rules:
            raise HTTPException(status_code=404, detail="No rules to export")

        output = io.StringIO()
        fieldnames = [
            "id",
            "rule_type",
            "source_entity",
            "target_entity",
            "description",
            "limit",
            "confidence",
            "source_text",
            "source_document",
            "status",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for rule in rules:
            writer.writerow({k: rule.get(k, "") for k in fieldnames})

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=rules_export.csv"},
        )

    return {"rules": rules, "count": len(rules), "format": "json"}


@router.post("/import")
async def import_rules(
    file: UploadFile = File(...),
    neo4j=Depends(get_neo4j),
):
    """Import rules from JSON file."""
    content = await file.read()

    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files supported")

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if not isinstance(data, dict) or "rules" not in data:
        raise HTTPException(status_code=400, detail="JSON must contain 'rules' array")

    imported = 0
    errors = []

    for rule_data in data["rules"]:
        try:
            rule_id = neo4j.generate_rule_id()
            neo4j.save_pending_rule(
                rule_id=rule_id,
                rule_type=rule_data.get("rule_type", "HAS_AUTHORITY"),
                source_entity=rule_data.get("source_entity"),
                target_entity=rule_data.get("target_entity"),
                description=rule_data.get("description", ""),
                limit=rule_data.get("limit"),
                confidence=rule_data.get("confidence", 0.8),
                source_text=rule_data.get("source_text", "Imported from file"),
                source_document=rule_data.get("source_document", "import"),
                source_page=rule_data.get("source_page"),
            )
            imported += 1
        except Exception as e:
            errors.append(f"Failed to import rule: {str(e)}")

    return {"imported": imported, "errors": errors}
