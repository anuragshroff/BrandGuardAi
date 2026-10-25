"""Request/response models (Pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["Creator", "Manager", "Admin", "Legal"]


class ScanCreate(BaseModel):
    title: str = Field(default="Untitled draft", max_length=255)
    content: str = Field(min_length=1, max_length=40_000)
    channel: str = "Blog Post"
    audience: str = "Enterprise IT"
    region: str = "North America"
    campaign: str = "Q4 Global Launch"
    actor: str = "Dhanraj Sonar"
    role: Role = "Creator"


class FindingAction(BaseModel):
    actor: str = "Dhanraj Sonar"
    role: Role = "Manager"
    note: str = ""


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2_000)
    finding_id: str | None = None
    author: str = "Dhanraj Sonar"
    role: Role = "Creator"


class ApprovalAction(BaseModel):
    actor: str = "Brand Manager"
    role: Role = "Manager"


class GuidelineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = "Tone"
    section: str = "Uploaded clause"
    content: str = Field(min_length=1)
    code: str | None = None
    tags: str = ""


class GuidelineOut(BaseModel):
    id: str
    code: str
    title: str
    category: str
    section: str
    content: str
    tags: str
    created_at: str
