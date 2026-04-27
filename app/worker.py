import asyncio
from datetime import datetime, timedelta

from app import crud
from app.database import get_db
from app.models import ProcessStatus
from app.processor import aggregate_results


async def execute_process(process_id: str, stop_signals: set[str]) -> None:
    with get_db() as db:
        documents = crud.get_documents_by_process(db, process_id)
        if not documents:
            process = crud.get_process(db, process_id)
            if process:
                process.status = ProcessStatus.FAILED.value
                process.error_message = "No documents available to process."
                db.commit()
            return

    total = len(documents)
    processed_payloads: list[dict] = []

    for index, document in enumerate(documents, start=1):
        if process_id in stop_signals:
            with get_db() as db:
                process = crud.get_process(db, process_id)
                if process:
                    process.status = ProcessStatus.STOPPED.value
                    db.commit()
            return

        await asyncio.sleep(0.05)
        processed_payloads.append(
            {"name": document.document_name, "content": document.content}
        )

        with get_db() as db:
            crud.mark_document_processed(db, document.id)
            process = crud.get_process(db, process_id)
            if not process:
                return
            process.completed_files = index
            process.estimated_completion = datetime.utcnow() + timedelta(
                seconds=max(total - index, 0)
            )
            db.commit()

    results = aggregate_results(processed_payloads)
    with get_db() as db:
        crud.upsert_result(db, process_id, results)
        process = crud.get_process(db, process_id)
        if not process:
            return
        process.status = ProcessStatus.COMPLETED.value
        process.estimated_completion = datetime.utcnow()
        db.commit()
