from fastapi import Depends, Request, HTTPException, APIRouter, Response, Cookie
import os
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names, default_engine, get_tenant_db
from src.authorization.utils import  get_current_user_with_refresh
# from src.masters.schemas import MenuResponse
from src.masters.models import CostFactorMst
from src.masters.query import  get_branch_list, get_dept_list_by_branch_id, get_item_group_drodown
from src.procurement.query import get_project, get_expense_types, get_item_by_group_id_purchaseable
from src.procurement.query import get_item_make_by_group_id, get_item_uom_by_group_id
from datetime import datetime

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