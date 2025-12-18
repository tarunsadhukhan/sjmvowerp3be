import logging
from fastapi import Depends, Request, HTTPException, APIRouter
from sqlalchemy.orm import Session
from typing import Optional
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.procurement.query import (
    get_inward_table_query,
    get_inward_table_count_query,
)
from src.procurement.indent import calculate_financial_year

logger = logging.getLogger(__name__)

router = APIRouter()


def format_inward_no(
    inward_sequence_no: Optional[int],
    co_prefix: Optional[str],
    branch_prefix: Optional[str],
    inward_date,
) -> str:
    """Format Inward/GRN number as 'co_prefix/branch_prefix/GRN/financial_year/sequence_no'."""
    if inward_sequence_no is None or inward_sequence_no == 0:
        return ""
    
    fy = calculate_financial_year(inward_date)
    co_pref = co_prefix or ""
    branch_pref = branch_prefix or ""
    
    parts = []
    if co_pref:
        parts.append(co_pref)
    if branch_pref:
        parts.append(branch_pref)
    parts.extend(["GRN", fy, str(inward_sequence_no)])
    
    return "/".join(parts)


def format_po_no(
    po_no: Optional[int],
    co_prefix: Optional[str],
    branch_prefix: Optional[str],
    po_date,
) -> str:
    """Format PO number as 'co_prefix/branch_prefix/PO/financial_year/po_no'."""
    if po_no is None or po_no == 0:
        return ""
    
    fy = calculate_financial_year(po_date)
    co_pref = co_prefix or ""
    branch_pref = branch_prefix or ""
    
    parts = []
    if co_pref:
        parts.append(co_pref)
    if branch_pref:
        parts.append(branch_pref)
    parts.extend(["PO", fy, str(po_no)])
    
    return "/".join(parts)


@router.get("/get_inward_table")
async def get_inward_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
    co_id: int | None = None,
):
    """Return paginated procurement inward/GRN list."""

    try:
        page = max(page, 1)
        limit = max(min(limit, 100), 1)
        offset = (page - 1) * limit
        search_like = None
        if search:
            search_like = f"%{search.strip()}%"

        params = {
            "co_id": co_id,
            "search_like": search_like,
            "limit": limit,
            "offset": offset,
        }

        list_query = get_inward_table_query()
        rows = db.execute(list_query, params).fetchall()
        data = []
        for row in rows:
            mapped = dict(row._mapping)
            
            # Format inward date
            inward_date_obj = mapped.get("inward_date")
            inward_date = inward_date_obj
            if hasattr(inward_date_obj, "isoformat"):
                inward_date = inward_date_obj.isoformat()
            
            # Format GRN/Inward number
            raw_inward_no = mapped.get("inward_sequence_no")
            formatted_inward_no = ""
            if raw_inward_no is not None and raw_inward_no != 0:
                try:
                    inward_no_int = int(raw_inward_no) if raw_inward_no else None
                    co_prefix = mapped.get("co_prefix")
                    branch_prefix = mapped.get("branch_prefix")
                    formatted_inward_no = format_inward_no(
                        inward_sequence_no=inward_no_int,
                        co_prefix=co_prefix,
                        branch_prefix=branch_prefix,
                        inward_date=inward_date_obj,
                    )
                except Exception as e:
                    logger.exception("Error formatting Inward number in list, using raw value")
                    formatted_inward_no = str(raw_inward_no) if raw_inward_no else ""
            
            # Format PO number
            raw_po_no = mapped.get("po_no")
            po_date_obj = mapped.get("po_date")
            formatted_po_no = ""
            if raw_po_no is not None and raw_po_no != 0:
                try:
                    po_no_int = int(raw_po_no) if raw_po_no else None
                    co_prefix = mapped.get("co_prefix")
                    branch_prefix = mapped.get("branch_prefix")
                    formatted_po_no = format_po_no(
                        po_no=po_no_int,
                        co_prefix=co_prefix,
                        branch_prefix=branch_prefix,
                        po_date=po_date_obj,
                    )
                except Exception as e:
                    logger.exception("Error formatting PO number in inward list, using raw value")
                    formatted_po_no = str(raw_po_no) if raw_po_no else ""
            
            data.append(
                {
                    "inward_id": mapped.get("inward_id"),
                    "inward_no": formatted_inward_no,
                    "inward_date": inward_date,
                    "branch_id": mapped.get("branch_id"),
                    "branch_name": mapped.get("branch_name") or "",
                    "po_id": mapped.get("po_id"),
                    "po_no": formatted_po_no,
                    "supplier_id": mapped.get("supplier_id"),
                    "supplier_name": mapped.get("supplier_name") or "",
                    "status": mapped.get("status_name") or "Pending",
                }
            )

        count_query = get_inward_table_count_query()
        count_result = db.execute(count_query, params).scalar()
        total = int(count_result) if count_result is not None else 0

        return {"data": data, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching Inward table")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
