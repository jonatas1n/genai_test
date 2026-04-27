import asyncio
import uuid
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
)
from fastapi.websockets import WebSocketDisconnect

from app import crud
from app.database import get_db
from app.models import ProcessStatus, Result
from app.schemas import (
    ProcessResponse,
    ProgressSchema,
    ResultsSchema,
    StartProcessResponse,
)
from app.worker import execute_process
from app.websocket_manager import manager

router = APIRouter(prefix="/process", tags=["process"])
stop_signals: set[str] = set()


def _to_response(process, result) -> ProcessResponse:
    percentage = 0.0
    if process.total_files > 0:
        percentage = (process.completed_files / process.total_files) * 100

    response_results = None
    if result:
        response_results = ResultsSchema(
            total_words=result.total_words,
            total_lines=result.total_lines,
            total_chars=result.total_chars,
            most_frequent_words=result.most_frequent_words,
            files_processed=result.files_processed,
        )

    return ProcessResponse(
        process_id=process.process_id,
        status=process.status,
        progress=ProgressSchema(
            total_files=process.total_files,
            completed_files=process.completed_files,
            percentage=percentage,
        ),
        started_at=process.started_at,
        estimated_completion=process.estimated_completion,
        error_message=process.error_message,
        results=response_results,
    )


@router.post("/start", response_model=StartProcessResponse)
async def start_process(
    background_tasks: BackgroundTasks, documents: List[UploadFile] = File(...)
):
    if not documents:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    process_id = str(uuid.uuid4())
    parsed_documents: list[dict] = []
    for document in documents:
        content = (await document.read()).decode("utf-8", errors="ignore")
        parsed_documents.append({"name": document.filename, "content": content})

    with get_db() as db:
        crud.create_process(db, process_id, parsed_documents)

    background_tasks.add_task(asyncio.run, execute_process(process_id, stop_signals))
    return StartProcessResponse(
        message="Process started",
        process_id=process_id,
        files=[doc["name"] for doc in parsed_documents],
    )


@router.post("/stop/{process_id}", response_model=ProcessResponse)
async def stop_process(process_id: str):
    stop_signals.add(process_id)
    with get_db() as db:
        process = crud.get_process(db, process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found.")

        if process.status in {
            ProcessStatus.STOPPED.value,
            ProcessStatus.COMPLETED.value,
        }:
            raise HTTPException(
                status_code=400, detail="Process already finished or stopped."
            )

        process = crud.stop_process(db, process)
        result = db.query(Result).filter_by(process_id=process_id).first()
        return _to_response(process, result)


@router.get("/status/{process_id}", response_model=ProcessResponse)
async def get_process_status(process_id: str):
    with get_db() as db:
        process = crud.get_process(db, process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found.")
        result = db.query(Result).filter_by(process_id=process_id).first()
        return _to_response(process, result)


@router.get("/list", response_model=list[ProcessResponse])
async def list_processes():
    with get_db() as db:
        processes = crud.list_processes(db)
        responses = []
        for process in processes:
            result = db.query(Result).filter_by(process_id=process.process_id).first()
            responses.append(_to_response(process, result))
        return responses


@router.get("/results/{process_id}", response_model=ResultsSchema)
async def get_process_results(process_id: str):
    with get_db() as db:
        process = crud.get_process(db, process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found.")

        result = db.query(Result).filter_by(process_id=process_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Result not found.")

        return ResultsSchema(
            total_words=result.total_words,
            total_lines=result.total_lines,
            total_chars=result.total_chars,
            most_frequent_words=result.most_frequent_words,
            files_processed=result.files_processed,
        )


@router.websocket("/ws/{process_id}")
async def websocket_endpoint(websocket: WebSocket, process_id: str):
    with get_db() as db:
        process = crud.get_process(db, process_id)
        if not process:
            await websocket.close(code=4004)
            return

    await manager.connect(process_id, websocket)
    try:
        while True:
            # Check every second whether the process has finished.
            await asyncio.sleep(1)
            with get_db() as db:
                result = crud.get_result(db, process_id)
                if result and result.is_finished:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(process_id, websocket)
        await websocket.close()
