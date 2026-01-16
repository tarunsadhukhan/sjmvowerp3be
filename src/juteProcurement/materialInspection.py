"""
Jute Quality Check API endpoints.
Provides endpoints for QC/material inspection of jute MR entries.
Only shows entries where qc_check IS NULL OR qc_check = 0 (pending QC).

Updated (2026-01-16): 
- Renamed from "Material Inspection" to "Jute Quality Check"
- Now uses jute_mr table instead of deleted jute_gate_entry table
- QC data stored directly in jute_mr_li table
- When QC is complete, set qc_check = 1 on jute_mr
- Moisture readings stored in jute_moisture_rdg table
"""

from fastapi import Depends, Request, HTTPException, APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.query import (
    get_material_inspection_table_query,
    get_material_inspection_table_count_query,
    get_material_inspection_by_id_query,
    get_material_inspection_line_items_query,
    update_material_inspection_qc_complete,
    insert_jute_mr_li_query,
    insert_jute_moisture_rdg_query,
    get_jute_items_query,
    get_jute_qualities_by_item_query,
    get_mukam_list_query,
)
from src.models.jute import JuteMrLi, JuteMoistureRdg

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class MoistureReading(BaseModel):
    """Single moisture reading."""
    moisture_percentage: float


class MRLineItemCreate(BaseModel):
    """Model for updating a jute_mr_li record with QC data."""
    jute_mr_li_id: int  # Line item ID from jute_mr_li table
    # Actual data (received/QC verified)
    actual_item_id: Optional[int] = None
    actual_quality_id: Optional[int] = None
    actual_qty: Optional[float] = None
    actual_weight: Optional[float] = None
    # Moisture
    allowable_moisture: Optional[float] = None
    actual_moisture: Optional[str] = None  # Can be comma-separated values
    moisture_readings: List[MoistureReading] = []
    # Pricing and storage
    accepted_weight: Optional[float] = None
    rate: Optional[float] = None
    warehouse_id: Optional[int] = None
    marka: Optional[str] = None
    crop_year: Optional[int] = None
    remarks: Optional[str] = None


class MaterialInspectionCompleteRequest(BaseModel):
    """Request model for completing quality check on a jute MR."""
    jute_mr_id: int  # Now uses jute_mr_id instead of gate_entry_id
    # MR-level data
    net_weight: Optional[float] = None
    tare_weight: Optional[float] = None
    remarks: Optional[str] = None
    # Line items with QC data
    line_items: List[MRLineItemCreate] = []


class MoistureReadingsRequest(BaseModel):
    """Request model for saving moisture readings for a MR line item."""

    moisture_readings: List[float]


class MoistureReadingsResponse(BaseModel):
    """Response model after saving moisture readings."""

    average_moisture: float
    readings: List[float]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/get_inspection_table")
async def get_material_inspection_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get paginated list of jute MR entries pending quality check (qc_check IS NULL OR qc_check = 0).
    
    Updated 2026-01-16: Now uses jute_mr table instead of jute_gate_entry.
    
    Query params:
    - co_id: Company ID (required)
    - branch_ids: Comma-separated branch IDs (optional)
    - page: Page number (default: 1)
    - limit: Records per page (default: 10)
    - search: Search term
    """
    try:
        # Get query parameters
        q_co_id = request.query_params.get("co_id")
        q_branch_ids = request.query_params.get("branch_ids", "").strip()
        q_page = request.query_params.get("page", "1")
        q_limit = request.query_params.get("limit", "10")
        q_search = request.query_params.get("search", "").strip()

        # Validate co_id
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        # Parse branch_ids
        branch_ids = []
        if q_branch_ids:
            try:
                branch_ids = [int(bid.strip()) for bid in q_branch_ids.split(",") if bid.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid branch_ids format")

        # Parse pagination
        try:
            page = max(1, int(q_page))
            limit = min(100, max(1, int(q_limit)))
        except ValueError:
            page = 1
            limit = 10

        offset = (page - 1) * limit

        # Build search parameter
        search_param = f"%{q_search}%" if q_search else None

        # Get total count
        count_query = get_material_inspection_table_count_query(
            co_id=co_id, 
            branch_ids=branch_ids if branch_ids else None,
            search=q_search if q_search else None
        )
        count_params = {"co_id": co_id}
        if search_param:
            count_params["search"] = search_param
        # Add branch_id params
        for i, bid in enumerate(branch_ids):
            count_params[f"branch_id_{i}"] = bid

        count_result = db.execute(count_query, count_params).fetchone()
        total = count_result.total if count_result else 0

        # Get paginated data
        data_query = get_material_inspection_table_query(
            co_id=co_id, 
            branch_ids=branch_ids if branch_ids else None,
            search=q_search if q_search else None
        )
        data_params = {"co_id": co_id, "limit": limit, "offset": offset}
        if search_param:
            data_params["search"] = search_param
        # Add branch_id params
        for i, bid in enumerate(branch_ids):
            data_params[f"branch_id_{i}"] = bid

        result = db.execute(data_query, data_params).fetchall()
        rows = [dict(r._mapping) for r in result]

        # Add 'id' field for frontend compatibility
        for row in rows:
            row["id"] = row.get("jute_mr_id")

        # Format dates for JSON serialization
        for row in rows:
            if row.get("jute_gate_entry_date"):
                dt = row["jute_gate_entry_date"]
                if isinstance(dt, (datetime, date)):
                    row["jute_gate_entry_date"] = str(dt) if isinstance(dt, date) else dt.isoformat()
            if row.get("updated_date_time"):
                dt = row["updated_date_time"]
                if isinstance(dt, datetime):
                    row["updated_date_time"] = dt.isoformat()

        return {
            "data": rows,
            "total": total,
            "page": page,
            "page_size": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching material inspection table")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_inspection_by_id")
async def get_material_inspection_by_id(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single jute MR entry with line items for quality check.
    
    Updated 2026-01-16: Now uses jute_mr_id instead of gate_entry_id.
    
    Query params:
    - id: Jute MR ID (required) - using jute_mr_id
    """
    try:
        q_id = request.query_params.get("id")
        if not q_id:
            raise HTTPException(status_code=400, detail="id is required")
        
        try:
            jute_mr_id = int(q_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid id")

        # Get header data
        header_query = get_material_inspection_by_id_query()
        header_result = db.execute(header_query, {"jute_mr_id": jute_mr_id}).fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail="Jute MR entry not found")

        header = dict(header_result._mapping)

        # Check if already QC complete
        if header.get("qc_check") == 1 or header.get("qc_check") == "1":
            raise HTTPException(status_code=400, detail="This entry has already completed QC")

        # Format dates
        for field in ["jute_gate_entry_date", "challan_date", "updated_date_time"]:
            if header.get(field):
                dt = header[field]
                if isinstance(dt, (datetime, date)):
                    header[field] = str(dt) if isinstance(dt, date) else dt.isoformat()

        # Get line items from jute_mr_li
        line_items_query = get_material_inspection_line_items_query()
        line_items_result = db.execute(line_items_query, {"jute_mr_id": jute_mr_id}).fetchall()
        line_items = [dict(r._mapping) for r in line_items_result]

        return {
            "header": header,
            "line_items": line_items,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching material inspection by ID")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_inspection_setup")
async def get_material_inspection_setup(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get dropdown options for material inspection form.
    Returns jute items, qualities, mukams, and warehouses.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        # Get jute items
        items_query = get_jute_items_query()
        items_result = db.execute(items_query, {"co_id": co_id}).fetchall()
        items = [dict(r._mapping) for r in items_result]

        # Get mukams
        mukam_query = get_mukam_list_query()
        mukam_result = db.execute(mukam_query).fetchall()
        mukams = [dict(r._mapping) for r in mukam_result]

        # Get warehouses
        warehouse_query = text("""
            SELECT warehouse_id, warehouse_name
            FROM ware_house_master
            WHERE co_id = :co_id AND (active = 1 OR active IS NULL)
            ORDER BY warehouse_name
        """)
        warehouse_result = db.execute(warehouse_query, {"co_id": co_id}).fetchall()
        warehouses = [dict(r._mapping) for r in warehouse_result]

        return {
            "jute_items": items,
            "mukams": mukams,
            "warehouses": warehouses,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching material inspection setup")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_mr_line_item/{mr_li_id}")
async def get_mr_line_item(
    mr_li_id: int,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single jute MR line item with its moisture readings.

    This is useful when viewing or editing moisture readings after MR creation.
    """
    try:
        mr_li: Optional[JuteMrLi] = (
            db.query(JuteMrLi)
            .filter(JuteMrLi.jute_mr_li_id == mr_li_id)
            .first()
        )
        if not mr_li:
            raise HTTPException(status_code=404, detail="MR line item not found")

        readings: List[JuteMoistureRdg] = (
            db.query(JuteMoistureRdg)
            .filter(JuteMoistureRdg.jute_mr_li_id == mr_li_id)
            .order_by(JuteMoistureRdg.jute_moisture_rdg_id)
            .all()
        )
        moisture_values = [
            float(r.moisture_percentage)
            for r in readings
            if r.moisture_percentage is not None
        ]

        average = sum(moisture_values) / len(moisture_values) if moisture_values else 0.0

        line_item = {
            "jute_mr_li_id": mr_li.jute_mr_li_id,
            "jute_mr_id": mr_li.jute_mr_id,
            "jute_gate_entry_lineitem_id": mr_li.jute_gate_entry_lineitem_id,
            "challan_item_id": mr_li.challan_item_id,
            "challan_quality_id": mr_li.challan_quality_id,
            "challan_quantity": mr_li.challan_quantity,
            "challan_weight": mr_li.challan_weight,
            "actual_item_id": mr_li.actual_item_id,
            "actual_quality": mr_li.actual_quality,
            "actual_qty": mr_li.actual_qty,
            "actual_weight": mr_li.actual_weight,
            "allowable_moisture": mr_li.allowable_moisture,
            "actual_moisture": mr_li.actual_moisture,
            "accepted_weight": mr_li.accepted_weight,
        }

        return {
            "line_item": line_item,
            "moisture_readings": moisture_values,
            "average_moisture": average,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching MR line item with moisture readings")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save_moisture_readings/{mr_li_id}", response_model=MoistureReadingsResponse)
async def save_moisture_readings(
    mr_li_id: int,
    body: MoistureReadingsRequest,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Save moisture readings for a jute MR line item.

    - Deletes existing readings for the MR line item
    - Inserts new readings
    - Calculates average moisture and updates jute_mr_li.actual_moisture
    - Recalculates accepted_weight using:
        if actual_moisture > allowable_moisture:
            accepted_weight = actual_weight - (actual_weight * (actual_moisture - allowable_moisture) / 100)
        else:
            accepted_weight = actual_weight
    """
    try:
        mr_li: Optional[JuteMrLi] = (
            db.query(JuteMrLi)
            .filter(JuteMrLi.jute_mr_li_id == mr_li_id)
            .first()
        )
        if not mr_li:
            raise HTTPException(status_code=404, detail="MR line item not found")

        # Clear existing readings
        db.query(JuteMoistureRdg).filter(
            JuteMoistureRdg.jute_mr_li_id == mr_li_id
        ).delete()

        readings = [float(r) for r in body.moisture_readings if r is not None]

        # Insert new readings
        for value in readings:
            db.add(
                JuteMoistureRdg(
                    jute_mr_li_id=mr_li_id,
                    moisture_percentage=value,
                )
            )

        # Calculate average moisture
        average = sum(readings) / len(readings) if readings else 0.0
        mr_li.actual_moisture = f"{average:.2f}"

        # Recalculate accepted_weight
        actual_weight = float(mr_li.actual_weight or 0.0)
        allowable_moisture = (
            float(mr_li.allowable_moisture)
            if mr_li.allowable_moisture is not None
            else None
        )

        accepted_weight = actual_weight
        if (
            readings
            and allowable_moisture is not None
            and average > allowable_moisture
            and actual_weight > 0
        ):
            deduction_percentage = average - allowable_moisture
            accepted_weight = actual_weight - (
                actual_weight * deduction_percentage / 100.0
            )

        mr_li.accepted_weight = accepted_weight

        db.commit()

        return MoistureReadingsResponse(
            average_moisture=average,
            readings=readings,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error saving moisture readings for MR line item")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_qualities_by_item/{item_id}")
async def get_qualities_by_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get jute qualities for a specific jute item.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        qualities_query = get_jute_qualities_by_item_query()
        qualities_result = db.execute(qualities_query, {"item_id": item_id, "co_id": co_id}).fetchall()
        qualities = [dict(r._mapping) for r in qualities_result]

        return {
            "qualities": qualities,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching qualities by item")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete_inspection")
async def complete_material_inspection(
    request: Request,
    body: MaterialInspectionCompleteRequest,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Complete quality check for a jute MR entry.
    Updates jute_mr_li records with QC data and sets qc_check = 1 on jute_mr.
    
    Updated 2026-01-16: 
    - Now uses jute_mr_id instead of gate_entry_id
    - jute_mr already exists, we just update line items and mark QC complete
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        jute_mr_id = body.jute_mr_id
        
        # Verify jute_mr exists and is not already QC complete
        header_query = get_material_inspection_by_id_query()
        header_result = db.execute(header_query, {"jute_mr_id": jute_mr_id}).fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail="Jute MR entry not found")

        header = dict(header_result._mapping)
        if header.get("qc_check") == 1 or header.get("qc_check") == "1":
            raise HTTPException(status_code=400, detail="This entry has already completed QC")

        # Get user info for audit
        user_id = token_data.get("user_id")
        now = datetime.now()

        # Update jute_mr header fields if provided
        mr_updates = []
        mr_params = {"jute_mr_id": jute_mr_id, "updated_by": user_id, "updated_date_time": now}
        
        if body.net_weight is not None:
            mr_updates.append("net_weight = :net_weight")
            mr_params["net_weight"] = body.net_weight
        if body.tare_weight is not None:
            mr_updates.append("tare_weight = :tare_weight")
            mr_params["tare_weight"] = body.tare_weight
        if body.remarks is not None:
            mr_updates.append("remarks = :remarks")
            mr_params["remarks"] = body.remarks
        
        if mr_updates:
            mr_updates.append("updated_by = :updated_by")
            mr_updates.append("updated_date_time = :updated_date_time")
            mr_update_sql = f"UPDATE jute_mr SET {', '.join(mr_updates)} WHERE jute_mr_id = :jute_mr_id"
            db.execute(text(mr_update_sql), mr_params)

        # Update jute_mr_li records with QC data
        moisture_insert_query = insert_jute_moisture_rdg_query()
        
        for item in body.line_items:
            # Skip line items without a valid jute_mr_li_id (shouldn't happen in normal flow)
            if not item.jute_mr_li_id or item.jute_mr_li_id <= 0:
                logger.warning(f"Skipping line item with invalid jute_mr_li_id: {item.jute_mr_li_id}")
                continue
                
            # Determine average moisture from readings or provided value
            avg_moisture: Optional[float] = None
            if item.moisture_readings:
                values = [
                    float(r.moisture_percentage)
                    for r in item.moisture_readings
                    if r.moisture_percentage is not None
                ]
                if values:
                    avg_moisture = sum(values) / len(values)
            elif item.actual_moisture:
                try:
                    avg_moisture = float(item.actual_moisture)
                except (TypeError, ValueError):
                    avg_moisture = None

            actual_moisture_str = f"{avg_moisture:.2f}" if avg_moisture is not None else item.actual_moisture

            # Calculate accepted weight using average moisture and allowable moisture
            actual_weight = float(item.actual_weight or 0.0)
            allowable_moisture = float(item.allowable_moisture) if item.allowable_moisture is not None else None

            accepted_weight = actual_weight
            if (
                avg_moisture is not None
                and allowable_moisture is not None
                and avg_moisture > allowable_moisture
                and actual_weight > 0
            ):
                deduction_percentage = avg_moisture - allowable_moisture
                accepted_weight = actual_weight - (actual_weight * deduction_percentage / 100.0)

            # Update the existing jute_mr_li record
            update_li_sql = text("""
                UPDATE jute_mr_li
                SET actual_item_id = COALESCE(:actual_item_id, actual_item_id),
                    actual_jute_quality_id = COALESCE(:actual_quality_id, actual_jute_quality_id),
                    actual_quantity = COALESCE(:actual_qty, actual_quantity),
                    actual_weight = COALESCE(:actual_weight, actual_weight),
                    allowable_moisture = COALESCE(:allowable_moisture, allowable_moisture),
                    actual_moisture = COALESCE(:actual_moisture, actual_moisture),
                    accepted_weight = :accepted_weight,
                    rate = COALESCE(:rate, rate),
                    warehouse_id = COALESCE(:warehouse_id, warehouse_id),
                    marka = COALESCE(:marka, marka),
                    crop_year = COALESCE(:crop_year, crop_year),
                    remarks = COALESCE(:remarks, remarks),
                    updated_date_time = :updated_date_time
                WHERE jute_mr_li_id = :jute_mr_li_id
            """)
            
            db.execute(update_li_sql, {
                "jute_mr_li_id": item.jute_mr_li_id,
                "actual_item_id": item.actual_item_id,
                "actual_quality_id": item.actual_quality_id,
                "actual_qty": item.actual_qty,
                "actual_weight": item.actual_weight,
                "allowable_moisture": item.allowable_moisture,
                "actual_moisture": actual_moisture_str,
                "accepted_weight": accepted_weight,
                "rate": item.rate,
                "warehouse_id": item.warehouse_id,
                "marka": item.marka,
                "crop_year": item.crop_year,
                "remarks": item.remarks,
                "updated_date_time": now,
            })

            # Delete existing moisture readings and insert new ones
            if item.moisture_readings:
                db.execute(
                    text("DELETE FROM jute_moisture_rdg WHERE jute_mr_li_id = :jute_mr_li_id"),
                    {"jute_mr_li_id": item.jute_mr_li_id}
                )
                for reading in item.moisture_readings:
                    db.execute(moisture_insert_query, {
                        "jute_mr_li_id": item.jute_mr_li_id,
                        "moisture_percentage": reading.moisture_percentage,
                    })

        # Mark jute_mr as QC complete
        complete_query = update_material_inspection_qc_complete()
        db.execute(complete_query, {
            "jute_mr_id": jute_mr_id,
            "updated_by": user_id,
            "updated_date_time": now,
        })

        db.commit()

        return {
            "success": True,
            "message": "Quality check completed successfully",
            "jute_mr_id": jute_mr_id,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error completing quality check")
        raise HTTPException(status_code=500, detail=str(e))
