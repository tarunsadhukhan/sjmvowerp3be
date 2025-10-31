from fastapi import Depends, Request, HTTPException, APIRouter
import os
import logging
from sqlalchemy.orm import Session
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
)
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


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
			indent_date = mapped.get("indent_date")
			if hasattr(indent_date, "isoformat"):
				indent_date = indent_date.isoformat()
			data.append(
				{
					"indent_id": mapped.get("indent_id"),
					"indent_no": mapped.get("indent_no"),
					"indent_date": indent_date,
					"branch_name": mapped.get("branch_name"),
					"expense_type": mapped.get("expense_type_name"),
					"status": mapped.get("status_name"),
				}
			)

		count_query = get_indent_table_count_query()
		count_params = {"co_id": co_id, "search_like": search_like}
		total_row = db.execute(count_query, count_params).fetchone()
		total = int(total_row[0]) if total_row and total_row[0] is not None else len(data)

		return {
			"data": data,
			"page": page,
			"pageSize": limit,
			"total": total,
		}
	except HTTPException:
		raise
	except Exception as e:
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
			"status_id": None,
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