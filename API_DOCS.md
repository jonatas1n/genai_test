# API Documentation

## Overview
- **Project**: Document Processing API  
- **Version**: v1  
- **Owner**: Jônatas Gomes Barbosa da Silva  

This API was designed to process text documents asynchronously, allowing real-time progress tracking and aggregated content metrics.

---

## Status Codes
- `200` OK — request completed successfully  
- `201` Created — resource created successfully  
- `400` Bad Request — validation error or incorrect usage  
- `404` Not Found — resource not found  
- `500` Internal Server Error — unexpected server error  

---

## Endpoints

### POST /process/start
**Description**  
Starts a new processing job with one or more text files.

**Authorization**  
None

**Request Headers**
| Header | Required | Example |
|---|---|---|
| Content-Type | Yes | multipart/form-data |

**Request Body**  
File upload via form-data in the `documents` field.

**Successful Response (200)**
```json
{
  "message": "Process started",
  "process_id": "uuid",
  "files": ["file1.txt", "file2.txt"]
}
```

**Error Responses**
- `400`: no files were sent  

---

### GET /process/status/{process_id}
**Description**  
Returns the current process state, including progress and partial results.

**Authorization**  
None

**Path Parameters**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| process_id | string | Yes | Process identifier | `abc123` |

**Successful Response (200)**
```json
{
  "process_id": "abc123",
  "status": "RUNNING",
  "progress": {
    "total_files": 5,
    "completed_files": 2,
    "percentage": 40.0
  },
  "results": {
    "total_words": 300,
    "files_processed": ["a.txt", "b.txt"],
    "is_finished": false
  }
}
```

**Error Responses**
- `404`: process not found  

---

### GET /process/results/{process_id}
**Description**  
Returns the final or partial processing result.

**Authorization**  
None

**Path Parameters**
| Name | Type | Required | Description |
|---|---|---|---|
| process_id | string | Yes | Process identifier |

**Successful Response (200)**
```json
{
  "total_words": 1000,
  "total_lines": 200,
  "total_chars": 8000,
  "most_frequent_words": ["the", "and"],
  "files_processed": ["doc1.txt", "doc2.txt"],
  "is_finished": true,
  "summary": "Short summary of the processed content..."
}
```

**Error Responses**
- `404`: result not found  

---

### POST /process/stop/{process_id}
**Description**  
Stops a running process.

**Authorization**  
None

**Successful Response (200)**
```json
{
  "process_id": "abc123",
  "status": "STOPPED"
}
```

**Error Responses**
- `400`: process already finished  
- `404`: process not found  

---

### POST /process/pause/{process_id}
**Description**  
Temporarily pauses a running process.

**Authorization**  
None

**Successful Response (200)**  
Returns the updated process state.

---

### POST /process/resume/{process_id}
**Description**  
Resumes a paused process.

**Authorization**  
None

**Successful Response (200)**  
Returns the updated process state.

---

### GET /process/list
**Description**  
Lists all registered processes with status and progress.

**Authorization**  
None

**Successful Response (200)**
```json
[
  {
    "process_id": "abc123",
    "status": "COMPLETED",
    "progress": {
      "total_files": 5,
      "completed_files": 5,
      "percentage": 100.0
    }
  }
]
```

---

### WebSocket /process/ws/{process_id}
**Description**  
Real-time channel to follow processing progress.

**Received Message**
```json
{
  "process_id": "abc123",
  "status": "RUNNING",
  "progress": {
    "total_files": 5,
    "completed_files": 3,
    "percentage": 60.0
  },
  "results": {
    "total_words": 500,
    "files_processed": ["a.txt"],
    "is_finished": false
  }
}
```

The connection is automatically closed when processing finishes.

---

## Data Models

### Process
| Field | Type | Description |
|---|---|---|
| process_id | string | Unique identifier |
| status | string | Current process state |
| total_files | integer | Total number of files |
| completed_files | integer | Number of files already processed |
| started_at | datetime | Processing start timestamp |
| estimated_completion | datetime | Estimated completion timestamp |

---

### Result
| Field | Type | Description |
|---|---|---|
| total_words | integer | Total word count |
| total_lines | integer | Total line count |
| total_chars | integer | Total character count |
| most_frequent_words | list | Most frequent words |
| files_processed | list | Already processed files |
| summary | string | Content summary |
| is_finished | boolean | Indicates completion |

---

## Rate Limiting
No rate limiting is currently configured.

---

## Webhooks
Not applicable.

---

## Changelog
- 2026-04-28: Initial API version with support for asynchronous processing, WebSocket updates, and execution control