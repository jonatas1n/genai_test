from sqlalchemy.orm import Session

from app.models import Document, Process, ProcessStatus, Result


def create_process(db: Session, process_id: str, documents: list[dict]) -> Process:
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

    db.commit()
    db.refresh(process)
    return process


def get_process(db: Session, process_id: str) -> Process | None:
    return db.query(Process).filter(Process.process_id == process_id).first()


def stop_process(db: Session, process: Process) -> Process:
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
        return
    document.is_processed = True
    db.commit()


def upsert_result(db: Session, process_id: str, payload: dict) -> Result:
    result = db.query(Result).filter(Result.process_id == process_id).first()
    if result is None:
        result = Result(process_id=process_id)
        db.add(result)

    result.total_words = payload["total_words"]
    result.total_lines = payload["total_lines"]
    result.total_chars = payload["total_chars"]
    result.most_frequent_words = payload["most_frequent_words"]
    result.files_processed = payload["files_processed"]
    db.commit()
    db.refresh(result)
    return result
