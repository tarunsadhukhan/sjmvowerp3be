"""
Jute Gate Entry API endpoints.
Provides CRUD operations for jute gate entry management.
"""

from fastapi import Depends, Request, HTTPException, APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, time
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.query import (
    get_jute_gate_entry_table_query,
    get_jute_gate_entry_table_count_query,
    get_jute_gate_entry_by_id_query,
    get_jute_gate_entry_line_items_query,
    get_branches_query,
    get_mukam_list_query,
    get_all_suppliers_query,
    get_parties_by_supplier_query,
    get_jute_items_query,
    get_jute_qualities_by_item_query,
    get_open_jute_pos_query,
    get_jute_po_for_gate_entry_query,
    get_jute_po_line_items_for_gate_entry_query,
    get_vehicle_types_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_jute_gate_entry_table")
async def get_jute_gate_entry_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get paginated list of Jute Gate Entries.
    
    Query params:
    - co_id: Company ID (required)
    - branch_ids: Comma-separated list of branch IDs to filter by (optional)
    - page: Page number (default: 1)
    - limit: Records per page (default: 10)
    - search: Search term for gate entry no, challan no, or vehicle no
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

        # Parse branch_ids (comma-separated list)
        branch_ids = []
        if q_branch_ids:
            try:
                branch_ids = [int(bid.strip()) for bid in q_branch_ids.split(",") if bid.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid branch_ids format")

        # Parse pagination
        try:
            page = max(1, int(q_page))
            limit = min(100, max(1, int(q_limit)))  # Clamp between 1 and 100
        except ValueError:
            page = 1
            limit = 10

        offset = (page - 1) * limit

        # Build search parameter
        search_param = f"%{q_search}%" if q_search else None

        # Build params dict for count query
        count_params = {"co_id": co_id}
        if search_param:
            count_params["search"] = search_param
        # Add branch_id params
        for i, bid in enumerate(branch_ids):
            count_params[f"branch_id_{i}"] = bid

        # Get total count
        count_query = get_jute_gate_entry_table_count_query(
            co_id=co_id, 
            branch_ids=branch_ids if branch_ids else None,
            search=q_search if q_search else None
        )
        count_result = db.execute(count_query, count_params).fetchone()
        total = count_result.total if count_result else 0

        # Build params dict for data query
        data_params = {"co_id": co_id, "limit": limit, "offset": offset}
        if search_param:
            data_params["search"] = search_param
        # Add branch_id params
        for i, bid in enumerate(branch_ids):
            data_params[f"branch_id_{i}"] = bid

        # Get paginated data
        data_query = get_jute_gate_entry_table_query(
            co_id=co_id,
            branch_ids=branch_ids if branch_ids else None,
            search=q_search if q_search else None
        )
        result = db.execute(data_query, data_params).fetchall()
        rows = [dict(r._mapping) for r in result]

        # Format dates for JSON serialization
        for row in rows:
            if row.get("jute_gate_entry_date"):
                row["jute_gate_entry_date"] = str(row["jute_gate_entry_date"])
            if row.get("in_time"):
                row["in_time"] = str(row["in_time"])
            if row.get("out_date"):
                row["out_date"] = str(row["out_date"])
            if row.get("out_time"):
                row["out_time"] = str(row["out_time"])
            if row.get("challan_date"):
                row["challan_date"] = str(row["challan_date"])
            if row.get("updated_date_time"):
                row["updated_date_time"] = str(row["updated_date_time"])
            # Map jute_mr_id to id for frontend compatibility
            if row.get("jute_mr_id"):
                row["id"] = row["jute_mr_id"]

        return {
            "data": rows,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching jute gate entry table")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/get_jute_gate_entry_by_id/{jute_mr_id}")
async def get_jute_gate_entry_by_id(
    jute_mr_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single Jute Gate Entry by ID with line items.
    
    Updated 2026-01-15: Now uses jute_mr table (merged gate entry + MR).
    The parameter is jute_mr_id which corresponds to the jute_mr table.
    """
    try:
        q_co_id = request.query_params.get("co_id")

        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        query = get_jute_gate_entry_by_id_query()
        result = db.execute(query, {"jute_mr_id": jute_mr_id, "co_id": co_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Jute Gate Entry not found")

        row = dict(result._mapping)

        # Format dates for JSON serialization
        for date_field in ["jute_gate_entry_date", "in_time", "out_date", "out_time", "challan_date", "updated_date_time"]:
            if row.get(date_field):
                row[date_field] = str(row[date_field])

        # Fetch line items
        line_items_query = get_jute_gate_entry_line_items_query()
        line_items_result = db.execute(line_items_query, {"jute_mr_id": jute_mr_id}).fetchall()
        row["line_items"] = [dict(r._mapping) for r in line_items_result]

        return row

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching Jute Gate Entry by ID")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jute_gate_entry_create_setup")
async def jute_gate_entry_create_setup(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get setup data for creating a Jute Gate Entry.
    Returns branches, suppliers, mukams, jute items, open POs, and UOM options.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        # Get branches
        branches_result = db.execute(get_branches_query(), {"co_id": co_id}).fetchall()
        branches = [dict(r._mapping) for r in branches_result]

        # Get mukams
        mukams_result = db.execute(get_mukam_list_query(), {"co_id": co_id}).fetchall()
        mukams = [dict(r._mapping) for r in mukams_result]

        # Get all jute suppliers
        suppliers_result = db.execute(get_all_suppliers_query(), {"co_id": co_id}).fetchall()
        suppliers = [dict(r._mapping) for r in suppliers_result]

        # Get jute items (where item_type_id = 2)
        jute_items_result = db.execute(get_jute_items_query(), {"co_id": co_id}).fetchall()
        jute_items = [dict(r._mapping) for r in jute_items_result]

        # Get open Jute POs for selection
        open_pos_result = db.execute(get_open_jute_pos_query(), {"co_id": co_id}).fetchall()
        open_pos = []
        for r in open_pos_result:
            po = dict(r._mapping)
            if po.get("po_date"):
                po["po_date"] = str(po["po_date"])
            open_pos.append(po)

        # Static UOM options for jute
        uom_options = [
            {"value": "LOOSE", "label": "Loose"},
            {"value": "BALE", "label": "Bale"},
        ]

        # Get vehicle types
        vehicle_types_result = db.execute(get_vehicle_types_query(), {"co_id": co_id}).fetchall()
        vehicle_types = [dict(r._mapping) for r in vehicle_types_result]

        return {
            "branches": branches,
            "mukams": mukams,
            "suppliers": suppliers,
            "jute_items": jute_items,
            "open_pos": open_pos,
            "uom_options": uom_options,
            "vehicle_types": vehicle_types,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching Jute Gate Entry create setup")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_parties_by_supplier/{supplier_id}")
async def get_parties_by_supplier(
    supplier_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Get parties mapped to a jute supplier."""
    try:
        query = get_parties_by_supplier_query()
        result = db.execute(query, {"supplier_id": supplier_id}).fetchall()
        parties = [dict(r._mapping) for r in result]
        
        return {"parties": parties}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching parties by supplier")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_qualities_by_item/{item_id}")
async def get_qualities_by_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Get jute qualities for a specific item."""
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        co_id = int(q_co_id)
        
        query = get_jute_qualities_by_item_query()
        result = db.execute(query, {"item_id": item_id, "co_id": co_id}).fetchall()
        qualities = [dict(r._mapping) for r in result]
        
        return {"qualities": qualities}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching qualities by item")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_po_details/{po_id}")
async def get_po_details(
    po_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get PO details and line items for auto-filling gate entry.
    When a PO is selected, this returns the PO header and line items.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        co_id = int(q_co_id)
        
        # Get PO header
        po_query = get_jute_po_for_gate_entry_query()
        po_result = db.execute(po_query, {"po_id": po_id, "co_id": co_id}).fetchone()
        
        if not po_result:
            raise HTTPException(status_code=404, detail="PO not found")
        
        po_data = dict(po_result._mapping)
        if po_data.get("po_date"):
            po_data["po_date"] = str(po_data["po_date"])
        
        # Get PO line items
        line_items_query = get_jute_po_line_items_for_gate_entry_query()
        line_items_result = db.execute(line_items_query, {"po_id": po_id}).fetchall()
        po_data["line_items"] = [dict(r._mapping) for r in line_items_result]
        
        return po_data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching PO details for gate entry")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# JUTE GATE ENTRY CREATE / UPDATE MODELS
# =============================================================================

class JuteGateEntryLineItemCreate(BaseModel):
    """Schema for a Jute Gate Entry line item.
    
    Updated 2026-01-14: Added jute_po_li_id and allowable_moisture.
    When PO is referenced, jute_po_li_id links to PO line and allowable_moisture is copied from PO.
    When no PO, allowable_moisture can be manually entered.
    """
    jute_po_li_id: Optional[int] = None
    challan_item_id: Optional[int] = None
    challan_jute_quality_id: Optional[int] = None
    challan_quantity: Optional[float] = None
    challan_weight: Optional[float] = None
    actual_item_id: Optional[int] = None
    actual_jute_quality_id: Optional[int] = None
    actual_quantity: Optional[float] = None
    actual_weight: Optional[float] = None
    allowable_moisture: Optional[float] = None
    jute_uom: Optional[str] = None
    remarks: Optional[str] = None


class JuteGateEntryCreate(BaseModel):
    """Schema for creating a Jute Gate Entry."""
    co_id: int
    branch_id: int
    jute_gate_entry_date: date
    in_time: Optional[str] = None  # Time string like "14:30"
    challan_no: str
    challan_date: date
    challan_weight: float
    vehicle_no: str
    driver_name: str
    transporter: str
    po_id: Optional[int] = None
    jute_uom: str  # LOOSE or BALE
    mukam_id: int
    jute_supplier_id: int
    party_id: Optional[int] = None
    gross_weight: float
    tare_weight: float
    net_weight: Optional[float] = None
    variable_shortage: Optional[float] = None
    vehicle_type_id: Optional[int] = None
    marketing_slip: Optional[int] = None  # 1 if checked, 0 if not
    remarks: Optional[str] = None
    line_items: List[JuteGateEntryLineItemCreate]


class JuteGateEntryUpdate(BaseModel):
    """Schema for updating a Jute Gate Entry (including OUT action)."""
    branch_id: Optional[int] = None
    jute_gate_entry_date: Optional[date] = None
    in_time: Optional[str] = None
    out_date: Optional[date] = None
    out_time: Optional[str] = None  # Time string like "16:45"
    challan_no: Optional[str] = None
    challan_date: Optional[date] = None
    challan_weight: Optional[float] = None
    vehicle_no: Optional[str] = None
    driver_name: Optional[str] = None
    transporter: Optional[str] = None
    po_id: Optional[int] = None
    jute_uom: Optional[str] = None
    mukam_id: Optional[int] = None
    jute_supplier_id: Optional[int] = None
    party_id: Optional[int] = None
    gross_weight: Optional[float] = None
    tare_weight: Optional[float] = None
    net_weight: Optional[float] = None
    variable_shortage: Optional[float] = None
    vehicle_type_id: Optional[int] = None
    marketing_slip: Optional[int] = None  # 1 if checked, 0 if not
    remarks: Optional[str] = None
    line_items: Optional[List[JuteGateEntryLineItemCreate]] = None
    action: Optional[str] = None  # "OUT" to mark vehicle exit


# =============================================================================
# JUTE GATE ENTRY CREATE / UPDATE ENDPOINTS
# =============================================================================

# Gate Entry Status IDs
GATE_ENTRY_STATUS_IN = 1  # "IN" - Vehicle has entered
GATE_ENTRY_STATUS_OUT = 5  # "OUT" - Vehicle has exited (Closed)


@router.post("/jute_gate_entry_create")
async def jute_gate_entry_create(
    payload: JuteGateEntryCreate,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Create a new Jute Gate Entry (IN action) and corresponding MR (Material Receipt)."""
    try:
        from src.models.jute import JuteGateEntry, JuteGateEntryLi, JuteMr, JuteMrLi
        
        user_id = token_data.get("user_id")
        username = token_data.get("username", "system")
        
        # Calculate financial year from jute_gate_entry_date
        # Financial year: April 1 to March 31
        # Example: January 20, 2025 → FY 2024-2025, April 15, 2025 → FY 2025-2026
        entry_date = payload.jute_gate_entry_date
        if entry_date.month >= 4:
            fy_start_year = entry_date.year
            fy_end_year = entry_date.year + 1
        else:
            fy_start_year = entry_date.year - 1
            fy_end_year = entry_date.year
        
        # Financial year starts on April 1 and ends on March 31
        fy_start_date = date(fy_start_year, 4, 1)
        fy_end_date = date(fy_end_year, 3, 31)
        
        # Generate entry sequence (get max branch_gate_entry_no for branch + financial year and increment)
        max_seq_result = db.execute(
            text("""
                SELECT COALESCE(MAX(branch_gate_entry_no), 0) + 1 AS next_seq 
                FROM jute_gate_entry 
                WHERE branch_id = :branch_id 
                  AND DATE(jute_gate_entry_date) >= :fy_start 
                  AND DATE(jute_gate_entry_date) <= :fy_end
            """),
            {
                "branch_id": payload.branch_id,
                "fy_start": fy_start_date,
                "fy_end": fy_end_date
            }
        ).fetchone()
        next_seq = max_seq_result.next_seq if max_seq_result else 1
        
        # Calculate weights:
        # net_weight = gross_weight - tare_weight
        # actual_weight = net_weight - variable_shortage
        net_weight = payload.gross_weight - payload.tare_weight
        variable_shortage = payload.variable_shortage if payload.variable_shortage is not None else 0
        actual_weight = net_weight - variable_shortage
        
        # Parse in_time
        in_time_dt = None
        if payload.in_time:
            try:
                time_parts = payload.in_time.split(":")
                in_time_dt = datetime.combine(
                    payload.jute_gate_entry_date,
                    time(int(time_parts[0]), int(time_parts[1]))
                )
            except (ValueError, IndexError):
                in_time_dt = datetime.now()
        else:
            in_time_dt = datetime.now()
        
        # Create header
        gate_entry = JuteGateEntry(
            branch_gate_entry_no=next_seq,
            branch_id=payload.branch_id,
            jute_gate_entry_date=datetime.combine(payload.jute_gate_entry_date, time(0, 0)),
            in_time=in_time_dt,
            challan_no=payload.challan_no,
            challan_date=datetime.combine(payload.challan_date, time(0, 0)),
            challan_weight=payload.challan_weight,
            vehicle_no=payload.vehicle_no,
            driver_name=payload.driver_name,
            transporter=payload.transporter,
            po_id=payload.po_id,
            unit_conversion=payload.jute_uom,
            mukam_id=payload.mukam_id,
            jute_supplier_id=payload.jute_supplier_id,
            party_id=payload.party_id,
            gross_weight=payload.gross_weight,
            tare_weight=payload.tare_weight,
            net_weight=net_weight,
            variable_shortage=variable_shortage,
            actual_weight=actual_weight,
            vehicle_type_id=payload.vehicle_type_id,
            marketing_slip=payload.marketing_slip or 0,
            remarks=payload.remarks,
            status_id=GATE_ENTRY_STATUS_IN,  # IN status
            qc_check="N",
            updated_by=user_id,
            updated_date_time=datetime.now(),
        )
        
        db.add(gate_entry)
        db.flush()  # Get the generated ID
        
        # Create line items and collect them for MR creation
        gate_entry_line_items = []
        total_actual_weight = 0.0
        for li in payload.line_items:
            line_item = JuteGateEntryLi(
                jute_gate_entry_id=gate_entry.jute_gate_entry_id,
                jute_po_li_id=li.jute_po_li_id,  # Reference to PO line item if PO is selected
                challan_item_id=li.challan_item_id,
                challan_jute_quality_id=li.challan_jute_quality_id,
                challan_quantity=li.challan_quantity,
                challan_weight=li.challan_weight,
                actual_item_id=li.actual_item_id,
                actual_jute_quality_id=li.actual_jute_quality_id,
                actual_quantity=li.actual_quantity,
                actual_weight=li.actual_weight,
                allowable_moisture=li.allowable_moisture,  # From PO or manually entered
                jute_uom=li.jute_uom or payload.jute_uom,
                remarks=li.remarks,
                active=1,
                updated_by=user_id,
                updated_date_time=datetime.now(),
            )
            db.add(line_item)
            db.flush()  # Get the generated line item ID
            gate_entry_line_items.append(line_item)
            total_actual_weight += float(li.actual_weight or 0)
        
        # =============================================================================
        # CREATE JUTE MR (Material Receipt) FROM GATE ENTRY
        # =============================================================================
        # MR status: 21 = Drafted
        MR_STATUS_DRAFTED = 21
        
        # MR number will be generated later when MR is processed/approved
        # At gate entry stage, MR is created without mr_no and mr_date
        
        # Create MR header
        jute_mr = JuteMr(
            branch_id=payload.branch_id,
            branch_mr_no=None,  # Will be generated later
            jute_mr_date=None,  # Will be set later
            jute_gate_entry_id=gate_entry.jute_gate_entry_id,
            jute_gate_entry_date=payload.jute_gate_entry_date,
            challan_no=payload.challan_no,
            challan_date=payload.challan_date,
            jute_supplier_id=payload.jute_supplier_id,
            party_id=str(payload.party_id) if payload.party_id else None,
            mukam_id=payload.mukam_id,
            unit_conversion=payload.jute_uom,
            po_id=payload.po_id,
            mr_weight=total_actual_weight,  # Sum of line item actual weights
            vehicle_no=payload.vehicle_no,
            status_id=MR_STATUS_DRAFTED,
            remarks=payload.remarks,
            src_com_id=payload.co_id,  # Source company from which gate entry was done
            updated_by=user_id,
            updated_date_time=datetime.now(),
        )
        db.add(jute_mr)
        db.flush()  # Get the generated MR ID
        
        # Create MR line items
        for ge_li in gate_entry_line_items:
            mr_line_item = JuteMrLi(
                jute_mr_id=jute_mr.jute_mr_id,
                jute_gate_entry_lineitem_id=ge_li.jute_gate_entry_li_id,
                challan_item_id=ge_li.challan_item_id,
                challan_quality_id=ge_li.challan_jute_quality_id,
                challan_quantity=ge_li.challan_quantity,
                challan_weight=ge_li.challan_weight,
                actual_item_id=ge_li.actual_item_id,
                actual_quality=ge_li.actual_jute_quality_id,
                actual_qty=ge_li.actual_quantity,
                actual_weight=ge_li.actual_weight,
                remarks=ge_li.remarks,
                active=1,
                updated_date_time=datetime.now(),
            )
            db.add(mr_line_item)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Jute Gate Entry and MR created successfully",
            "jute_gate_entry_id": gate_entry.jute_gate_entry_id,
            "branch_gate_entry_no": next_seq,
            "jute_mr_id": jute_mr.jute_mr_id,
            "net_weight": net_weight,
            "actual_weight": actual_weight,
            "mr_weight": total_actual_weight,
            "status": "IN",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error creating Jute Gate Entry")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/jute_gate_entry_update/{jute_gate_entry_id}")
async def jute_gate_entry_update(
    jute_gate_entry_id: int,
    payload: JuteGateEntryUpdate,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Update a Jute Gate Entry. Use action='OUT' to mark vehicle exit."""
    try:
        from src.models.jute import JuteGateEntry, JuteGateEntryLi
        
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        co_id = int(q_co_id)
        user_id = token_data.get("user_id")
        username = token_data.get("username", "system")
        
        # Get existing gate entry
        existing = db.execute(
            text("""
                SELECT jge.jute_gate_entry_id, jge.status_id, jge.in_time
                FROM jute_gate_entry jge
                INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
                WHERE jge.jute_gate_entry_id = :id AND bm.co_id = :co_id
            """),
            {"id": jute_gate_entry_id, "co_id": co_id}
        ).fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Jute Gate Entry not found")
        
        # Handle OUT action
        if payload.action and payload.action.upper() == "OUT":
            if not payload.out_time:
                raise HTTPException(status_code=400, detail="out_time is required for OUT action")
            
            # Validate out_time > in_time
            out_date = payload.out_date or date.today()
            try:
                time_parts = payload.out_time.split(":")
                out_time_dt = datetime.combine(out_date, time(int(time_parts[0]), int(time_parts[1])))
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Invalid out_time format. Use HH:MM")
            
            in_time_dt = existing.in_time
            if in_time_dt and out_time_dt <= in_time_dt:
                raise HTTPException(status_code=400, detail="Out date/time must be after In date/time")
            
            # Update out date/time only (status remains unchanged - stays as OPEN/IN)
            db.execute(
                text("""
                    UPDATE jute_gate_entry
                    SET out_date = :out_date, out_time = :out_time,
                        updated_by = :user_id, updated_date_time = :updated_dt
                    WHERE jute_gate_entry_id = :id
                """),
                {
                    "out_date": datetime.combine(out_date, time(0, 0)),
                    "out_time": out_time_dt,
                    "user_id": user_id,
                    "updated_dt": datetime.now(),
                    "id": jute_gate_entry_id,
                }
            )
            db.commit()
            
            return {
                "success": True,
                "message": "Vehicle marked as OUT successfully",
                "jute_gate_entry_id": jute_gate_entry_id,
            }
        
        # Regular update (not OUT action)
        update_fields = []
        update_params = {"id": jute_gate_entry_id, "user_id": user_id, "updated_dt": datetime.now()}
        
        if payload.branch_id is not None:
            update_fields.append("branch_id = :branch_id")
            update_params["branch_id"] = payload.branch_id
        
        if payload.jute_gate_entry_date is not None:
            update_fields.append("jute_gate_entry_date = :entry_date")
            update_params["entry_date"] = datetime.combine(payload.jute_gate_entry_date, time(0, 0))
        
        if payload.in_time is not None:
            try:
                time_parts = payload.in_time.split(":")
                in_time_dt = datetime.combine(
                    payload.jute_gate_entry_date or date.today(),
                    time(int(time_parts[0]), int(time_parts[1]))
                )
                update_fields.append("in_time = :in_time")
                update_params["in_time"] = in_time_dt
            except (ValueError, IndexError):
                pass
        
        if payload.challan_no is not None:
            update_fields.append("challan_no = :challan_no")
            update_params["challan_no"] = payload.challan_no
        
        if payload.challan_date is not None:
            update_fields.append("challan_date = :challan_date")
            update_params["challan_date"] = datetime.combine(payload.challan_date, time(0, 0))
        
        if payload.challan_weight is not None:
            update_fields.append("challan_weight = :challan_weight")
            update_params["challan_weight"] = payload.challan_weight
        
        if payload.vehicle_no is not None:
            update_fields.append("vehicle_no = :vehicle_no")
            update_params["vehicle_no"] = payload.vehicle_no
        
        if payload.driver_name is not None:
            update_fields.append("driver_name = :driver_name")
            update_params["driver_name"] = payload.driver_name
        
        if payload.transporter is not None:
            update_fields.append("transporter = :transporter")
            update_params["transporter"] = payload.transporter
        
        if payload.po_id is not None:
            update_fields.append("po_id = :po_id")
            update_params["po_id"] = payload.po_id
        
        if payload.jute_uom is not None:
            update_fields.append("unit_conversion = :jute_uom")
            update_params["jute_uom"] = payload.jute_uom
        
        if payload.mukam_id is not None:
            update_fields.append("mukam_id = :mukam_id")
            update_params["mukam_id"] = payload.mukam_id
        
        if payload.jute_supplier_id is not None:
            update_fields.append("jute_supplier_id = :supplier_id")
            update_params["supplier_id"] = payload.jute_supplier_id
        
        if payload.party_id is not None:
            update_fields.append("party_id = :party_id")
            update_params["party_id"] = payload.party_id
        
        if payload.gross_weight is not None:
            update_fields.append("gross_weight = :gross_weight")
            update_params["gross_weight"] = payload.gross_weight
        
        if payload.tare_weight is not None:
            update_fields.append("tare_weight = :tare_weight")
            update_params["tare_weight"] = payload.tare_weight
        
        if payload.net_weight is not None:
            update_fields.append("net_weight = :net_weight")
            update_params["net_weight"] = payload.net_weight
        elif payload.gross_weight is not None and payload.tare_weight is not None:
            # Auto-calculate net_weight = gross - tare
            update_fields.append("net_weight = :net_weight")
            update_params["net_weight"] = payload.gross_weight - payload.tare_weight
        
        if payload.variable_shortage is not None:
            update_fields.append("variable_shortage = :variable_shortage")
            update_params["variable_shortage"] = payload.variable_shortage
            # Recalculate actual_weight = net_weight - variable_shortage
            # Get net_weight from payload or existing record
            if "net_weight" in update_params:
                net_wt = update_params["net_weight"]
            elif payload.gross_weight is not None and payload.tare_weight is not None:
                net_wt = payload.gross_weight - payload.tare_weight
            else:
                # Fetch existing net_weight from DB
                existing = db.execute(
                    text("SELECT net_weight FROM jute_gate_entry WHERE jute_gate_entry_id = :id"),
                    {"id": jute_gate_entry_id}
                ).fetchone()
                net_wt = existing.net_weight if existing and existing.net_weight else 0
            update_fields.append("actual_weight = :actual_weight")
            update_params["actual_weight"] = net_wt - payload.variable_shortage
        
        if payload.vehicle_type_id is not None:
            update_fields.append("vehicle_type_id = :vehicle_type_id")
            update_params["vehicle_type_id"] = payload.vehicle_type_id
        
        if payload.marketing_slip is not None:
            update_fields.append("marketing_slip = :marketing_slip")
            update_params["marketing_slip"] = payload.marketing_slip
        
        if payload.remarks is not None:
            update_fields.append("remarks = :remarks")
            update_params["remarks"] = payload.remarks
        
        update_fields.append("updated_by = :user_id")
        update_fields.append("updated_date_time = :updated_dt")
        
        if update_fields:
            update_sql = f"UPDATE jute_gate_entry SET {', '.join(update_fields)} WHERE jute_gate_entry_id = :id"
            db.execute(text(update_sql), update_params)
        
        # Update line items if provided
        if payload.line_items is not None:
            # Delete existing line items
            db.execute(
                text("DELETE FROM jute_gate_entry_li WHERE jute_gate_entry_id = :id"),
                {"id": jute_gate_entry_id}
            )
            
            # Insert new line items and track for MR update
            total_actual_weight = 0.0
            new_ge_line_items = []
            for li in payload.line_items:
                line_item = JuteGateEntryLi(
                    jute_gate_entry_id=jute_gate_entry_id,
                    challan_item_id=li.challan_item_id,
                    challan_jute_quality_id=li.challan_jute_quality_id,
                    challan_quantity=li.challan_quantity,
                    challan_weight=li.challan_weight,
                    actual_item_id=li.actual_item_id,
                    actual_jute_quality_id=li.actual_jute_quality_id,
                    actual_quantity=li.actual_quantity,
                    actual_weight=li.actual_weight,
                    jute_uom=li.jute_uom,
                    remarks=li.remarks,
                    active=1,
                    updated_by=user_id,
                    updated_date_time=datetime.now(),
                )
                db.add(line_item)
                db.flush()  # Get the generated ID
                new_ge_line_items.append(line_item)
                total_actual_weight += float(li.actual_weight or 0)
            
            # Update MR records linked to this gate entry
            # Find the MR for this gate entry
            mr_result = db.execute(
                text("SELECT jute_mr_id FROM jute_mr WHERE jute_gate_entry_id = :ge_id"),
                {"ge_id": jute_gate_entry_id}
            ).fetchone()
            
            if mr_result:
                mr_id = mr_result.jute_mr_id
                
                # Update MR weight (sum of line item actual weights)
                db.execute(
                    text("""
                        UPDATE jute_mr 
                        SET mr_weight = :mr_weight, updated_date_time = :updated_dt 
                        WHERE jute_mr_id = :mr_id
                    """),
                    {"mr_weight": total_actual_weight, "updated_dt": datetime.now(), "mr_id": mr_id}
                )
                
                # Delete existing MR line items
                db.execute(
                    text("DELETE FROM jute_mr_li WHERE jute_mr_id = :mr_id"),
                    {"mr_id": mr_id}
                )
                
                # Insert new MR line items
                from src.models.jute import JuteMrLi
                for ge_li in new_ge_line_items:
                    mr_line_item = JuteMrLi(
                        jute_mr_id=mr_id,
                        jute_gate_entry_lineitem_id=ge_li.jute_gate_entry_li_id,
                        challan_item_id=ge_li.challan_item_id,
                        challan_quality_id=ge_li.challan_jute_quality_id,
                        challan_quantity=ge_li.challan_quantity,
                        challan_weight=ge_li.challan_weight,
                        actual_item_id=ge_li.actual_item_id,
                        actual_quality=ge_li.actual_jute_quality_id,
                        actual_qty=ge_li.actual_quantity,
                        actual_weight=ge_li.actual_weight,
                        remarks=ge_li.remarks,
                        active=1,
                        updated_date_time=datetime.now(),
                    )
                    db.add(mr_line_item)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Jute Gate Entry updated successfully",
            "jute_gate_entry_id": jute_gate_entry_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error updating Jute Gate Entry")
        raise HTTPException(status_code=500, detail=str(e))
