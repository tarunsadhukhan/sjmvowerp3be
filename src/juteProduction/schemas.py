"""Pydantic schemas for jute production - spreader reports."""
from datetime import date
from typing import List, Optional

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


# =============================================================================
# Drawing Reports — daily_drawing_transaction (machine-wise output meters)
# =============================================================================


class DrawingReportParams(BaseModel):
    """Query params for drawing report endpoints."""
    branch_id: int = Field(..., gt=0)
    from_date: date
    to_date: date

    @model_validator(mode="after")
    def _check_range(self) -> "DrawingReportParams":
        if self.from_date > self.to_date:
            raise ValueError("from_date must be <= to_date")
        return self


class DrawingSummaryRow(BaseModel):
    report_date: str
    opening: float
    production: float
    issue: float
    closing: float


class DrawingSummaryResponse(BaseModel):
    data: List[DrawingSummaryRow]


class DrawingDateProductionRow(BaseModel):
    report_date: str
    quality_id: int
    quality_name: str
    opening: float
    production: float
    issue: float
    closing: float


class DrawingDateProductionResponse(BaseModel):
    data: List[DrawingDateProductionRow]


class DrawingDateIssueRow(BaseModel):
    report_date: str
    quality_id: int
    quality_name: str
    issue: float


class DrawingDateIssueResponse(BaseModel):
    data: List[DrawingDateIssueRow]


class DrawingQualityDetailsRow(BaseModel):
    quality_id: int
    quality_name: str
    total_production: float
    total_issue: float
    balance: float


class DrawingQualityDetailsResponse(BaseModel):
    data: List[DrawingQualityDetailsRow]


class DrawingShiftMatrixRow(BaseModel):
    mc_id: int
    mc_short_name: str
    shed_type: Optional[str] = None
    drg_type: Optional[int] = None
    spell_id: int
    spell_name: str
    op: float
    cl: float
    unit: float
    eff: float


class DrawingShiftMatrixResponse(BaseModel):
    data: List[DrawingShiftMatrixRow]


# =============================================================================
# Spinning Reports
# =============================================================================


class SpinningReportParams(BaseModel):
    """Query params for spinning report endpoints."""
    branch_id: int = Field(..., gt=0)
    from_date: date
    to_date: date

    @model_validator(mode="after")
    def _check_range(self) -> "SpinningReportParams":
        if self.from_date > self.to_date:
            raise ValueError("from_date must be <= to_date")
        return self


class SpinningProductionEffRow(BaseModel):
    report_date: str
    quality_id: Optional[int] = None
    quality_name: Optional[str] = None
    spell_id: Optional[int] = None
    spell_name: Optional[str] = None
    frames: float
    production: float
    tarprod: float


class SpinningProductionEffResponse(BaseModel):
    data: List[SpinningProductionEffRow]


class SpinningMcDateRow(BaseModel):
    report_date: str
    mc_id: Optional[int] = None
    mc_name: Optional[str] = None
    frames: float
    production: float
    tarprod: float


class SpinningMcDateResponse(BaseModel):
    data: List[SpinningMcDateRow]


class SpinningEmpDateRow(BaseModel):
    report_date: str
    emp_id: Optional[int] = None
    emp_name: Optional[str] = None
    production: float
    eff: float


class SpinningEmpDateResponse(BaseModel):
    data: List[SpinningEmpDateRow]


class SpinningFrameRunningRow(BaseModel):
    frame_id: Optional[int] = None
    frame_name: Optional[str] = None
    running_hours: float
    total_hours: float
    eff: float


class SpinningFrameRunningResponse(BaseModel):
    data: List[SpinningFrameRunningRow]


class SpinningRunningHoursEffRow(BaseModel):
    mc_id: Optional[int] = None
    mc_name: Optional[str] = None
    quality_id: Optional[int] = None
    quality_name: Optional[str] = None
    production: float
    running_hours: float
    eff: float


class SpinningRunningHoursEffResponse(BaseModel):
    data: List[SpinningRunningHoursEffRow]
