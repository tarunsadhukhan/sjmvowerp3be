"""
Material Inspection API endpoints.
Provides endpoints for QC/material inspection of jute gate entries.
Only shows entries where qc_check = 'N'.

Updated (2026-01-07): QC data now stored in jute_mr and jute_mr_li tables.
When inspection is complete:
1. Create jute_mr record (Material Receipt)
2. Create jute_mr_li records with QC data for each line item
3. Optionally create jute_moisture_rdg records for moisture readings
4. Set qc_check = 'Y' on jute_gate_entry
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
    insert_jute_mr_query,
    insert_jute_mr_li_query,
    insert_jute_moisture_rdg_query,
    get_jute_items_query,
    get_jute_qualities_by_item_query,
    get_mukam_list_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class MoistureReading(BaseModel):
    """Single moisture reading."""
    moisture_percentage: float


class MRLineItemCreate(BaseModel):
    """Model for creating a jute_mr_li record with QC data."""
    gate_entry_line_item_id: int
    # Challan data (copied from gate entry line item)
    challan_item_id: Optional[int] = None
    challan_quality_id: Optional[int] = None
    challan_quantity: Optional[float] = None
    challan_weight: Optional[float] = None
    # Actual data (received)
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
    """Request model for completing material inspection and creating MR."""
    gate_entry_id: int
    # MR-level data
    mr_weight: Optional[float] = None
    remarks: Optional[str] = None
    # Line items with QC data
    line_items: List[MRLineItemCreate] = []


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
    Get paginated list of gate entries pending material inspection (qc_check = 'N').
    
    Query params:
    - co_id: Company ID (required)
    - page: Page number (default: 1)
    - limit: Records per page (default: 10)
    - search: Search term
    """
    try:
        # Get query parameters
        q_co_id = request.query_params.get("co_id")
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
        count_query = get_material_inspection_table_count_query(co_id=co_id, search=q_search if q_search else None)
        count_params = {"co_id": co_id}
        if search_param:
            count_params["search"] = search_param

        count_result = db.execute(count_query, count_params).fetchone()
        total = count_result.total if count_result else 0

        # Get paginated data
        data_query = get_material_inspection_table_query(co_id=co_id, search=q_search if q_search else None)
        data_params = {"co_id": co_id, "limit": limit, "offset": offset}
        if search_param:
            data_params["search"] = search_param

        result = db.execute(data_query, data_params).fetchall()
        rows = [dict(r._mapping) for r in result]

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
    Get a single gate entry with line items for material inspection.
    
    Query params:
    - id: Gate Entry ID (required)
    """
    try:
        q_id = request.query_params.get("id")
        if not q_id:
            raise HTTPException(status_code=400, detail="id is required")
        
        try:
            gate_entry_id = int(q_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid id")

        # Get header data
        header_query = get_material_inspection_by_id_query()
        header_result = db.execute(header_query, {"gate_entry_id": gate_entry_id}).fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail="Gate entry not found")

        header = dict(header_result._mapping)

        # Check if already QC complete
        if header.get("qc_check") == "Y":
            raise HTTPException(status_code=400, detail="This gate entry has already been inspected")

        # Format dates
        for field in ["jute_gate_entry_date", "challan_date", "updated_date_time"]:
            if header.get(field):
                dt = header[field]
                if isinstance(dt, (datetime, date)):
                    header[field] = str(dt) if isinstance(dt, date) else dt.isoformat()

        # Get line items
        line_items_query = get_material_inspection_line_items_query()
        line_items_result = db.execute(line_items_query, {"gate_entry_id": gate_entry_id}).fetchall()
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
    Complete material inspection for a gate entry.
    Creates a jute_mr record with jute_mr_li records for QC data,
    then sets qc_check = 'Y' on the gate entry.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        gate_entry_id = body.gate_entry_id
        
        # Verify gate entry exists and is not already inspected
        header_query = get_material_inspection_by_id_query()
        header_result = db.execute(header_query, {"gate_entry_id": gate_entry_id}).fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail="Gate entry not found")

        header = dict(header_result._mapping)
        if header.get("qc_check") == "Y":
            raise HTTPException(status_code=400, detail="This gate entry has already been inspected")

        # Get user info for audit
        user_id = token_data.get("user_id")
        now = datetime.now()

        # Generate branch MR number
        mr_no_result = db.execute(
            text("SELECT COALESCE(MAX(branch_mr_no), 0) + 1 AS next_mr_no FROM jute_mr WHERE branch_id = :branch_id"),
            {"branch_id": header.get("branch_id")}
        ).fetchone()
        next_mr_no = mr_no_result.next_mr_no if mr_no_result else 1

        # Create jute_mr record
        mr_insert_query = insert_jute_mr_query()
        mr_params = {
            "branch_id": header.get("branch_id"),
            "branch_mr_no": next_mr_no,
            "jute_mr_date": now.date(),
            "jute_gate_entry_id": gate_entry_id,
            "jute_gate_entry_date": header.get("jute_gate_entry_date"),
            "challan_no": header.get("challan_no"),
            "challan_date": header.get("challan_date"),
            "jute_supplier_id": header.get("jute_supplier_id"),
            "party_id": header.get("party_id"),
            "mukam_id": header.get("mukam_id"),
            "unit_conversion": header.get("unit_conversion"),
            "po_id": header.get("po_id"),
            "mr_weight": body.mr_weight or header.get("net_weight"),
            "vehicle_no": header.get("vehicle_no"),
            "status_id": 1,  # Open status
            "remarks": body.remarks or header.get("remarks"),
            "updated_by": user_id,
            "updated_date_time": now,
        }
        db.execute(mr_insert_query, mr_params)
        
        # Get the inserted MR ID
        mr_id_result = db.execute(text("SELECT LAST_INSERT_ID() AS mr_id")).fetchone()
        mr_id = mr_id_result.mr_id if mr_id_result else None
        
        if not mr_id:
            raise HTTPException(status_code=500, detail="Failed to create Material Receipt")

        # Create jute_mr_li records
        if body.line_items:
            mr_li_insert_query = insert_jute_mr_li_query()
            moisture_insert_query = insert_jute_moisture_rdg_query()
            
            for item in body.line_items:
                mr_li_params = {
                    "jute_mr_id": mr_id,
                    "jute_gate_entry_lineitem_id": item.gate_entry_line_item_id,
                    "challan_item_id": item.challan_item_id,
                    "challan_quality_id": item.challan_quality_id,
                    "challan_quantity": item.challan_quantity,
                    "challan_weight": item.challan_weight,
                    "actual_item_id": item.actual_item_id,
                    "actual_quality": item.actual_quality_id,
                    "actual_qty": item.actual_qty,
                    "actual_weight": item.actual_weight,
                    "allowable_moisture": item.allowable_moisture,
                    "actual_moisture": item.actual_moisture,
                    "accepted_weight": item.accepted_weight,
                    "rate": item.rate or 0,
                    "warehouse_id": item.warehouse_id,
                    "marka": item.marka,
                    "crop_year": item.crop_year,
                    "remarks": item.remarks,
                    "status": "Active",
                    "updated_date_time": now,
                }
                db.execute(mr_li_insert_query, mr_li_params)
                
                # Get inserted MR line item ID for moisture readings
                mr_li_id_result = db.execute(text("SELECT LAST_INSERT_ID() AS mr_li_id")).fetchone()
                mr_li_id = mr_li_id_result.mr_li_id if mr_li_id_result else None
                
                # Insert moisture readings if provided
                if mr_li_id and item.moisture_readings:
                    for reading in item.moisture_readings:
                        db.execute(moisture_insert_query, {
                            "jute_mr_li_id": mr_li_id,
                            "moisture_percentage": reading.moisture_percentage,
                        })

        # Mark gate entry as QC complete
        complete_query = update_material_inspection_qc_complete()
        db.execute(complete_query, {
            "gate_entry_id": gate_entry_id,
            "updated_by": user_id,
            "updated_date_time": now,
        })

        db.commit()

        return {
            "success": True,
            "message": "Material inspection completed successfully",
            "gate_entry_id": gate_entry_id,
            "mr_id": mr_id,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error completing material inspection")
        raise HTTPException(status_code=500, detail=str(e))
