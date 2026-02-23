"""Pydantic models for API request/response."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    response_mode: str = Field(default="detailed")
    company_id: str = Field(default="")


class HistoryDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


class CompanyItem(BaseModel):
    taxpayer_id: str
    taxpayer_name: str
    taxpayer_type: str
