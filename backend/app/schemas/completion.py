"""기사 완료 스키마"""
from datetime import datetime
from pydantic import BaseModel


class CompletionCreate(BaseModel):
    memo: str | None = None


class CompletionResponse(BaseModel):
    id: int
    stop_id: int
    completed_by_user_id: int | None
    completed_at: datetime
    memo: str | None

    model_config = {"from_attributes": True}


class PhotoResponse(BaseModel):
    id: int
    completion_id: int
    file_path: str
    filename: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
