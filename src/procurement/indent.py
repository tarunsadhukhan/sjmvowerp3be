from fastapi import Depends, Request, HTTPException, APIRouter
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from src.config.db import get_db_names, default_engine, get_tenant_db
from src.authorization.utils import  get_current_user_with_refresh
# from src.masters.schemas import MenuResponse
from src.masters.models import CostFactorMst
from src.masters.query import  get_branch_list, get_dept_list_by_branch_id, get_item_group_drodown
from src.procurement.query import (
	get_project,
	get_expense_types,
	get_item_by_group_id_purchaseable,
	get_item_make_by_group_id,
	get_item_uom_by_group_id,
	insert_proc_indent,
	insert_proc_indent_detail,
	get_indent_table_query,
	get_indent_table_count_query,
	get_indent_by_id_query,
	get_indent_detail_by_id_query,
	update_proc_indent,
	delete_proc_indent_detail,
	get_approval_flow_by_menu_branch,
	get_user_approval_level,
	get_max_approval_level,
	get_user_consumed_amounts,
	update_indent_status,
	get_indent_with_approval_info,
	check_approval_mst_exists,
	get_user_edit_access,
	get_max_indent_no_for_branch_fy,
	get_all_approved_indents_query,
	get_item_validation_data,
	get_item_fy_indent_check,
	get_item_regular_bom_outstanding,
	get_expense_type_name_by_id,
)
from src.procurement.constants import (
	INDENT_TYPES,
	VALID_INDENT_TYPE_VALUES,
	normalize_indent_type,
	is_valid_indent_type,
)
from datetime import datetime, date
from typing import Optional
import math

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

# Mapping: (indent_type, expense_type_name) -> validation logic
# Logic 1: Max/Min Quantity Validation with Stock Check
# Logic 2: Open Entry Validation with Financial Year Check
# Logic 3: No Validation (Capital/Overhaul)
VALIDATION_LOGIC_MAP = {
    # Regular indent
    ("Regular", "General"): 1,
    ("Regular", "Maintenance"): 1,
    ("Regular", "Production"): 1,
    ("Regular", "Overhaul"): 1,
    ("Regular", "Capital"): 3,
    # Open indent
    ("Open", "General"): 2,
    ("Open", "Maintenance"): 2,
    ("Open", "Production"): 2,
    # BOM indent
    ("BOM", "General"): 1,
    ("BOM", "Maintenance"): 1,
    ("BOM", "Production"): 1,
    ("BOM", "Capital"): 3,
    ("BOM", "Overhaul"): 3,
}


def determine_validation_logic(indent_type: str, expense_type_name: str) -> int:
    """Determine which validation logic applies based on indent type + expense type."""
    return VALIDATION_LOGIC_MAP.get((indent_type, expense_type_name), 3)


def get_fy_boundaries(doc_date):
    """Calculate financial year start/end dates (April 1 → March 31)."""
    if isinstance(doc_date, str):
        doc_date = datetime.strptime(doc_date, "%Y-%m-%d").date()
    elif hasattr(doc_date, "date") and callable(doc_date.date):
        doc_date = doc_date.date()
    year = doc_date.year
    month = doc_date.month
    if month >= 4:
        return date(year, 4, 1), date(year + 1, 3, 31)
    else:
        return date(year - 1, 4, 1), date(year, 3, 31)


def calculate_max_indent_qty(
    maxqty: float,
    branch_stock: float,
    outstanding_indent_qty: float,
    min_order_qty: float,
) -> float | None:
    """
    Calculate the maximum allowable indent quantity using the formula:
    available = max_qty - branch_stock - outstanding_indent_qty
    If available < reorder_qty → reorder_qty
    Else → ROUNDUP(available / reorder_qty) * reorder_qty
    Returns None if min_order_qty is 0/None (cannot compute).
    """
    if not min_order_qty or min_order_qty <= 0:
        # No reorder qty defined — cannot apply formula, allow any value
        return None
    available = maxqty - branch_stock - outstanding_indent_qty
    if available <= 0:
        return None  # No room to indent
    if available < min_order_qty:
        return min_order_qty
    return math.ceil(available / min_order_qty) * min_order_qty


@router.get("/validate_item_for_indent")
async def validate_item_for_indent(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Validate an item for indent creation.
    Returns validation data including errors, warnings, and allowable qty range
    based on (indent_type + expense_type) → Logic 1, 2, or 3.
    """
    try:
        branch_id = request.query_params.get("branch_id")
        item_id = request.query_params.get("item_id")
        indent_type = request.query_params.get("indent_type")
        expense_type_id = request.query_params.get("expense_type_id")

        if not branch_id:
            raise HTTPException(status_code=400, detail="branch_id is required")
        if not item_id:
            raise HTTPException(status_code=400, detail="item_id is required")
        if not indent_type:
            raise HTTPException(status_code=400, detail="indent_type is required")
        if not expense_type_id:
            raise HTTPException(status_code=400, detail="expense_type_id is required")

        try:
            branch_id = int(branch_id)
            item_id = int(item_id)
            expense_type_id = int(expense_type_id)
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter format: {e}")

        indent_type = normalize_indent_type(indent_type)
        if not is_valid_indent_type(indent_type):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid indent_type '{indent_type}'",
            )

        # Resolve expense type name
        expense_row = db.execute(
            get_expense_type_name_by_id(),
            {"expense_type_id": expense_type_id},
        ).fetchone()
        if not expense_row:
            raise HTTPException(status_code=400, detail=f"Invalid expense_type_id: {expense_type_id}")
        expense_type_name = dict(expense_row._mapping)["expense_type_name"]

        validation_logic = determine_validation_logic(indent_type, expense_type_name)

        result = {
            "validation_logic": validation_logic,
            "indent_type": indent_type,
            "expense_type_name": expense_type_name,
            "errors": [],
            "warnings": [],
            # Logic 1 fields
            "branch_stock": None,
            "outstanding_indent_qty": None,
            "minqty": None,
            "maxqty": None,
            "min_order_qty": None,
            "has_open_indent": False,
            "stock_exceeds_max": False,
            "max_indent_qty": None,
            "min_indent_qty": None,
            # Logic 2 fields
            "fy_indent_exists": False,
            "fy_indent_no": None,
            "has_minmax": False,
            "regular_bom_outstanding": None,
            "forced_qty": None,
        }

        if validation_logic == 3:
            # No validation — free entry
            return result

        # Fetch common validation data
        vdata_row = db.execute(
            get_item_validation_data(),
            {"branch_id": branch_id, "item_id": item_id},
        ).fetchone()

        vdata = dict(vdata_row._mapping) if vdata_row else {}
        branch_stock = float(vdata.get("branch_stock") or 0)
        outstanding = float(vdata.get("outstanding_indent_qty") or 0)
        minqty = vdata.get("minqty")
        maxqty = vdata.get("maxqty")
        min_order_qty = vdata.get("min_order_qty")
        has_open = int(vdata.get("has_open_indent") or 0)

        result["branch_stock"] = branch_stock
        result["outstanding_indent_qty"] = outstanding
        result["minqty"] = float(minqty) if minqty is not None else None
        result["maxqty"] = float(maxqty) if maxqty is not None else None
        result["min_order_qty"] = float(min_order_qty) if min_order_qty is not None else None
        result["has_open_indent"] = bool(has_open)

        if validation_logic == 1:
            # --- Logic 1: Max/Min + Stock Check ---

            # Step 1: Check for open indent against the item
            if has_open:
                result["errors"].append(
                    "An open indent already exists for this item at this branch."
                )

            # Step 2: Check stock + outstanding against max quantity
            if maxqty is not None and float(maxqty) > 0:
                result["has_minmax"] = True
                max_val = float(maxqty)
                if branch_stock + outstanding > max_val:
                    result["stock_exceeds_max"] = True
                    result["errors"].append(
                        f"Branch stock ({branch_stock}) + outstanding indent qty ({outstanding}) "
                        f"exceeds max qty ({max_val}). Cannot create indent."
                    )
                else:
                    # Step 3: Calculate allowable indent qty
                    reorder = float(min_order_qty) if min_order_qty else 0
                    max_indent = calculate_max_indent_qty(
                        max_val, branch_stock, outstanding, reorder
                    )
                    result["max_indent_qty"] = max_indent
                    result["min_indent_qty"] = float(minqty) if minqty else None
            else:
                # No max qty → user may enter any value
                result["has_minmax"] = False

        elif validation_logic == 2:
            # --- Logic 2: Open Entry + FY Check ---

            # Step 1: Check for existing open indent in current FY
            today = date.today()
            fy_start, fy_end = get_fy_boundaries(today)
            fy_row = db.execute(
                get_item_fy_indent_check(),
                {
                    "branch_id": branch_id,
                    "item_id": item_id,
                    "fy_start": fy_start,
                    "fy_end": fy_end,
                },
            ).fetchone()

            if fy_row:
                fy_data = dict(fy_row._mapping)
                result["fy_indent_exists"] = True
                result["fy_indent_no"] = fy_data.get("indent_no")
                result["errors"].append(
                    f"An open indent (#{fy_data.get('indent_no')}) already exists for this item "
                    f"in the current financial year ({fy_start.strftime('%d-%b-%Y')} to {fy_end.strftime('%d-%b-%Y')})."
                )

            # Step 2: Check if max/min exists
            if maxqty is None and minqty is None:
                result["has_minmax"] = False
                result["errors"].append(
                    "No max/min quantity defined for this item. Cannot create open indent."
                )
            else:
                result["has_minmax"] = True

            # Step 3: Check Regular/BOM outstanding (warning only)
            rb_row = db.execute(
                get_item_regular_bom_outstanding(),
                {"branch_id": branch_id, "item_id": item_id},
            ).fetchone()

            if rb_row:
                rb_outstanding = float(dict(rb_row._mapping).get("regular_bom_outstanding") or 0)
                result["regular_bom_outstanding"] = rb_outstanding
                if rb_outstanding > 0:
                    result["warnings"].append(
                        f"Outstanding indent qty ({rb_outstanding}) exists from Regular/BOM indents for this item."
                    )

            # Step 4: Force qty to maxqty
            if maxqty is not None:
                result["forced_qty"] = float(maxqty)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error validating item for indent")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_indent_setup_1")
async def get_indent_setup_1(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
	branch_id: int | None = None,
	co_id: int | None = None,
):
	"""Return branches, departments, projects, expense types and item groups for given branch_id and co_id."""
	try:
		# prefer query params if provided in request
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

		# Branch list: if branch_id provided, pass as single-element list, else let helper fetch all
		branch_ids_list = [branch_id] if branch_id is not None else None
		branchquery = get_branch_list(branch_ids=branch_ids_list) if branch_ids_list else get_branch_list()
		branch_result = db.execute(branchquery, {"branch_ids": branch_ids_list} if branch_ids_list else {}).fetchall()
		branches = [dict(r._mapping) for r in branch_result]

		# Departments for the branch(s)
		dept_query = get_dept_list_by_branch_id(branch_ids_list if branch_ids_list is not None else [])
		dept_result = db.execute(dept_query, {"branch_ids": branch_ids_list, "co_id": co_id}).fetchall()
		departments = [dict(r._mapping) for r in dept_result]

		# Projects (expects branch_id)
		projects = []
		if branch_id is not None:
			project_query = get_project(branch_id=branch_id)
			proj_result = db.execute(project_query, {"branch_id": branch_id}).fetchall()
			projects = [dict(r._mapping) for r in proj_result]

		# Expense types
		expense_query = get_expense_types()
		exp_result = db.execute(expense_query).fetchall()
		expense_types = [dict(r._mapping) for r in exp_result]

		# Item group dropdown (expects co_id)
		itemgrp_query = get_item_group_drodown(co_id=co_id)
		itemgrp_result = db.execute(itemgrp_query, {"co_id": co_id}).fetchall()
		item_groups = [dict(r._mapping) for r in itemgrp_result]

		return {
			"branches": branches,
			"departments": departments,
			"projects": projects,
			"expense_types": expense_types,
			"item_groups": item_groups,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
	

@router.get("/get_indent_setup_2")
async def get_indent_setup_2(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Return additional setup data for indents."""
	try:
		# Expecting an item_group param in the request (query param or JSON body)
		q_item_group = request.query_params.get("item_group")
		# if client sends JSON body for GET (non-standard), try reading it
		if q_item_group is None:
			try:
				body = await request.json()
				q_item_group = body.get("item_group") if isinstance(body, dict) else None
			except Exception:
				q_item_group = None

		if q_item_group is None:
			raise HTTPException(status_code=400, detail="item_group is required")

		try:
			item_group_id = int(q_item_group)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid item_group")

		# get items purchasable in this group
		items_query = get_item_by_group_id_purchaseable(item_group_id=item_group_id)
		items_result = db.execute(items_query, {"item_group_id": item_group_id}).fetchall()
		items = [dict(r._mapping) for r in items_result]

		# get item makes for this group
		makes_query = get_item_make_by_group_id(item_group_id=item_group_id)
		makes_result = db.execute(makes_query, {"item_group_id": item_group_id}).fetchall()
		makes = [dict(r._mapping) for r in makes_result]

		# get item uom mappings for this group
		uoms_query = get_item_uom_by_group_id(item_group_id=item_group_id)
		uoms_result = db.execute(uoms_query, {"item_group_id": item_group_id}).fetchall()
		uoms = [dict(r._mapping) for r in uoms_result]


		return {
			"items": items,
			"makes": makes,
			"uoms": uoms,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_indent_table")
async def get_indent_table(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
	page: int = 1,
	limit: int = 10,
	search: str | None = None,
	co_id: int | None = None,
):
	"""Return paginated procurement indent list."""

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

		list_query = get_indent_table_query()
		rows = db.execute(list_query, params).fetchall()
		data = []
		for row in rows:
			mapped = dict(row._mapping)
			indent_date_obj = mapped.get("indent_date")
			indent_date = indent_date_obj
			if hasattr(indent_date_obj, "isoformat"):
				indent_date = indent_date_obj.isoformat()
			
			# Format indent_no if it exists
			raw_indent_no = mapped.get("indent_no")
			formatted_indent_no = ""
			if raw_indent_no is not None and raw_indent_no != 0:
				try:
					indent_no_int = int(raw_indent_no) if raw_indent_no else None
					co_prefix = mapped.get("co_prefix")
					branch_prefix = mapped.get("branch_prefix")
					formatted_indent_no = format_indent_no(
						indent_no=indent_no_int,
						co_prefix=co_prefix,
						branch_prefix=branch_prefix,
						indent_date=indent_date_obj,
						document_type="INDENT"
					)
				except Exception as e:
					logger.exception("Error formatting indent number in list, using raw value")
					formatted_indent_no = str(raw_indent_no) if raw_indent_no else ""
			
			data.append(
				{
					"indent_id": mapped.get("indent_id"),
					"indent_no": formatted_indent_no,
					"indent_date": indent_date,
					"branch_name": mapped.get("branch_name"),
					"expense_type": mapped.get("expense_type_name"),
					"status": mapped.get("status_name"),
				}
			)

		count_query = get_indent_table_count_query()
		count_params = {"co_id": co_id, "search_like": search_like}
		count_result = db.execute(count_query, count_params).scalar()
		total = int(count_result) if count_result is not None else 0

		return {
			"data": data,
			"total": total,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_all_approved_indents")
async def get_all_approved_indents(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
	branch_id: int | None = None,
	co_id: int | None = None,
):
	"""Get all approved indents (status_id = 3) for dropdown selection."""
	try:
		# Priority: 1. co_id from query params, 2. co_id from token_data, 3. derive from branch_id
		filter_co_id = co_id
		
		if filter_co_id is None:
			# Try to get from token_data
			user_co_id = token_data.get("co_id")
			if user_co_id:
				filter_co_id = user_co_id
		
		if filter_co_id is None and branch_id:
			# If we have branch_id but no co_id, get co_id from branch
			# Query branch_mst directly to get co_id
			from sqlalchemy.sql import text
			branch_sql = text("SELECT co_id FROM branch_mst WHERE branch_id = :branch_id")
			branch_result = db.execute(branch_sql, {"branch_id": branch_id}).fetchone()
			if branch_result:
				filter_co_id = branch_result[0] if isinstance(branch_result, tuple) else branch_result._mapping.get("co_id")
		
		# If still no co_id, raise error
		if filter_co_id is None:
			raise HTTPException(status_code=400, detail="Company ID is required. Please provide co_id or branch_id.")
		
		query = get_all_approved_indents_query()
		params = {"branch_id": branch_id, "co_id": filter_co_id}
		results = db.execute(query, params).fetchall()
		
		data = []
		for row in results:
			mapped = row._mapping
			indent_id = mapped.get("indent_id")
			if not indent_id:
				continue
			
			# Format indent_no
			raw_indent_no = mapped.get("indent_no")
			formatted_indent_no = ""
			if raw_indent_no is not None and raw_indent_no != 0:
				try:
					indent_date_str = mapped.get("indent_date")
					indent_date_obj = None
					if indent_date_str:
						if isinstance(indent_date_str, str):
							indent_date_obj = datetime.strptime(indent_date_str, "%Y-%m-%d").date()
						else:
							indent_date_obj = indent_date_str
					
					indent_no_int = int(raw_indent_no) if raw_indent_no else None
					co_prefix = mapped.get("co_prefix")
					branch_prefix = mapped.get("branch_prefix")
					formatted_indent_no = format_indent_no(
						indent_no=indent_no_int,
						co_prefix=co_prefix,
						branch_prefix=branch_prefix,
						indent_date=indent_date_obj,
						document_type="INDENT"
					)
				except Exception as e:
					logger.exception("Error formatting indent number, using raw value")
					formatted_indent_no = str(raw_indent_no) if raw_indent_no else ""
			
			indent_date = mapped.get("indent_date")
			if indent_date:
				if isinstance(indent_date, str):
					indent_date = indent_date
				else:
					indent_date = indent_date.strftime("%Y-%m-%d") if hasattr(indent_date, "strftime") else str(indent_date)
			else:
				indent_date = ""
			
			data.append({
				"indent_id": indent_id,
				"indent_no": formatted_indent_no,
				"indent_date": indent_date,
				"branch_name": mapped.get("branch_name") or "",
				"expense_type": mapped.get("expense_type_name") or "",
			})
		
		return {"data": data}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching approved indents")
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_indent_by_id")
async def get_indent_by_id(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Return indent details by ID with all line items."""
	try:
		# Get query parameters
		q_indent_id = request.query_params.get("indent_id")
		q_co_id = request.query_params.get("co_id")

		if q_indent_id is None:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if q_co_id is None:
			raise HTTPException(status_code=400, detail="co_id is required")

		try:
			indent_id = int(q_indent_id)
			co_id = int(q_co_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id or co_id")

		# Fetch header data
		header_query = get_indent_by_id_query()
		header_params = {"indent_id": indent_id, "co_id": co_id}
		header_result = db.execute(header_query, header_params).fetchone()

		if not header_result:
			raise HTTPException(status_code=404, detail="Indent not found or access denied")

		header = dict(header_result._mapping)

		# Fetch line items
		detail_query = get_indent_detail_by_id_query()
		detail_params = {"indent_id": indent_id}
		detail_results = db.execute(detail_query, detail_params).fetchall()
		details = [dict(r._mapping) for r in detail_results]

		# Get indent_type - use normalize_indent_type from constants for consistency
		indent_type_id = header.get("indent_type_id")
		indent_type_str = normalize_indent_type(indent_type_id)

		# Format dates - frontend expects YYYY-MM-DD format
		indent_date = header.get("indent_date")
		if indent_date and hasattr(indent_date, "date"):
			# datetime object
			indent_date_str = indent_date.date().isoformat()
		elif indent_date and hasattr(indent_date, "isoformat"):
			# date object
			indent_date_str = indent_date.isoformat()
		elif indent_date:
			indent_date_str = str(indent_date)
		else:
			indent_date_str = ""

		updated_at = header.get("updated_date_time")
		updated_at_str = None
		if updated_at:
			if hasattr(updated_at, "isoformat"):
				updated_at_str = updated_at.isoformat()
			else:
				updated_at_str = str(updated_at)

		# Get approval_level (only when status_id = 20, otherwise null)
		approval_level = header.get("approval_level")
		if approval_level is not None:
			try:
				approval_level = int(approval_level)
			except (TypeError, ValueError):
				approval_level = None
		else:
			approval_level = None
		
		# Get status_id
		status_id = header.get("status_id")
		branch_id = header.get("branch_id")
		
		# Get menu_id from query params (optional - needed for permission calculation)
		q_menu_id = request.query_params.get("menu_id")
		menu_id = None
		if q_menu_id is not None:
			try:
				menu_id = int(q_menu_id)
			except (TypeError, ValueError):
				menu_id = None
		
		# Calculate permissions if menu_id is provided
		permissions = None
		if menu_id is not None and branch_id is not None and status_id is not None:
			try:
				user_id = int(token_data.get("user_id"))
				permissions = calculate_approval_permissions(
					user_id=user_id,
					menu_id=menu_id,
					branch_id=branch_id,
					status_id=status_id,
					current_approval_level=approval_level,
					db=db,
				)
			except Exception as e:
				logger.exception("Error calculating permissions, continuing without them")
				permissions = None
		
		# Format indent_no if it exists
		raw_indent_no = header.get("indent_no")
		formatted_indent_no = ""
		if raw_indent_no is not None and raw_indent_no != 0:
			try:
				indent_no_int = int(raw_indent_no) if raw_indent_no else None
				co_prefix = header.get("co_prefix")
				branch_prefix = header.get("branch_prefix")
				formatted_indent_no = format_indent_no(
					indent_no=indent_no_int,
					co_prefix=co_prefix,
					branch_prefix=branch_prefix,
					indent_date=indent_date,
					document_type="INDENT"
				)
			except Exception as e:
				logger.exception("Error formatting indent number, using raw value")
				formatted_indent_no = str(raw_indent_no) if raw_indent_no else ""

		# Build response
		response = {
			"id": str(header.get("indent_id", "")),
			"indentNo": formatted_indent_no,
			"indentDate": indent_date_str,
			"branch": str(header.get("branch_id", "")) if header.get("branch_id") else "",
			"indentType": indent_type_str,
			"expenseType": str(header.get("expense_type_id", "")) if header.get("expense_type_id") else "",
			"project": str(header.get("project_id", "")) if header.get("project_id") else None,
			"requester": header.get("indent_title") if header.get("indent_title") else None,
			"status": header.get("status_name") if header.get("status_name") else None,
			"statusId": header.get("status_id"),
			"approvalLevel": approval_level,
			"updatedBy": str(header.get("updated_by", "")) if header.get("updated_by") else None,
			"updatedAt": updated_at_str,
			"remarks": header.get("remarks") if header.get("remarks") else None,
			"lines": [],
		}
		
		# Add permissions if calculated
		if permissions is not None:
			response["permissions"] = permissions

		# Map line items
		for detail in details:
			line = {
				"id": str(detail.get("indent_dtl_id", "")) if detail.get("indent_dtl_id") else "",
				"department": str(detail.get("dept_id", "")) if detail.get("dept_id") else None,
				"itemGroup": str(detail.get("item_grp_id", "")) if detail.get("item_grp_id") else "",
				"item": str(detail.get("item_id", "")) if detail.get("item_id") else "",
				"itemMake": str(detail.get("item_make_id", "")) if detail.get("item_make_id") else None,
				"quantity": float(detail.get("qty", 0)) if detail.get("qty") is not None else 0,
				"uom": str(detail.get("uom_id", "")) if detail.get("uom_id") else "",
				"remarks": detail.get("remarks") if detail.get("remarks") else None,
			}
			response["lines"].append(line)

		return response
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching indent by ID")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/create_indent")
async def create_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Create a procurement indent with detail rows."""

	def to_int(value, field_name: str, required: bool = False) -> int | None:
		if value is None or value == "":
			if required:
				raise HTTPException(status_code=400, detail=f"{field_name} is required")
			return None
		try:
			return int(value)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

	def to_positive_float(value, field_name: str) -> float:
		try:
			qty = float(value)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail=f"Invalid {field_name}")
		if qty <= 0:
			raise HTTPException(status_code=400, detail=f"{field_name} must be greater than zero")
		return qty

	try:
		branch_id = to_int(payload.get("branch"), "branch", required=True)
		expense_type_id = to_int(payload.get("expense_type"), "expense_type", required=True)
		indent_type = payload.get("indent_type")
		if not indent_type:
			raise HTTPException(status_code=400, detail="indent_type is required")
		if not is_valid_indent_type(indent_type):
			raise HTTPException(
				status_code=400, 
				detail=f"Invalid indent_type '{indent_type}'. Valid values: {VALID_INDENT_TYPE_VALUES}"
			)

		date_str = payload.get("date")
		if not date_str:
			raise HTTPException(status_code=400, detail="date is required")
		try:
			indent_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
		except ValueError:
			raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

		raw_items = payload.get("items")
		if not isinstance(raw_items, list) or len(raw_items) == 0:
			raise HTTPException(status_code=400, detail="At least one item row is required")

		updated_by = to_int(token_data.get("user_id"), "updated_by")
		created_at = datetime.utcnow()
		indent_title_raw = payload.get("name")
		indent_title = str(indent_title_raw).strip() if indent_title_raw else None
		header_remarks_raw = payload.get("remarks")
		header_remarks = str(header_remarks_raw).strip() if header_remarks_raw else None
		indent_no_value = to_int(payload.get("indent_no"), "indent_no", required=False)
		project_id = to_int(payload.get("project"), "project")

		normalized_items = []
		for idx, item in enumerate(raw_items, start=1):
			item_id = to_int(item.get("item"), f"items[{idx}].item", required=True)
			qty = to_positive_float(item.get("quantity"), f"items[{idx}].quantity")
			uom_id = to_int(item.get("uom"), f"items[{idx}].uom", required=True)
			item_make_id = to_int(item.get("item_make"), f"items[{idx}].item_make")
			department_id = to_int(item.get("department"), f"items[{idx}].department")

			remarks_raw = item.get("remarks")
			remarks = str(remarks_raw).strip() if remarks_raw else None
			if remarks:
				remarks = remarks[:599]

			normalized_items.append(
				{
					"item_id": item_id,
					"qty": qty,
					"uom_id": uom_id,
					"item_make_id": item_make_id,
					"remarks": remarks,
					"dept_id": department_id,
				}
			)

		logger.debug("Normalized indent items: %s", normalized_items)

		# ── Server-side line-item validation (safety net) ──────────────
		expense_name_row = db.execute(
			get_expense_type_name_by_id(),
			{"expense_type_id": int(expense_type_id)},
		).fetchone()
		resolved_expense_name = (
			dict(expense_name_row._mapping)["expense_type_name"]
			if expense_name_row
			else None
		)
		validation_logic = determine_validation_logic(indent_type, resolved_expense_name)

		if validation_logic in (1, 2):
			fy_start, fy_end = get_fy_boundaries(indent_date)
			for idx, ni in enumerate(normalized_items, start=1):
				item_id = ni["item_id"]

				if validation_logic == 1:
					vdata = db.execute(
						get_item_validation_data(),
						{"branch_id": int(branch_id), "item_id": int(item_id)},
					).fetchone()
					if vdata:
						vd = dict(vdata._mapping)
						max_allowed = calculate_max_indent_qty(
							vd.get("maxqty"),
							vd.get("branch_stock", 0),
							vd.get("outstanding_indent_qty", 0),
							vd.get("min_order_qty"),
						)
						if max_allowed is not None and ni["qty"] > max_allowed:
							raise HTTPException(
								status_code=400,
								detail=(
									f"Row {idx}: Quantity {ni['qty']} exceeds the "
									f"maximum allowed indent quantity of {max_allowed:.2f} "
									f"for this item (maxQty={vd.get('maxqty')}, "
									f"stock={vd.get('branch_stock', 0)}, "
									f"outstanding={vd.get('outstanding_indent_qty', 0)})."
								),
							)

				elif validation_logic == 2:
					fy_row = db.execute(
						get_item_fy_indent_check(),
						{
							"item_id": int(item_id),
							"branch_id": int(branch_id),
							"fy_start": fy_start,
							"fy_end": fy_end,
						},
					).fetchone()
					if fy_row:
						existing = dict(fy_row._mapping)
						raise HTTPException(
							status_code=400,
							detail=(
								f"Row {idx}: An open indent already exists for this "
								f"item in the current financial year "
								f"(Indent No: {existing.get('indent_no')})."
							),
						)

		insert_header_query = insert_proc_indent()
		header_params = {
			"indent_date": indent_date,
			"indent_no": indent_no_value,
			"active": 1,
			"indent_type_id": indent_type,
			"remarks": header_remarks,
			"branch_id": branch_id,
			"expense_type_id": expense_type_id,
			"project_id": project_id,
			"updated_by": updated_by,
			"updated_date_time": created_at,
			"status_id": 21,
			"indent_title": indent_title,
		}

		logger.info(
			"Creating indent: branch=%s, indent_type=%s, expense_type=%s, item_rows=%s",
			branch_id,
			indent_type,
			expense_type_id,
			len(normalized_items),
		)
		logger.debug("Indent header params: %s", header_params)

		result = db.execute(insert_header_query, header_params)
		indent_id = result.lastrowid
		if not indent_id:
			raise HTTPException(status_code=500, detail="Failed to create indent header")

		if indent_no_value is None:
			indent_no_value = indent_id

		detail_query = insert_proc_indent_detail()
		for detail in normalized_items:
			db.execute(
				detail_query,
				{
					"indent_id": indent_id,
					"required_by_days": None,
					"active": 1,
					"item_id": detail["item_id"],
					"qty": detail["qty"],
					"uom_id": detail["uom_id"],
					"remarks": detail["remarks"],
					"updated_by": updated_by,
					"updated_date_time": created_at,
					"item_make_id": detail["item_make_id"],
					"dept_id": detail["dept_id"],
				},
			)

		db.commit()
		return {
			"message": "Indent created successfully",
			"indent_id": indent_id,
			"indent_no": indent_no_value,
		}
	except HTTPException as exc:
		db.rollback()
		logger.warning("Indent create failed with HTTP error: %s", getattr(exc, "detail", exc))
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Unexpected error while creating indent")
		raise HTTPException(
			status_code=500,
			detail={
				"message": "Failed to create indent",
				"error": str(e),
			},
		)


@router.put("/update_indent")
async def update_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Update a procurement indent with detail rows."""
	def to_int(value, field_name: str, required: bool = False) -> int | None:
		if value is None or value == "":
			if required:
				raise HTTPException(status_code=400, detail=f"{field_name} is required")
			return None
		try:
			return int(value)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

	def to_positive_float(value, field_name: str) -> float:
		try:
			qty = float(value)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail=f"Invalid {field_name}")
		if qty <= 0:
			raise HTTPException(status_code=400, detail=f"{field_name} must be greater than zero")
		return qty

	try:
		indent_id = to_int(payload.get("id"), "id", required=True)
		branch_id = to_int(payload.get("branch"), "branch", required=True)
		expense_type_id = to_int(payload.get("expense_type"), "expense_type", required=True)
		indent_type = payload.get("indent_type")
		if not indent_type:
			raise HTTPException(status_code=400, detail="indent_type is required")
		if not is_valid_indent_type(indent_type):
			raise HTTPException(
				status_code=400, 
				detail=f"Invalid indent_type '{indent_type}'. Valid values: {VALID_INDENT_TYPE_VALUES}"
			)

		date_str = payload.get("date")
		if not date_str:
			raise HTTPException(status_code=400, detail="date is required")
		try:
			indent_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
		except ValueError:
			raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

		raw_items = payload.get("items")
		if not isinstance(raw_items, list) or len(raw_items) == 0:
			raise HTTPException(status_code=400, detail="At least one item row is required")

		updated_by = to_int(token_data.get("user_id"), "updated_by")
		updated_at = datetime.utcnow()
		indent_title_raw = payload.get("name")
		indent_title = str(indent_title_raw).strip() if indent_title_raw else None
		header_remarks_raw = payload.get("remarks")
		header_remarks = str(header_remarks_raw).strip() if header_remarks_raw else None
		project_id = to_int(payload.get("project"), "project")

		# Verify indent exists (basic check - full access control handled by branch_id validation)
		# We'll verify the indent exists by checking if we can fetch it
		# The actual co_id validation happens through branch access
		check_query = text("SELECT indent_id FROM proc_indent WHERE indent_id = :indent_id AND active = 1")
		check_result = db.execute(check_query, {"indent_id": indent_id}).fetchone()
		if not check_result:
			raise HTTPException(status_code=404, detail="Indent not found or inactive")

		normalized_items = []
		for idx, item in enumerate(raw_items, start=1):
			item_id = to_int(item.get("item"), f"items[{idx}].item", required=True)
			qty = to_positive_float(item.get("quantity"), f"items[{idx}].quantity")
			uom_id = to_int(item.get("uom"), f"items[{idx}].uom", required=True)
			item_make_id = to_int(item.get("item_make"), f"items[{idx}].item_make")
			department_id = to_int(item.get("department"), f"items[{idx}].department")

			remarks_raw = item.get("remarks")
			remarks = str(remarks_raw).strip() if remarks_raw else None
			if remarks:
				remarks = remarks[:599]

			normalized_items.append(
				{
					"item_id": item_id,
					"qty": qty,
					"uom_id": uom_id,
					"item_make_id": item_make_id,
					"remarks": remarks,
					"dept_id": department_id,
				}
			)

		logger.debug("Normalized indent items for update: %s", normalized_items)

		# ── Server-side line-item validation (safety net) ──────────────
		expense_name_row = db.execute(
			get_expense_type_name_by_id(),
			{"expense_type_id": int(expense_type_id)},
		).fetchone()
		resolved_expense_name = (
			dict(expense_name_row._mapping)["expense_type_name"]
			if expense_name_row
			else None
		)
		validation_logic = determine_validation_logic(indent_type, resolved_expense_name)

		if validation_logic in (1, 2):
			fy_start, fy_end = get_fy_boundaries(indent_date)
			for idx, ni in enumerate(normalized_items, start=1):
				item_id = ni["item_id"]

				if validation_logic == 1:
					vdata = db.execute(
						get_item_validation_data(),
						{"branch_id": int(branch_id), "item_id": int(item_id)},
					).fetchone()
					if vdata:
						vd = dict(vdata._mapping)
						max_allowed = calculate_max_indent_qty(
							vd.get("maxqty"),
							vd.get("branch_stock", 0),
							vd.get("outstanding_indent_qty", 0),
							vd.get("min_order_qty"),
						)
						if max_allowed is not None and ni["qty"] > max_allowed:
							raise HTTPException(
								status_code=400,
								detail=(
									f"Row {idx}: Quantity {ni['qty']} exceeds the "
									f"maximum allowed indent quantity of {max_allowed:.2f} "
									f"for this item (maxQty={vd.get('maxqty')}, "
									f"stock={vd.get('branch_stock', 0)}, "
									f"outstanding={vd.get('outstanding_indent_qty', 0)})."
								),
							)

				elif validation_logic == 2:
					fy_row = db.execute(
						get_item_fy_indent_check(),
						{
							"item_id": int(item_id),
							"branch_id": int(branch_id),
							"fy_start": fy_start,
							"fy_end": fy_end,
						},
					).fetchone()
					if fy_row:
						existing = dict(fy_row._mapping)
						raise HTTPException(
							status_code=400,
							detail=(
								f"Row {idx}: An open indent already exists for this "
								f"item in the current financial year "
								f"(Indent No: {existing.get('indent_no')})."
							),
						)

		# Get existing indent_no, active, and status_id to preserve them
		# This also helps avoid trigger issues by ensuring all columns are present
		existing_query = text("SELECT indent_no, active, status_id FROM proc_indent WHERE indent_id = :indent_id")
		existing_result = db.execute(existing_query, {"indent_id": indent_id}).fetchone()
		if not existing_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		existing_indent_no = existing_result[0] if existing_result[0] is not None else None
		existing_active = existing_result[1] if existing_result[1] is not None else 1
		existing_status_id = existing_result[2] if existing_result[2] is not None else None

		# Update header
		update_header_query = update_proc_indent()
		header_params = {
			"indent_id": indent_id,
			"indent_date": indent_date,
			"branch_id": branch_id,
			"indent_type_id": indent_type,
			"expense_type_id": expense_type_id,
			"project_id": project_id,
			"indent_title": indent_title,
			"remarks": header_remarks,
			"updated_by": updated_by,
			"updated_date_time": updated_at,
			"indent_no": existing_indent_no,
			"active": existing_active,
			"status_id": existing_status_id,
		}

		logger.info(
			"Updating indent: indent_id=%s, branch=%s, indent_type=%s, expense_type=%s, item_rows=%s",
			indent_id,
			branch_id,
			indent_type,
			expense_type_id,
			len(normalized_items),
		)
		logger.debug("Indent header update params: %s", header_params)

		db.execute(update_header_query, header_params)

		# Soft delete existing detail rows
		delete_detail_query = delete_proc_indent_detail()
		db.execute(
			delete_detail_query,
			{
				"indent_id": indent_id,
				"updated_by": updated_by,
				"updated_date_time": updated_at,
			},
		)

		# Insert new detail rows
		detail_query = insert_proc_indent_detail()
		for detail in normalized_items:
			db.execute(
				detail_query,
				{
					"indent_id": indent_id,
					"required_by_days": None,
					"active": 1,
					"item_id": detail["item_id"],
					"qty": detail["qty"],
					"uom_id": detail["uom_id"],
					"remarks": detail["remarks"],
					"updated_by": updated_by,
					"updated_date_time": updated_at,
					"item_make_id": detail["item_make_id"],
					"dept_id": detail["dept_id"],
				},
			)

		db.commit()
		return {
			"message": "Indent updated successfully",
			"indent_id": indent_id,
		}
	except HTTPException as exc:
		db.rollback()
		logger.warning("Indent update failed with HTTP error: %s", getattr(exc, "detail", exc))
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Unexpected error while updating indent")
		raise HTTPException(
			status_code=500,
			detail=str(e),
		)


# ==================== INDENT NUMBER FORMATTING ====================

def calculate_financial_year(indent_date) -> str:
	"""Calculate financial year in YY-YY format from a date.
	
	Financial year: April 1 to March 31
	- If month >= 4 (April-December): FY = YY-YY (e.g., April 2025 = 25-26)
	- If month < 4 (January-March): FY = (YY-1)-YY (e.g., January 2025 = 24-25)
	
	Args:
		indent_date: Date object, datetime object, or date string
		
	Returns:
		Financial year string in YY-YY format (e.g., "25-26")
	"""
	try:
		# Handle different date formats
		if hasattr(indent_date, "year") and hasattr(indent_date, "month"):
			# Date object
			year = indent_date.year
			month = indent_date.month
		elif hasattr(indent_date, "date"):
			# Datetime object
			date_obj = indent_date.date()
			year = date_obj.year
			month = date_obj.month
		else:
			# String or other format - try to parse
			if isinstance(indent_date, str):
				try:
					date_obj = datetime.strptime(indent_date, "%Y-%m-%d").date()
				except ValueError:
					date_obj = datetime.fromisoformat(indent_date).date()
			else:
				date_obj = datetime.fromisoformat(str(indent_date)).date()
			year = date_obj.year
			month = date_obj.month
		
		# Calculate financial year
		if month >= 4:
			# April-December: FY = current year to next year
			fy_start = year % 100
			fy_end = (year + 1) % 100
		else:
			# January-March: FY = previous year to current year
			fy_start = (year - 1) % 100
			fy_end = year % 100
		
		return f"{fy_start:02d}-{fy_end:02d}"
	except Exception as e:
		logger.exception(f"Error calculating financial year from {indent_date}")
		# Fallback to current year if date parsing fails
		now = datetime.now()
		current_year = now.year
		current_month = now.month
		if current_month >= 4:
			return f"{current_year % 100:02d}-{(current_year + 1) % 100:02d}"
		else:
			return f"{(current_year - 1) % 100:02d}-{current_year % 100:02d}"


def format_indent_no(
	indent_no: Optional[int],
	co_prefix: Optional[str],
	branch_prefix: Optional[str],
	indent_date,
	document_type: str = "INDENT"
) -> str:
	"""Format indent number as "co_prefix/branch_prefix/document_type/financial_year/indent_no".
	
	Args:
		indent_no: Numeric indent number (from database)
		co_prefix: Company prefix from co_mst
		branch_prefix: Branch prefix from branch_mst
		indent_date: Date for calculating financial year
		document_type: Document type prefix (default: "INDENT")
		
	Returns:
		Formatted indent number string (e.g., "ABC/MAIN/INDENT/25-26/1")
		Returns empty string if indent_no is None or 0
	"""
	# Return empty string if indent_no is not set
	if indent_no is None or indent_no == 0:
		return ""
	
	# Calculate financial year
	fy = calculate_financial_year(indent_date)
	
	# Get prefixes with fallbacks (use empty string if None)
	co_pref = co_prefix or ""
	branch_pref = branch_prefix or ""
	
	# Build formatted string: co_prefix/branch_prefix/document_type/financial_year/indent_no
	# Filter out empty prefixes but keep structure for non-empty parts
	parts = []
	if co_pref:
		parts.append(co_pref)
	if branch_pref:
		parts.append(branch_pref)
	# Always include document_type, financial_year, and indent_no
	parts.extend([document_type, fy, str(indent_no)])
	
	return "/".join(parts)


# ==================== APPROVAL FLOW FUNCTIONS ====================

def get_approval_flow_details(menu_id: int, branch_id: int, db: Session) -> list:
	"""Get approval flow details for a menu and branch combination.
	
	Args:
		menu_id: The menu ID
		branch_id: The branch ID
		db: Database session
		
	Returns:
		List of approval flow records ordered by approval_level
	"""
	try:
		query = get_approval_flow_by_menu_branch()
		result = db.execute(query, {"menu_id": menu_id, "branch_id": branch_id}).fetchall()
		return [dict(r._mapping) for r in result]
	except Exception as e:
		logger.exception("Error fetching approval flow details")
		raise


def calculate_approval_permissions(
	user_id: int,
	menu_id: int,
	branch_id: int,
	status_id: int,
	current_approval_level: Optional[int],
	db: Session,
) -> dict:
	"""Calculate approval permissions for a user based on indent status and approval configuration.
	
	Args:
		user_id: The user ID
		menu_id: The menu ID
		branch_id: The branch ID
		status_id: Current status ID of the indent
		current_approval_level: Current approval level (only relevant when status_id = 20)
		db: Database session
		
	Returns:
		Dict with permission flags
	"""
	permissions = {
		"canApprove": False,
		"canReject": False,
		"canOpen": False,
		"canSendForApproval": False,
		"canCancelDraft": False,
		"canReopen": False,
		"canViewApprovalLog": False,
		"canClone": False,
		"canSave": False,
	}
	
	try:
		# Check if approval_mst has entries for this menu/branch
		approval_exists_query = check_approval_mst_exists()
		approval_exists_result = db.execute(
			approval_exists_query,
			{"menu_id": menu_id, "branch_id": branch_id}
		).fetchone()
		approval_exists = False
		if approval_exists_result:
			result_dict = dict(approval_exists_result._mapping)
			approval_exists = (result_dict.get("count") or 0) > 0
		
		# Status-based permissions (always available based on status)
		if status_id == 21:  # Drafted
			permissions["canOpen"] = True
			permissions["canCancelDraft"] = True
			permissions["canSave"] = True
		elif status_id == 1:  # Open - show Approve button instead of Send for Approval
			permissions["canSave"] = True
			# Check approval permissions for Open status (same logic as Pending Approval)
			if approval_exists:
				# Approval hierarchy exists - check if user has approval level 1
				user_level_query = get_user_approval_level()
				user_level_result = db.execute(
					user_level_query,
					{"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
				).fetchone()
				
				if user_level_result:
					user_approval_level = dict(user_level_result._mapping).get("approval_level")
					if user_approval_level == 1:  # User can approve at level 1
						permissions["canApprove"] = True
			else:
				# No approval hierarchy - check if user has edit access
				edit_access_query = get_user_edit_access()
				edit_access_result = db.execute(
					edit_access_query,
					{"user_id": user_id, "branch_id": branch_id, "menu_id": menu_id}
				).fetchone()
				
				if edit_access_result:
					max_access_type = dict(edit_access_result._mapping).get("max_access_type_id")
					# access_type_id >= 4 means edit access
					if max_access_type is not None and max_access_type >= 4:
						permissions["canApprove"] = True
		elif status_id == 6:  # Cancelled
			permissions["canReopen"] = True
			permissions["canClone"] = True
			permissions["canViewApprovalLog"] = True
		elif status_id == 4:  # Rejected
			permissions["canReopen"] = True
			permissions["canClone"] = True
			permissions["canViewApprovalLog"] = True
		elif status_id == 3:  # Approved
			permissions["canViewApprovalLog"] = True
			permissions["canClone"] = True
		elif status_id == 5:  # Closed
			permissions["canViewApprovalLog"] = True
		
		# Approval/Reject permissions (only for status_id = 20)
		if status_id == 20:  # Pending Approval
			permissions["canViewApprovalLog"] = True
			
			if approval_exists:
				# Approval hierarchy exists - check if user's level matches current level
				if current_approval_level is not None:
					user_level_query = get_user_approval_level()
					user_level_result = db.execute(
						user_level_query,
						{"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
					).fetchone()
					
					if user_level_result:
						user_approval_level = dict(user_level_result._mapping).get("approval_level")
						if user_approval_level == current_approval_level:
							permissions["canApprove"] = True
							permissions["canReject"] = True
			else:
				# No approval hierarchy - check if user has edit access
				edit_access_query = get_user_edit_access()
				edit_access_result = db.execute(
					edit_access_query,
					{"user_id": user_id, "branch_id": branch_id, "menu_id": menu_id}
				).fetchone()
				
				if edit_access_result:
					max_access_type = dict(edit_access_result._mapping).get("max_access_type_id")
					# access_type_id >= 4 means edit access
					if max_access_type is not None and max_access_type >= 4:
						permissions["canApprove"] = True
						permissions["canReject"] = True
		
		return permissions
	except Exception as e:
		logger.exception("Error calculating approval permissions")
		# Return default permissions (all False) on error
		return permissions


def process_approval_without_value(
	indent_id: int,
	user_id: int,
	menu_id: int,
	db: Session,
) -> dict:
	"""Process approval for documents without monetary value (e.g., Indent).
	
	Logic:
	1. Get current indent status and approval level
	2. Get user's approval level for the menu/branch
	3. Check if user can approve at current level
	4. If yes, move to next level or approve if final level
	5. Update status_id and approval_level in database
	
	Args:
		indent_id: The indent ID
		user_id: The user ID who is approving
		menu_id: The menu ID (e.g., indent menu)
		db: Database session
		
	Returns:
		Dict with status, new_status_id, new_approval_level, and message
	"""
	try:
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		current_approval_level = indent.get("approval_level") or 0
		branch_id = indent.get("branch_id")
		
		# If status is Open (1), first transition to Pending Approval (20) with level 1
		if current_status_id == 1:
			# Change status to Pending Approval (20) with level 1
			updated_at = datetime.utcnow()
			update_query = update_indent_status()
			db.execute(
				update_query,
				{
					"indent_id": indent_id,
					"status_id": 20,  # Pending Approval
					"approval_level": 1,  # Start at level 1
					"updated_by": user_id,
					"updated_date_time": updated_at,
					"indent_no": None,  # Don't update indent_no
				}
			)
			db.commit()
			# Update current status and level for further processing
			current_status_id = 20
			current_approval_level = 1
			# Refresh indent data after status change
			indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
			if indent_result:
				indent = dict(indent_result._mapping)
		
		# Verify current status is Pending Approval (20)
		if current_status_id != 20:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot approve indent with status_id {current_status_id}. Expected status 20 (Pending Approval) or 1 (Open)."
			)
		
		# Get user's approval level
		user_level_query = get_user_approval_level()
		user_level_result = db.execute(
			user_level_query,
			{"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
		).fetchone()
		
		if not user_level_result:
			raise HTTPException(
				status_code=403,
				detail="User does not have approval permission for this menu and branch."
			)
		
		user_approval_level = dict(user_level_result._mapping).get("approval_level")
		
		# Check if user can approve at current level
		if user_approval_level != current_approval_level:
			raise HTTPException(
				status_code=403,
				detail=f"User approval level ({user_approval_level}) does not match current indent approval level ({current_approval_level})."
			)
		
		# Get max approval level
		max_level_query = get_max_approval_level()
		max_level_result = db.execute(
			max_level_query,
			{"menu_id": menu_id, "branch_id": branch_id}
		).fetchone()
		
		max_approval_level = dict(max_level_result._mapping).get("max_level") if max_level_result else user_approval_level
		
		# Determine next status
		if user_approval_level >= max_approval_level:
			# Final level - approve
			new_status_id = 3  # Approved
			new_approval_level = user_approval_level
			message = "Indent approved (final level)."
		else:
			# Move to next level
			new_status_id = 20  # Still Pending Approval
			new_approval_level = current_approval_level + 1
			message = f"Indent moved to approval level {new_approval_level}."
		
		# Update indent status
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		db.execute(
			update_query,
			{
				"indent_id": indent_id,
				"status_id": new_status_id,
				"approval_level": new_approval_level,
				"updated_by": user_id,
				"updated_date_time": updated_at,
				"indent_no": None,  # Don't update indent_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": new_status_id,
			"new_approval_level": new_approval_level,
			"message": message,
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error processing approval without value")
		raise HTTPException(status_code=500, detail=str(e))


def process_approval_with_value(
	indent_id: int,
	user_id: int,
	menu_id: int,
	document_amount: float,
	db: Session,
) -> dict:
	"""Process approval for documents with monetary value.
	
	Logic:
	1. Get current indent status and approval level
	2. Get user's approval level and amount limits
	3. Check if user can approve at current level
	4. Check amount limits: max_amount_single, day_max_amount, month_max_amount
	5. If all criteria met, move to next level or approve if final level
	6. Update status_id and approval_level in database
	
	Args:
		indent_id: The indent ID
		user_id: The user ID who is approving
		menu_id: The menu ID
		document_amount: The document amount
		db: Database session
		
	Returns:
		Dict with status, new_status_id, new_approval_level, and message
	"""
	try:
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		current_approval_level = indent.get("approval_level") or 0
		branch_id = indent.get("branch_id")
		
		# Verify current status is Pending Approval (20)
		if current_status_id != 20:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot approve indent with status_id {current_status_id}. Expected status 20 (Pending Approval)."
			)
		
		# Get user's approval level and limits
		user_level_query = get_user_approval_level()
		user_level_result = db.execute(
			user_level_query,
			{"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
		).fetchone()
		
		if not user_level_result:
			raise HTTPException(
				status_code=403,
				detail="User does not have approval permission for this menu and branch."
			)
		
		user_data = dict(user_level_result._mapping)
		user_approval_level = user_data.get("approval_level")
		max_amount_single = user_data.get("max_amount_single")
		day_max_amount = user_data.get("day_max_amount")
		month_max_amount = user_data.get("month_max_amount")
		
		# Check if user can approve at current level
		if user_approval_level != current_approval_level:
			raise HTTPException(
				status_code=403,
				detail=f"User approval level ({user_approval_level}) does not match current indent approval level ({current_approval_level})."
			)
		
		# Check amount limits
		if max_amount_single is not None and document_amount > max_amount_single:
			raise HTTPException(
				status_code=403,
				detail=f"Document amount ({document_amount}) exceeds maximum single approval amount ({max_amount_single})."
			)
		
		# Get consumed amounts
		consumed_query = get_user_consumed_amounts()
		consumed_result = db.execute(
			consumed_query,
			{
				"menu_id": menu_id,
				"branch_id": branch_id,
				"user_id": user_id,
				"approval_level": user_approval_level,
			}
		).fetchone()
		
		if consumed_result:
			consumed = dict(consumed_result._mapping)
			# Note: This is a placeholder - actual implementation needs to track amounts, not just counts
			# day_consumed = consumed.get("day_count", 0)
			# month_consumed = consumed.get("month_count", 0)
			
			# TODO: Implement actual amount checking logic here
			# if day_max_amount is not None and (day_consumed + document_amount) > day_max_amount:
			#     raise HTTPException(...)
			# if month_max_amount is not None and (month_consumed + document_amount) > month_max_amount:
			#     raise HTTPException(...)
		
		# Get max approval level
		max_level_query = get_max_approval_level()
		max_level_result = db.execute(
			max_level_query,
			{"menu_id": menu_id, "branch_id": branch_id}
		).fetchone()
		
		max_approval_level = dict(max_level_result._mapping).get("max_level") if max_level_result else user_approval_level
		
		# Determine next status
		if user_approval_level >= max_approval_level:
			# Final level - approve
			new_status_id = 3  # Approved
			new_approval_level = user_approval_level
			message = "Indent approved (final level)."
		else:
			# Move to next level
			new_status_id = 20  # Still Pending Approval
			new_approval_level = current_approval_level + 1
			message = f"Indent moved to approval level {new_approval_level}."
		
		# Update indent status
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		db.execute(
			update_query,
			{
				"indent_id": indent_id,
				"status_id": new_status_id,
				"approval_level": new_approval_level,
				"updated_by": user_id,
				"updated_date_time": updated_at,
				"indent_no": None,  # Don't update indent_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": new_status_id,
			"new_approval_level": new_approval_level,
			"message": message,
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error processing approval with value")
		raise HTTPException(status_code=500, detail=str(e))


# ==================== APPROVAL API ENDPOINTS ====================

@router.get("/get_approval_flow")
async def get_approval_flow(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
	menu_id: Optional[int] = None,
	branch_id: Optional[int] = None,
):
	"""Get approval flow details for a menu and branch."""
	try:
		q_menu_id = request.query_params.get("menu_id")
		q_branch_id = request.query_params.get("branch_id")
		
		if q_menu_id is not None:
			try:
				menu_id = int(q_menu_id)
			except Exception:
				raise HTTPException(status_code=400, detail="Invalid menu_id")
		
		if q_branch_id is not None:
			try:
				branch_id = int(q_branch_id)
			except Exception:
				raise HTTPException(status_code=400, detail="Invalid branch_id")
		
		if menu_id is None:
			raise HTTPException(status_code=400, detail="menu_id is required")
		if branch_id is None:
			raise HTTPException(status_code=400, detail="branch_id is required")
		
		flow_details = get_approval_flow_details(menu_id, branch_id, db)
		
		return {
			"menu_id": menu_id,
			"branch_id": branch_id,
			"approval_flow": flow_details,
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching approval flow")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve_indent")
async def approve_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Approve an indent (without value check - indents don't have monetary amounts)."""
	try:
		indent_id = payload.get("indent_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		approval_level = payload.get("approval_level")  # Optional, for logging
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			indent_id = int(indent_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Process approval (indent is without value)
		result = process_approval_without_value(
			indent_id=indent_id,
			user_id=user_id,
			menu_id=menu_id,
			db=db,
		)
		
		return result
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error approving indent")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve_indent_with_value")
async def approve_indent_with_value(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Approve an indent with value checks (for documents with monetary amounts)."""
	try:
		indent_id = payload.get("indent_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		document_amount = payload.get("amount", 0.0)
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			indent_id = int(indent_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
			document_amount = float(document_amount)
		except (TypeError, ValueError) as e:
			raise HTTPException(status_code=400, detail=f"Invalid parameters: {str(e)}")
		
		user_id = int(token_data.get("user_id"))
		
		# Process approval with value checks
		result = process_approval_with_value(
			indent_id=indent_id,
			user_id=user_id,
			menu_id=menu_id,
			document_amount=document_amount,
			db=db,
		)
		
		return result
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error approving indent with value")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/open_indent")
async def open_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Open an indent (change status from 21 Drafted to 1 Open). Generates document number if not already generated."""
	try:
		indent_id = payload.get("indent_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			indent_id = int(indent_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		current_indent_no = indent.get("indent_no")
		indent_date = indent.get("indent_date")
		
		# Verify current status is Drafted (21)
		if current_status_id != 21:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot open indent with status_id {current_status_id}. Expected status 21 (Drafted)."
			)
		
		# Generate indent_no if not already set
		new_indent_no = None
		if not indent_date:
			raise HTTPException(
				status_code=400,
				detail="Indent date is required to generate indent number."
			)
		
		# Only generate if indent_no is NULL or 0
		if current_indent_no is None or current_indent_no == 0:
			# Calculate financial year boundaries
			if hasattr(indent_date, "year") and hasattr(indent_date, "month"):
				# Date object
				year = indent_date.year
				month = indent_date.month
			elif hasattr(indent_date, "date"):
				# Datetime object
				date_obj = indent_date.date()
				year = date_obj.year
				month = date_obj.month
			else:
				# String or other format - try to parse
				try:
					if isinstance(indent_date, str):
						date_obj = datetime.strptime(indent_date, "%Y-%m-%d").date()
					else:
						date_obj = datetime.fromisoformat(str(indent_date)).date()
					year = date_obj.year
					month = date_obj.month
				except Exception:
					raise HTTPException(
						status_code=400,
						detail=f"Invalid indent_date format: {indent_date}"
					)
			
			# Calculate financial year boundaries
			# Financial year: April 1 to March 31
			# If month >= 4 (April-December): FY = year-04-01 to (year+1)-03-31
			# If month < 4 (January-March): FY = (year-1)-04-01 to year-03-31
			if month >= 4:
				fy_start_year = year
				fy_end_year = year + 1
			else:
				fy_start_year = year - 1
				fy_end_year = year
			
			fy_start_date = datetime(fy_start_year, 4, 1).date()
			fy_end_date = datetime(fy_end_year, 3, 31).date()
			
			# Get max indent_no for this branch and financial year
			max_query = get_max_indent_no_for_branch_fy()
			max_result = db.execute(
				max_query,
				{
					"branch_id": branch_id,
					"fy_start_date": fy_start_date,
					"fy_end_date": fy_end_date,
				}
			).fetchone()
			
			if max_result:
				max_indent_no = dict(max_result._mapping).get("max_indent_no") or 0
				new_indent_no = max_indent_no + 1
			else:
				new_indent_no = 1
		
		# Update status to Open (1) and set indent_no if generated
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		update_params = {
			"indent_id": indent_id,
			"status_id": 1,  # Open
			"approval_level": None,  # Reset approval level
			"updated_by": user_id,
			"updated_date_time": updated_at,
		}
		# Only include indent_no if it was generated
		if new_indent_no is not None:
			update_params["indent_no"] = new_indent_no
		else:
			# Pass None to keep existing value
			update_params["indent_no"] = None
		
		db.execute(update_query, update_params)
		db.commit()
		
		# Return the indent_no that was set (either newly generated or existing)
		final_indent_no = new_indent_no if new_indent_no is not None else current_indent_no
		
		return {
			"status": "success",
			"new_status_id": 1,
			"message": "Indent opened successfully.",
			"indent_no": final_indent_no,
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error opening indent")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel_draft_indent")
async def cancel_draft_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Cancel a draft indent (change status from 21 Drafted to 6 Cancelled)."""
	try:
		indent_id = payload.get("indent_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			indent_id = int(indent_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		
		# Verify current status is Drafted (21)
		if current_status_id != 21:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot cancel indent with status_id {current_status_id}. Expected status 21 (Drafted)."
			)
		
		# Update status to Cancelled (6)
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		db.execute(
			update_query,
			{
				"indent_id": indent_id,
				"status_id": 6,  # Cancelled
				"approval_level": None,
				"updated_by": user_id,
				"updated_date_time": updated_at,
				"indent_no": None,  # Don't update indent_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": 6,
			"message": "Draft cancelled successfully.",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error cancelling draft indent")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/reopen_indent")
async def reopen_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Reopen an indent (change status from 6 Cancelled or 4 Rejected back to 1 Open or 21 Drafted)."""
	try:
		indent_id = payload.get("indent_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			indent_id = int(indent_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		
		# Determine target status based on current status
		if current_status_id == 6:  # Cancelled
			new_status_id = 21  # Back to Drafted
		elif current_status_id == 4:  # Rejected
			new_status_id = 1  # Back to Open
		else:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot reopen indent with status_id {current_status_id}. Only Cancelled (6) or Rejected (4) can be reopened."
			)
		
		# Update status
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		db.execute(
			update_query,
			{
				"indent_id": indent_id,
				"status_id": new_status_id,
				"approval_level": None,
				"updated_by": user_id,
				"updated_date_time": updated_at,
				"indent_no": None,  # Don't update indent_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": new_status_id,
			"message": f"Indent reopened successfully (status: {new_status_id}).",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error reopening indent")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/send_indent_for_approval")
async def send_indent_for_approval(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Send indent for approval (change status from 1 Open to 20 Pending Approval, set approval_level to 1)."""
	try:
		indent_id = payload.get("indent_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			indent_id = int(indent_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		
		# Verify current status is Open (1)
		if current_status_id != 1:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot send for approval indent with status_id {current_status_id}. Expected status 1 (Open)."
			)
		
		# Update status to Pending Approval (20) with level 1
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		db.execute(
			update_query,
			{
				"indent_id": indent_id,
				"status_id": 20,  # Pending Approval
				"approval_level": 1,  # Start at level 1
				"updated_by": user_id,
				"updated_date_time": updated_at,
				"indent_no": None,  # Don't update indent_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": 20,
			"new_approval_level": 1,
			"message": "Indent sent for approval successfully.",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error sending indent for approval")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject_indent")
async def reject_indent(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Reject an indent (change status from 20 Pending Approval to 4 Rejected)."""
	try:
		indent_id = payload.get("indent_id")
		co_id = payload.get("co_id")
		reason = payload.get("reason", "")
		
		if not indent_id:
			raise HTTPException(status_code=400, detail="indent_id is required")
		if not co_id:
			raise HTTPException(status_code=400, detail="co_id is required")
		
		try:
			indent_id = int(indent_id)
			co_id = int(co_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid indent_id or co_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get indent details
		indent_query = get_indent_with_approval_info()
		indent_result = db.execute(indent_query, {"indent_id": indent_id}).fetchone()
		if not indent_result:
			raise HTTPException(status_code=404, detail="Indent not found")
		
		indent = dict(indent_result._mapping)
		current_status_id = indent.get("status_id")
		
		# Verify current status is Pending Approval (20)
		if current_status_id != 20:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot reject indent with status_id {current_status_id}. Expected status 20 (Pending Approval)."
			)
		
		# Update status to Rejected (4)
		# TODO: Store rejection reason in a separate table or remarks field
		updated_at = datetime.utcnow()
		update_query = update_indent_status()
		db.execute(
			update_query,
			{
				"indent_id": indent_id,
				"status_id": 4,  # Rejected
				"approval_level": None,
				"updated_by": user_id,
				"updated_date_time": updated_at,
				"indent_no": None,  # Don't update indent_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": 4,
			"message": "Indent rejected successfully.",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error rejecting indent")
		raise HTTPException(status_code=500, detail=str(e))