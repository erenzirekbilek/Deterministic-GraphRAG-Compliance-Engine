import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BatchDocument:
    document_id: str
    content: str
    filename: Optional[str] = None
    status: BatchStatus = BatchStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class BatchProcessor:
    """Process multiple documents in batch."""

    def __init__(self, extraction_service, max_concurrent: int = 3):
        self.extraction_service = extraction_service
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._batches: Dict[str, List[BatchDocument]] = {}

    async def process_batch(
        self, documents: List[Dict[str, str]], batch_id: str = None
    ) -> Dict[str, Any]:
        """Process a batch of documents."""
        batch_id = batch_id or f"batch-{int(time.time())}"

        batch_docs = []
        for doc in documents:
            batch_docs.append(
                BatchDocument(
                    document_id=doc.get("document_id", f"doc-{len(batch_docs)}"),
                    content=doc.get("content", ""),
                    filename=doc.get("filename"),
                )
            )

        self._batches[batch_id] = batch_docs

        results = await self._process_documents(batch_docs, batch_id)

        return {
            "batch_id": batch_id,
            "total": len(documents),
            "completed": sum(1 for r in results if r["status"] == "completed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "results": results,
        }

    async def _process_documents(
        self, documents: List[BatchDocument], batch_id: str
    ) -> List[Dict]:
        """Process documents with concurrency limit."""
        tasks = [self._process_single(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "document_id": documents[i].document_id,
                        "status": "failed",
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _process_single(self, doc: BatchDocument) -> Dict:
        """Process a single document."""
        async with self._semaphore:
            doc.status = BatchStatus.PROCESSING
            doc.started_at = time.time()

            try:
                result = await asyncio.to_thread(
                    self.extraction_service.extract_from_text,
                    doc.content,
                    doc.document_id,
                )

                doc.status = BatchStatus.COMPLETED
                doc.result = result
                doc.completed_at = time.time()

                return {
                    "document_id": doc.document_id,
                    "status": "completed",
                    "result": result,
                    "duration_ms": int((doc.completed_at - doc.started_at) * 1000),
                }
            except Exception as e:
                logger.error(f"Batch processing error for {doc.document_id}: {e}")
                doc.status = BatchStatus.FAILED
                doc.error = str(e)
                doc.completed_at = time.time()

                return {
                    "document_id": doc.document_id,
                    "status": "failed",
                    "error": str(e),
                }

    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """Get status of a batch."""
        if batch_id not in self._batches:
            return None

        docs = self._batches[batch_id]

        return {
            "batch_id": batch_id,
            "total": len(docs),
            "completed": sum(1 for d in docs if d.status == BatchStatus.COMPLETED),
            "processing": sum(1 for d in docs if d.status == BatchStatus.PROCESSING),
            "failed": sum(1 for d in docs if d.status == BatchStatus.FAILED),
            "pending": sum(1 for d in docs if d.status == BatchStatus.PENDING),
        }

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a pending batch."""
        if batch_id not in self._batches:
            return False

        for doc in self._batches[batch_id]:
            if doc.status == BatchStatus.PENDING:
                doc.status = BatchStatus.FAILED
                doc.error = "Cancelled by user"

        return True


class SimpleBatchProcessor:
    """Simplified batch processor for synchronous services."""

    def __init__(self, service, max_concurrent: int = 3):
        self.service = service
        self.max_concurrent = max_concurrent

    def process_batch(
        self, texts: List[str], document_ids: List[str] = None
    ) -> List[Dict]:
        """Process texts in batch."""
        if document_ids is None:
            document_ids = [f"doc-{i}" for i in range(len(texts))]

        results = []

        for text, doc_id in zip(texts, document_ids):
            try:
                result = self.service.extract_from_text(text, doc_id)
                results.append(
                    {"document_id": doc_id, "status": "success", "result": result}
                )
            except Exception as e:
                results.append(
                    {"document_id": doc_id, "status": "failed", "error": str(e)}
                )

        return results
