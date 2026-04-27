import logging
import random
import time

from sqlalchemy.orm import Session

from app.models import Document, Process, ProcessStatus, Result

logger = logging.getLogger(__name__)


def create_process(db: Session, process_id: str, documents: list[dict]) -> Process:
    logger.info(
        "Creating process '%s' with %d document(s).", process_id, len(documents)
    )

    process = Process(
        process_id=process_id,
        total_files=len(documents),
        completed_files=0,
        status=ProcessStatus.RUNNING.value,
    )
    db.add(process)

    for document in documents:
        db.add(
            Document(
                process_id=process_id,
                document_name=document["name"],
                content=document["content"],
            )
        )

    # Create an empty result so the WebSocket can already find the record.
    db.add(
        Result(
            process_id=process_id,
            total_words=0,
            total_lines=0,
            total_chars=0,
            most_frequent_words=[],
            files_processed=[],
            is_finished=False,
        )
    )

    db.commit()
    db.refresh(process)
    logger.info("Process '%s' created successfully.", process_id)
    return process


def resume_process(db: Session, process: Process) -> Process:
    logger.info("Resuming process '%s'.", process.process_id)
    process.status = ProcessStatus.RUNNING.value
    db.commit()
    db.refresh(process)
    return process


def pause_process(db: Session, process: Process) -> Process:
    logger.info("Pausing process '%s'.", process.process_id)
    process.status = ProcessStatus.PAUSED.value
    db.commit()
    db.refresh(process)
    return process


def get_process(db: Session, process_id: str) -> Process | None:
    return db.query(Process).filter(Process.process_id == process_id).first()


def stop_process(db: Session, process: Process) -> Process:
    logger.info("Stopping process '%s'.", process.process_id)
    process.status = ProcessStatus.STOPPED.value
    db.commit()
    db.refresh(process)
    return process


def list_processes(db: Session) -> list[Process]:
    return db.query(Process).order_by(Process.started_at.desc()).all()


def get_documents_by_process(db: Session, process_id: str) -> list[Document]:
    return db.query(Document).filter(Document.process_id == process_id).all()


def mark_document_processed(db: Session, document_id: int) -> None:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        logger.warning(
            "Document id=%d not found when marking as processed.", document_id
        )
        return
    document.is_processed = True
    db.commit()


def get_result(db: Session, process_id: str) -> Result | None:
    return db.query(Result).filter(Result.process_id == process_id).first()


def upsert_result(
    db: Session, process_id: str, payload: dict, is_finished: bool = False
) -> Result:
    result = db.query(Result).filter(Result.process_id == process_id).first()
    if result is None:
        logger.debug("No existing result for '%s', creating a new one.", process_id)
        result = Result(process_id=process_id)
        db.add(result)

    result.total_words = payload["total_words"]
    result.total_lines = payload["total_lines"]
    result.total_chars = payload["total_chars"]
    result.most_frequent_words = payload["most_frequent_words"]
    result.files_processed = payload["files_processed"]
    result.is_finished = is_finished

    delay_seconds = random.randint(1, 10)
    time.sleep(5 + delay_seconds)

    db.commit()
    db.refresh(result)

    if is_finished:
        logger.info("Result for process '%s' marked as finished.", process_id)

    return result
