from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProgressSchema(BaseModel):
    total_files: int
    completed_files: int
    percentage: float


class ResultsSchema(BaseModel):
    total_words: int
    total_lines: int
    total_chars: int
    most_frequent_words: list[str] = Field(default_factory=list)
    files_processed: list[str] = Field(default_factory=list)
    is_finished: bool = False


class ProcessResponse(BaseModel):
    process_id: str
    status: str
    progress: ProgressSchema
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    results: Optional[ResultsSchema] = None
    error_message: Optional[str] = None


class StartProcessResponse(BaseModel):
    message: str
    process_id: str
    files: list[str]
