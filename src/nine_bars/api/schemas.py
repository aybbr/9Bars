"""Pydantic request bodies for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CoffeeCreate(BaseModel):
    name: str
    roaster: str | None = None
    origin: str | None = None
    process: str | None = None
    roast_level: str | None = None
    roast_date: str | None = None
    tasting_notes: list[str] = []


class ResearchRequest(BaseModel):
    text: str
    kind: Literal["name", "url", "free_text"] = "free_text"


class DraftPhase(BaseModel):
    name: str
    target_pressure_bar: float
    duration_s: float
    target_flow_g_s: float | None = None


class DraftCreate(BaseModel):
    name: str
    dose_g: float
    yield_g: float
    ratio: float
    temp_c: float
    grind_desc: str
    phases: list[DraftPhase] = []
    rationale: str
    assumptions: list[str] = []


class FeedbackCreate(BaseModel):
    shot_id: str
    acidity: int = Field(ge=1, le=5)
    sweetness: int = Field(ge=1, le=5)
    body: int = Field(ge=1, le=5)
    overall: int = Field(ge=1, le=5)
    bitterness: int = Field(default=3, ge=1, le=5)
    aroma: int = Field(default=3, ge=1, le=5)
    finish: int = Field(default=3, ge=1, le=5)
    note: str | None = None


class ApproveRequest(BaseModel):
    user_confirmed: bool


class NextActionRequest(BaseModel):
    coffee_id: str
    acidity: int = Field(ge=1, le=5)
    sweetness: int = Field(ge=1, le=5)
    body: int = Field(ge=1, le=5)
    overall: int = Field(ge=1, le=5)
