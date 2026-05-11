"""Pydantic schemas for jute production - spreader reports."""
from datetime import date
from typing import List

from pydantic import BaseModel, Field, model_validator


class SpreaderReportParams(BaseModel):
    """Query params for spreader report endpoints."""
    branch_id: int = Field(..., gt=0)
    from_date: date
    to_date: date

    @model_validator(mode="after")
    def _check_range(self) -> "SpreaderReportParams":
        if self.from_date > self.to_date:
            raise ValueError("from_date must be <= to_date")
        return self


class SpreaderSummaryRow(BaseModel):
    report_date: str
    opening: float
    production: float
    issue: float
    closing: float


class SpreaderSummaryResponse(BaseModel):
    data: List[SpreaderSummaryRow]


class SpreaderDateProductionRow(BaseModel):
    report_date: str
    quality_id: int
    quality_name: str
    opening: float
    production: float
    issue: float
    closing: float


class SpreaderDateProductionResponse(BaseModel):
    data: List[SpreaderDateProductionRow]


class SpreaderDateIssueRow(BaseModel):
    report_date: str
    quality_id: int
    quality_name: str
    issue: float


class SpreaderDateIssueResponse(BaseModel):
    data: List[SpreaderDateIssueRow]


class SpreaderQualityDetailsRow(BaseModel):
    quality_id: int
    quality_name: str
    total_production: float
    total_issue: float
    balance: float


class SpreaderQualityDetailsResponse(BaseModel):
    data: List[SpreaderQualityDetailsRow]
