"""Pydantic models for API request/response."""
from typing import Optional, List, Dict

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    response_mode: str = Field(default="detailed")
    company_id: str = Field(default="")
    thinking_mode: str = Field(default="quick")  # "quick" | "think" | "deep"
    conversation_history: Optional[List[Dict]] = Field(default=None)  # 对话历史（可选）
    conversation_depth: int = Field(default=3, ge=2, le=5)  # 对话轮次（2-5）


class HistoryDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


class CompanyItem(BaseModel):
    taxpayer_id: str
    taxpayer_name: str
    taxpayer_type: str


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="enterprise")
    display_name: str = Field(default="")
    is_active: int = Field(default=1)
    company_ids: list[str] = Field(default_factory=list)


class InterpretRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    result: dict = Field(...)
    response_mode: str = Field(default="detailed")
    company_id: str = Field(default="")
    cache_key: str = Field(default="")
    conversation_history: Optional[List[Dict]] = Field(default=None)  # 对话历史（可选）


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[int] = None
    company_ids: Optional[list[str]] = None


class CaptchaVerifyRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
