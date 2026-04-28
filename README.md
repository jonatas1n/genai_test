# Document Processing System

REST API for asynchronous text document processing with real-time monitoring.

Tool presentation video: [https://youtu.be/GVMY4jKIS1w](https://youtu.be/GVMY4jKIS1w)

## About the Project

This system allows users to upload `.txt` files, process them in batches, and extract content metrics.  
All processing is asynchronous and non-blocking. Each process has a full lifecycle with state control, and results are updated incrementally as files are analyzed.

The main design goal is to keep the architecture simple and practical. Processing runs in the background using FastAPI `BackgroundTasks`, and the database is used for both persistence and state coordination between the worker and the API layer.

---

## Features

- Asynchronous processing of multiple `.txt` files
- Per-file and aggregated metrics extraction: words, lines, characters, most frequent words, and summary
- Full lifecycle control: start, pause, resume, stop
- Incremental results updated after each processed file
- Real-time updates via WebSocket
- Web UI for monitoring
- Process state and results persistence in PostgreSQL

### Process States

| State | Description |
|---|---|
| `RUNNING` | Processing is in progress |
| `PAUSED` | Temporarily paused |
| `COMPLETED` | Finished successfully |
| `FAILED` | Finished with an error |
| `STOPPED` | Manually stopped |

---

## Technology Stack

- **Python 3.12**
- **FastAPI** - Web framework and WebSocket support
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Alembic** - Migrations
- **Docker + Docker Compose** - Runtime environment

---

## How to Run

### Prerequisites

- Docker
- Docker Compose

### Start the Environment

```bash
git clone <repo-url>
cd <repo>
docker compose up --build
```

API base routes are available at `http://localhost:8000/process`.  
The web interface is available at `http://localhost:8000`.

### Run Migrations Manually (Optional)

Migrations run automatically on startup. If you need to run them manually:

```bash
docker compose exec app alembic upgrade head
```

---

## Test Data

The `data/input/` folder contains 10 `.txt` files based on classic literature and philosophy texts, each with more than 500 words:

- Pride and Prejudice
- Moby-Dick
- Frankenstein
- Adventures of Huckleberry Finn
- A Tale of Two Cities
- The Republic (Plato)
- Federalist No. 10
- Gettysburg Address + Second Inaugural Address
- On the Origin of Species
- The Wealth of Nations

To seed the database with these files via script:

```bash
docker compose exec app python scripts/seed_files.py
```

---

## Tests

```bash
docker compose exec app pytest tests/ -v
```

The test suite covers core flows: start process, check status, list processes, stop a process, and validate results after completion.

---

## Main Endpoints

| Method | Route | Description |
|---|---|---|
| POST | `/process/start` | Starts a new process |
| GET | `/process/status/{id}` | Returns current process state |
| GET | `/process/results/{id}` | Returns process results |
| POST | `/process/stop/{id}` | Stops a process |
| POST | `/process/pause/{id}` | Pauses a process |
| POST | `/process/resume/{id}` | Resumes a process |
| GET | `/process/list` | Lists all processes |
| WS | `/process/ws/{id}` | Real-time updates |

Full endpoint documentation is available in [`API_DOCS.md`](./API_DOCS.md).

---

## Technical Decisions

**Why not Celery?**  
Celery is an excellent distributed worker solution. However, this local processing system does not require that level of infrastructure. FastAPI `BackgroundTasks` is sufficient and avoids the complexity of configuring an external broker such as Redis or RabbitMQ.

**Why incremental results?**  
Incremental updates allow clients to monitor progress through WebSocket or polling without waiting for full completion.

**Why Alembic migrations?**  
Every schema change is versioned. The migration history reflects the evolution of the data model over time.

---

## Project Structure

```
.
├── app/
│   ├── api.py              # Endpoints and WebSocket
│   ├── worker.py           # Asynchronous processing logic
│   ├── processor.py        # Text metrics extraction
│   ├── crud.py             # Database operations
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── database.py         # Session configuration
│   ├── websocket_manager.py
│   ├── main.py
│   ├── static/
│   └── templates/
├── alembic/
├── data/input/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── API_DOCS.md
└── requirements.txt
```
