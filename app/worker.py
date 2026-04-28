import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta

from app import crud
from app.database import get_db
from app.models import ProcessStatus
from app.processor import generate_summary, parse_text_metrics
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

TOP_N = 5
PAUSE_POLL_INTERVAL = 0.5


def _rebuild_partial_state(documents):
    total_words = 0
    total_lines = 0
    total_chars = 0
    merged_counter: Counter = Counter()
    files_processed: list[str] = []

    for document in documents:
        metrics = parse_text_metrics(document.content)
        total_words += metrics["total_words"]
        total_lines += metrics["total_lines"]
        total_chars += metrics["total_chars"]
        merged_counter.update(metrics["word_counter"])
        files_processed.append(document.document_name)

    return {
        "total_words": total_words,
        "total_lines": total_lines,
        "total_chars": total_chars,
        "merged_counter": merged_counter,
        "files_processed": files_processed,
    }


async def execute_process(process_id: str, stop_signals: set[str]) -> None:
    logger.info("Starting execution of process '%s'.", process_id)

    with get_db() as db:
        process = crud.get_process(db, process_id)
        if not process:
            logger.warning("Process '%s' was not found.", process_id)
            return

        documents = crud.get_documents_by_process(db, process_id)
        if not documents:
            process.status = ProcessStatus.FAILED.value
            process.error_message = "No documents available to process."
            db.commit()
            logger.warning("Process '%s' has no documents to process.", process_id)
            return

        processed_documents = [
            document for document in documents if document.is_processed
        ]
        pending_documents = [
            document for document in documents if not document.is_processed
        ]

    rebuilt_state = _rebuild_partial_state(processed_documents)
    accumulated_words = rebuilt_state["total_words"]
    accumulated_lines = rebuilt_state["total_lines"]
    accumulated_chars = rebuilt_state["total_chars"]
    merged_counter: Counter = rebuilt_state["merged_counter"]
    files_processed: list[str] = rebuilt_state["files_processed"]

    total_files = len(documents)
    completed_files = len(processed_documents)

    if not pending_documents:
        logger.info("Process '%s' has no pending documents left.", process_id)

        with get_db() as db:
            process = crud.get_process(db, process_id)
            if process and process.status not in {
                ProcessStatus.COMPLETED.value,
                ProcessStatus.STOPPED.value,
            }:
                process.status = ProcessStatus.COMPLETED.value
                process.completed_files = total_files
                process.estimated_completion = datetime.utcnow()
                db.commit()

        await manager.broadcast(
            process_id,
            {
                "process_id": process_id,
                "status": ProcessStatus.COMPLETED.value,
                "progress": {
                    "total_files": total_files,
                    "completed_files": total_files,
                    "percentage": 100.0,
                },
                "results": {
                    "total_words": accumulated_words,
                    "total_lines": accumulated_lines,
                    "total_chars": accumulated_chars,
                    "most_frequent_words": [
                        word for word, _ in merged_counter.most_common(TOP_N)
                    ],
                    "files_processed": files_processed,
                    "is_finished": True,
                },
            },
        )
        return

    for document in pending_documents:
        paused_logged = False

        while True:
            if process_id in stop_signals:
                logger.info("Stop signal received for process '%s'.", process_id)

                with get_db() as db:
                    process = crud.get_process(db, process_id)
                    if process:
                        process.status = ProcessStatus.STOPPED.value
                        process.estimated_completion = None
                        db.commit()

                stop_signals.discard(process_id)
                return

            with get_db() as db:
                process = crud.get_process(db, process_id)
                if not process:
                    logger.warning(
                        "Process '%s' disappeared during execution.", process_id
                    )
                    stop_signals.discard(process_id)
                    return

                current_status = process.status

            if current_status == ProcessStatus.PAUSED.value:
                if not paused_logged:
                    logger.info("Process '%s' paused. Waiting for resume.", process_id)
                    paused_logged = True
                await asyncio.sleep(PAUSE_POLL_INTERVAL)
                continue

            if current_status == ProcessStatus.STOPPED.value:
                logger.info("Process '%s' was stopped.", process_id)
                stop_signals.discard(process_id)
                return

            if current_status == ProcessStatus.FAILED.value:
                logger.info("Process '%s' is already marked as failed.", process_id)
                stop_signals.discard(process_id)
                return

            break

        try:
            await asyncio.sleep(0.05)

            logger.debug(
                "Processing document '%s' for process '%s'.",
                document.document_name,
                process_id,
            )

            metrics = parse_text_metrics(document.content)
            accumulated_words += metrics["total_words"]
            accumulated_lines += metrics["total_lines"]
            accumulated_chars += metrics["total_chars"]
            merged_counter.update(metrics["word_counter"])
            files_processed.append(document.document_name)
            completed_files += 1

            partial_result = {
                "total_words": accumulated_words,
                "total_lines": accumulated_lines,
                "total_chars": accumulated_chars,
                "most_frequent_words": [
                    word for word, _ in merged_counter.most_common(TOP_N)
                ],
                "files_processed": list(files_processed),
                "summary": generate_summary(document.content),
            }

            is_last = completed_files == total_files
            percentage = round((completed_files / total_files) * 100, 2)

            with get_db() as db:
                crud.mark_document_processed(db, document.id)
                crud.upsert_result(
                    db,
                    process_id,
                    partial_result,
                    is_finished=is_last,
                )

                process = crud.get_process(db, process_id)
                if not process:
                    logger.warning(
                        "Process '%s' was not found while updating progress.",
                        process_id,
                    )
                    stop_signals.discard(process_id)
                    return

                process.completed_files = completed_files
                process.estimated_completion = datetime.utcnow() + timedelta(
                    seconds=max(total_files - completed_files, 0)
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
                        "total_files": total_files,
                        "completed_files": completed_files,
                        "percentage": percentage,
                    },
                    "results": {
                        **partial_result,
                        "is_finished": is_last,
                    },
                },
            )

        except Exception as exc:
            logger.exception(
                "Unexpected error while processing '%s' in process '%s'.",
                document.document_name,
                process_id,
            )

            with get_db() as db:
                process = crud.get_process(db, process_id)
                if process:
                    process.status = ProcessStatus.FAILED.value
                    process.error_message = str(exc)
                    process.estimated_completion = None
                    db.commit()

            await manager.broadcast(
                process_id,
                {
                    "process_id": process_id,
                    "status": ProcessStatus.FAILED.value,
                    "progress": {
                        "total_files": total_files,
                        "completed_files": completed_files,
                        "percentage": round((completed_files / total_files) * 100, 2),
                    },
                    "results": {
                        "total_words": accumulated_words,
                        "total_lines": accumulated_lines,
                        "total_chars": accumulated_chars,
                        "most_frequent_words": [
                            word for word, _ in merged_counter.most_common(TOP_N)
                        ],
                        "files_processed": files_processed,
                        "is_finished": False,
                    },
                },
            )
            stop_signals.discard(process_id)
            return

    stop_signals.discard(process_id)
    logger.info("Process '%s' completed successfully.", process_id)
