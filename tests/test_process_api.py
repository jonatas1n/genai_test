from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import api as process_api
from app.models import ProcessStatus


@dataclass
class FakeProcess:
    process_id: str
    total_files: int
    completed_files: int = 0
    status: str = ProcessStatus.RUNNING.value
    started_at: datetime = field(default_factory=datetime.utcnow)
    estimated_completion: datetime | None = None
    error_message: str | None = None


@dataclass
class FakeResult:
    process_id: str
    total_words: int = 0
    total_lines: int = 0
    total_chars: int = 0
    most_frequent_words: list[str] = field(default_factory=list)
    files_processed: list[str] = field(default_factory=list)
    is_finished: bool = False


@pytest.fixture
def fake_backend(monkeypatch):
    store = {
        "processes": {},
        "results": {},
    }

    @contextmanager
    def fake_get_db():
        yield object()

    def create_process(_db, process_id: str, documents: list[dict]):
        process = FakeProcess(process_id=process_id, total_files=len(documents))
        store["processes"][process_id] = process
        store["results"][process_id] = FakeResult(process_id=process_id)
        return process

    def get_process(_db, process_id: str):
        return store["processes"].get(process_id)

    def list_processes(_db):
        return sorted(
            store["processes"].values(), key=lambda proc: proc.started_at, reverse=True
        )

    def get_result(_db, process_id: str):
        return store["results"].get(process_id)

    def stop_process(_db, process):
        process.status = ProcessStatus.STOPPED.value
        return process

    def pause_process(_db, process):
        process.status = ProcessStatus.PAUSED.value
        return process

    def resume_process(_db, process):
        process.status = ProcessStatus.RUNNING.value
        return process

    async def fake_execute_process(_process_id: str, _stop_signals: set[str]):
        # We patch this to avoid starting real background work in endpoint tests.
        return None

    monkeypatch.setattr(process_api, "get_db", fake_get_db)
    monkeypatch.setattr(process_api.crud, "create_process", create_process)
    monkeypatch.setattr(process_api.crud, "get_process", get_process)
    monkeypatch.setattr(process_api.crud, "list_processes", list_processes)
    monkeypatch.setattr(process_api.crud, "get_result", get_result)
    monkeypatch.setattr(process_api.crud, "stop_process", stop_process)
    monkeypatch.setattr(process_api.crud, "pause_process", pause_process, raising=False)
    monkeypatch.setattr(process_api.crud, "resume_process", resume_process, raising=False)
    monkeypatch.setattr(process_api, "execute_process", fake_execute_process)

    return store


@pytest.fixture
def client(fake_backend):
    app = FastAPI()
    app.include_router(process_api.router)
    return TestClient(app)


def _sample_uploads():
    return [
        ("documents", ("chapter_1.txt", b"hello world\nsecond line", "text/plain")),
        ("documents", ("chapter_2.txt", b"more words here", "text/plain")),
    ]


def test_start_process_returns_created_process_with_uploaded_filenames(client, fake_backend):
    response = client.post("/process/start", files=_sample_uploads())

    assert response.status_code == 200
    payload = response.json()

    assert payload["message"] == "Process started"
    assert payload["files"] == ["chapter_1.txt", "chapter_2.txt"]

    process_id = payload["process_id"]
    stored_process = fake_backend["processes"][process_id]
    assert stored_process.total_files == 2
    assert stored_process.status == ProcessStatus.RUNNING.value


def test_pause_and_resume_flow_enforces_valid_status_transitions(client):
    start_response = client.post("/process/start", files=_sample_uploads())
    process_id = start_response.json()["process_id"]

    pause_response = client.post(f"/process/pause/{process_id}")
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == ProcessStatus.PAUSED.value

    resume_response = client.post(f"/process/resume/{process_id}")
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == ProcessStatus.RUNNING.value

    invalid_resume = client.post(f"/process/resume/{process_id}")
    assert invalid_resume.status_code == 400
    assert invalid_resume.json()["detail"] == "Only paused processes can be resumed."


def test_stop_endpoint_marks_process_as_stopped_and_rejects_duplicate_stop(client):
    start_response = client.post("/process/start", files=_sample_uploads())
    process_id = start_response.json()["process_id"]

    first_stop = client.post(f"/process/stop/{process_id}")
    assert first_stop.status_code == 200
    assert first_stop.json()["status"] == ProcessStatus.STOPPED.value

    second_stop = client.post(f"/process/stop/{process_id}")
    assert second_stop.status_code == 400
    assert second_stop.json()["detail"] == "Process already finished or stopped."


def test_status_list_and_results_endpoints_return_expected_payloads(client):
    first_process = client.post("/process/start", files=_sample_uploads()).json()["process_id"]
    second_process = client.post("/process/start", files=_sample_uploads()).json()["process_id"]

    status_response = client.get(f"/process/status/{first_process}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["process_id"] == first_process
    assert status_payload["status"] == ProcessStatus.RUNNING.value
    assert status_payload["progress"]["percentage"] == 0.0

    list_response = client.get("/process/list")
    assert list_response.status_code == 200
    listed_process_ids = {entry["process_id"] for entry in list_response.json()}
    assert {first_process, second_process}.issubset(listed_process_ids)

    results_response = client.get(f"/process/results/{first_process}")
    assert results_response.status_code == 200
    assert results_response.json() == {
        "total_words": 0,
        "total_lines": 0,
        "total_chars": 0,
        "most_frequent_words": [],
        "files_processed": [],
        "is_finished": False,
        "summary": "",
    }


def test_status_for_unknown_process_returns_404(client):
    missing_response = client.get("/process/status/non-existent-process")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Process not found."
