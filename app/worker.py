import asyncio
from collections import Counter
from datetime import datetime, timedelta

from app import crud
from app.database import get_db
from app.models import ProcessStatus
from app.processor import parse_text_metrics
from app.websocket_manager import manager

TOP_N = 5


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
    accumulated_words = 0
    accumulated_lines = 0
    accumulated_chars = 0
    merged_counter: Counter = Counter()
    files_processed: list[str] = []

    for index, document in enumerate(documents, start=1):
        if process_id in stop_signals:
            with get_db() as db:
                process = crud.get_process(db, process_id)
                if process:
                    process.status = ProcessStatus.STOPPED.value
                    db.commit()
            return

        await asyncio.sleep(0.05)

        metrics = parse_text_metrics(document.content)
        accumulated_words += metrics["total_words"]
        accumulated_lines += metrics["total_lines"]
        accumulated_chars += metrics["total_chars"]
        merged_counter.update(metrics["word_counter"])
        files_processed.append(document.document_name)

        partial_result = {
            "total_words": accumulated_words,
            "total_lines": accumulated_lines,
            "total_chars": accumulated_chars,
            "most_frequent_words": [w for w, _ in merged_counter.most_common(TOP_N)],
            "files_processed": list(files_processed),
        }

        is_last = index == total
        percentage = round((index / total) * 100, 2)

        with get_db() as db:
            crud.mark_document_processed(db, document.id)
            crud.upsert_result(db, process_id, partial_result, is_finished=is_last)

            process = crud.get_process(db, process_id)
            if not process:
                return
            process.completed_files = index
            process.estimated_completion = datetime.utcnow() + timedelta(
                seconds=max(total - index, 0)
            )
            if is_last:
                process.status = ProcessStatus.COMPLETED.value
                process.estimated_completion = datetime.utcnow()
            db.commit()

        await manager.broadcast(
            process_id,
            {
                "process_id": process_id,
                "status": ProcessStatus.COMPLETED.value
                if is_last
                else ProcessStatus.RUNNING.value,
                "progress": {
                    "total_files": total,
                    "completed_files": index,
                    "percentage": percentage,
                },
                "results": {
                    **partial_result,
                    "is_finished": is_last,
                },
            },
        )
