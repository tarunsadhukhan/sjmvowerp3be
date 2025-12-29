import logging
from fastapi import Depends, Request, HTTPException, APIRouter
from sqlalchemy.orm import Session
from typing import Optional
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.procurement.query import (
    get_inward_table_query,
    get_inward_table_count_query,
    get_suppliers_with_party_type_1,
    get_supplier_branches,
    get_item_by_group_id_purchaseable,
    get_item_make_by_group_id,
    get_item_uom_by_group_id,
    get_approved_pos_by_supplier_query,
    get_po_line_items_for_inward_query,
)
from src.masters.query import get_item_group_drodown, get_branch_list
from src.common.companyAdmin.query import get_co_config_by_id_query
from src.procurement.indent import calculate_financial_year
from src.procurement.po import format_po_no, extract_formatted_po_no

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
            
            # Format PO number using helper
            formatted_po_no = extract_formatted_po_no(mapped)
            
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


@router.get("/get_inward_setup_1")
async def get_inward_setup_1(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    branch_id: int | None = None,
    co_id: int | None = None,
):
    """Return suppliers, item_groups, and co_config for inward/GRN creation."""
    try:
        # Get query parameters
        q_branch_id = request.query_params.get("branch_id")
        q_co_id = request.query_params.get("co_id")
        if q_branch_id is not None:
            try:
                branch_id = int(q_branch_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid branch_id")
        if q_co_id is not None:
            try:
                co_id = int(q_co_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid co_id")

        if co_id is None:
            raise HTTPException(status_code=400, detail="co_id is required")

        # Branches
        branch_ids_list = [branch_id] if branch_id is not None else None
        branchquery = get_branch_list(branch_ids=branch_ids_list) if branch_ids_list else get_branch_list()
        branch_result = db.execute(branchquery, {"branch_ids": branch_ids_list} if branch_ids_list else {}).fetchall()
        branches = [dict(r._mapping) for r in branch_result]

        # Suppliers (party_type_id contains 1)
        supplier_query = get_suppliers_with_party_type_1(co_id=co_id)
        supplier_result = db.execute(supplier_query, {"co_id": co_id}).fetchall()
        suppliers = [dict(r._mapping) for r in supplier_result]

        # Add branches to each supplier
        for supplier in suppliers:
            supplier_id = supplier.get("party_id")
            if supplier_id:
                try:
                    supplier_branch_query = get_supplier_branches(party_id=supplier_id)
                    supplier_branch_result = db.execute(supplier_branch_query, {"party_id": supplier_id}).fetchall()
                    supplier["branches"] = [dict(r._mapping) for r in supplier_branch_result]
                except Exception as e:
                    logger.exception(f"Error fetching branches for supplier {supplier_id}")
                    supplier["branches"] = []

        # Item groups
        itemgrp_query = get_item_group_drodown(co_id=co_id)
        itemgrp_result = db.execute(itemgrp_query, {"co_id": co_id}).fetchall()
        item_groups = [dict(r._mapping) for r in itemgrp_result]

        # Co config
        co_config_query = get_co_config_by_id_query(co_id)
        co_config_result = db.execute(co_config_query, {"co_id": co_id}).fetchone()
        co_config = dict(co_config_result._mapping) if co_config_result else {}

        return {
            "branches": branches,
            "suppliers": suppliers,
            "item_groups": item_groups,
            "co_config": co_config,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching inward setup 1")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/get_inward_setup_2")
async def get_inward_setup_2(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    item_group: int | None = None,
):
    """Return items, makes, and UOMs for a given item group (for manual line item entry)."""
    try:
        q_item_group = request.query_params.get("item_group")
        if q_item_group is not None:
            try:
                item_group = int(q_item_group)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid item_group")

        if item_group is None:
            raise HTTPException(status_code=400, detail="item_group is required")

        # Items for the group
        items_query = get_item_by_group_id_purchaseable(item_group_id=item_group)
        items_result = db.execute(items_query, {"item_group_id": item_group}).fetchall()
        items = [dict(r._mapping) for r in items_result]

        # Makes for the group
        makes_query = get_item_make_by_group_id(item_group_id=item_group)
        makes_result = db.execute(makes_query, {"item_group_id": item_group}).fetchall()
        makes = [dict(r._mapping) for r in makes_result]

        # UOMs for the group
        uom_query = get_item_uom_by_group_id(item_group_id=item_group)
        uom_result = db.execute(uom_query, {"item_group_id": item_group}).fetchall()
        uoms = [dict(r._mapping) for r in uom_result]

        return {
            "items": items,
            "makes": makes,
            "uoms": uoms,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching inward setup 2")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/get_approved_pos_by_supplier")
async def get_approved_pos_by_supplier(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    supplier_id: int | None = None,
    branch_id: int | None = None,
):
    """
    Return approved POs for a specific supplier that have pending items to receive.
    Used in Inward/GRN creation to select from which PO to receive goods.
    
    Parameters:
    - supplier_id (required): Filter by supplier
    - branch_id (optional): Filter by branch
    - status_id = 3 (hardcoded in query): Only approved POs
    """
    try:
        # Parse query parameters
        q_supplier_id = request.query_params.get("supplier_id")
        q_branch_id = request.query_params.get("branch_id")

        if q_supplier_id is not None:
            try:
                supplier_id = int(q_supplier_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid supplier_id")

        if q_branch_id is not None:
            try:
                branch_id = int(q_branch_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid branch_id")

        if supplier_id is None:
            raise HTTPException(status_code=400, detail="supplier_id is required")

        params = {
            "supplier_id": supplier_id,
            "branch_id": branch_id,
        }

        query = get_approved_pos_by_supplier_query()
        rows = db.execute(query, params).fetchall()

        data = []
        for row in rows:
            mapped = dict(row._mapping)

            # Format PO date
            po_date_obj = mapped.get("po_date")
            po_date_str = po_date_obj.isoformat() if hasattr(po_date_obj, "isoformat") else str(po_date_obj) if po_date_obj else ""

            # Format PO number using helper
            formatted_po_no = extract_formatted_po_no(mapped)

            data.append({
                "po_id": mapped.get("po_id"),
                "po_no": formatted_po_no,
                "po_date": po_date_str,
                "branch_id": mapped.get("branch_id"),
                "branch_name": mapped.get("branch_name") or "",
                "supplier_id": mapped.get("supplier_id"),
                "supplier_name": mapped.get("supplier_name") or "",
            })

        return {"data": data, "total": len(data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching approved POs by supplier")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/get_po_line_items")
async def get_po_line_items(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    po_id: int | None = None,
):
    """
    Return PO line items for inward/GRN entry with pending quantities.
    Only returns items with pending_qty > 0 (ordered - already received).
    """
    try:
        q_po_id = request.query_params.get("po_id")
        if q_po_id is not None:
            try:
                po_id = int(q_po_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid po_id")

        if po_id is None:
            raise HTTPException(status_code=400, detail="po_id is required")

        query = get_po_line_items_for_inward_query()
        rows = db.execute(query, {"po_id": po_id}).fetchall()

        line_items = []
        for row in rows:
            mapped = dict(row._mapping)

            # Format PO number using helper
            formatted_po_no = extract_formatted_po_no(mapped)

            line_items.append({
                "po_dtl_id": mapped.get("po_dtl_id"),
                "po_id": mapped.get("po_id"),
                "po_no": formatted_po_no,
                "item_id": mapped.get("item_id"),
                "item_code": mapped.get("item_code") or "",
                "item_name": mapped.get("item_name") or "",
                "item_grp_id": mapped.get("item_grp_id"),
                "item_grp_code": mapped.get("item_grp_code") or "",
                "item_grp_name": mapped.get("item_grp_name") or "",
                "item_make_id": mapped.get("item_make_id"),
                "item_make_name": mapped.get("item_make_name") or "",
                "ordered_qty": mapped.get("ordered_qty") or 0,
                "received_qty": mapped.get("received_qty") or 0,
                "pending_qty": mapped.get("pending_qty") or 0,
                "uom_id": mapped.get("uom_id"),
                "uom_name": mapped.get("uom_name") or "",
                "rate": mapped.get("rate") or 0,
                "amount": mapped.get("amount") or 0,
                "remarks": mapped.get("remarks") or "",
                "tax_percentage": mapped.get("tax_percentage"),
            })

        return {
            "po_id": po_id,
            "line_items": line_items,
            "total": len(line_items),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching PO line items for inward")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# from fastapi import Depends, Request, HTTPException, APIRouter
# import logging
# from sqlalchemy.orm import Session
# from typing import Optional
# from src.config.db import get_tenant_db
# from src.authorization.utils import get_current_user_with_refresh
# from src.procurement.query import (
# 	get_inward_table_query,
# 	get_inward_table_count_query,
# )
# from src.procurement.indent import (
# 	format_indent_no,
# 	calculate_financial_year,
# )

# logger = logging.getLogger(__name__)

# router = APIRouter()


# def format_inward_no(
# 	inward_sequence_no: Optional[int],
# 	co_prefix: Optional[str],
# 	branch_prefix: Optional[str],
# 	inward_date,
# ) -> str:
# 	"""Format inward number as 'co_prefix/branch_prefix/INW/financial_year/inward_sequence_no'."""
# 	if inward_sequence_no is None or inward_sequence_no == 0:
# 		return ""
	
# 	fy = calculate_financial_year(inward_date)
# 	co_pref = co_prefix or ""
# 	branch_pref = branch_prefix or ""
	
# 	parts = []
# 	if co_pref:
# 		parts.append(co_pref)
# 	if branch_pref:
# 		parts.append(branch_pref)
# 	parts.extend(["INW", fy, str(inward_sequence_no)])
	
# 	return "/".join(parts)


# def format_po_no(
# 	po_no: Optional[int],
# 	co_prefix: Optional[str],
# 	branch_prefix: Optional[str],
# 	po_date,
# ) -> str:
# 	"""Format PO number as 'co_prefix/branch_prefix/PO/financial_year/po_no'."""
# 	if po_no is None or po_no == 0:
# 		return ""
	
# 	fy = calculate_financial_year(po_date)
# 	co_pref = co_prefix or ""
# 	branch_pref = branch_prefix or ""
	
# 	parts = []
# 	if co_pref:
# 		parts.append(co_pref)
# 	if branch_pref:
# 		parts.append(branch_pref)
# 	parts.extend(["PO", fy, str(po_no)])
	
# 	return "/".join(parts)


# @router.get("/get_inward_table")
# async def get_inward_table(
# 	request: Request,
# 	db: Session = Depends(get_tenant_db),
# 	token_data: dict = Depends(get_current_user_with_refresh),
# 	page: int = 1,
# 	limit: int = 10,
# 	search: str | None = None,
# 	co_id: int | None = None,
# ):
# 	"""Return paginated inward list."""
# 	try:
# 		page = max(page, 1)
# 		limit = max(min(limit, 100), 1)
# 		offset = (page - 1) * limit
# 		search_like = None
# 		if search:
# 			search_like = f"%{search.strip()}%"

# 		params = {
# 			"co_id": co_id,
# 			"search_like": search_like,
# 			"limit": limit,
# 			"offset": offset,
# 		}

# 		list_query = get_inward_table_query()
# 		rows = db.execute(list_query, params).fetchall()
# 		data = []
# 		for row in rows:
# 			mapped = dict(row._mapping)
# 			inward_date_obj = mapped.get("inward_date")
# 			inward_date = inward_date_obj
# 			if hasattr(inward_date_obj, "isoformat"):
# 				inward_date = inward_date_obj.isoformat()

# 			# Format inward_no
# 			raw_inward_no = mapped.get("inward_sequence_no")
# 			formatted_inward_no = ""
# 			if raw_inward_no is not None and raw_inward_no != 0:
# 				try:
# 					inward_no_int = int(raw_inward_no) if raw_inward_no else None
# 					co_prefix = mapped.get("co_prefix")
# 					branch_prefix = mapped.get("branch_prefix")
# 					formatted_inward_no = format_inward_no(
# 						inward_sequence_no=inward_no_int,
# 						co_prefix=co_prefix,
# 						branch_prefix=branch_prefix,
# 						inward_date=inward_date_obj,
# 					)
# 				except Exception as e:
# 					logger.exception("Error formatting inward number, using raw value")
# 					formatted_inward_no = str(raw_inward_no) if raw_inward_no else ""

# 			# Format po_no
# 			raw_po_no = mapped.get("po_no")
# 			po_date_obj = mapped.get("po_date")
# 			formatted_po_no = ""
# 			if raw_po_no is not None and raw_po_no != 0:
# 				try:
# 					po_no_int = int(raw_po_no) if raw_po_no else None
# 					co_prefix = mapped.get("co_prefix")
# 					branch_prefix = mapped.get("branch_prefix")
# 					formatted_po_no = format_po_no(
# 						po_no=po_no_int,
# 						co_prefix=co_prefix,
# 						branch_prefix=branch_prefix,
# 						po_date=po_date_obj,
# 					)
# 				except Exception as e:
# 					logger.exception("Error formatting PO number, using raw value")
# 					formatted_po_no = str(raw_po_no) if raw_po_no else ""

# 			data.append(
# 				{
# 					"inward_id": mapped.get("inward_id"),
# 					"inward_no": formatted_inward_no,
# 					"inward_date": inward_date,
# 					"branch_name": mapped.get("branch_name") or "",
# 					"po_no": formatted_po_no,
# 					"supplier_name": mapped.get("supplier_name") or "",
# 					"status": mapped.get("status_name") or "Pending",
# 				}
# 			)

# 		count_query = get_inward_table_count_query()
# 		count_result = db.execute(count_query, params).scalar()
# 		total = int(count_result) if count_result is not None else 0

# 		return {"data": data, "total": total}
# 	except HTTPException:
# 		raise
# 	except Exception as e:
# 		logger.exception("Error fetching inward table")
# 		raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
