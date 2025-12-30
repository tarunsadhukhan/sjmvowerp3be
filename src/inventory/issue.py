"""
FastAPI router for inventory issue endpoints.
"""
from fastapi import Depends, Request, HTTPException, APIRouter
import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.inventory.query import (
    get_issue_table_query,
    get_issue_table_count_query,
    get_issue_by_id_query,
    get_issue_details_query,
    insert_issue_hdr,
    insert_issue_li,
    update_issue_hdr,
    delete_issue_li,
    get_max_issue_pass_no_for_branch,
    update_issue_status,
)
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_issue_table")
async def get_issue_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    co_id: int | None = None,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
):
    """
    Get paginated list of inventory issues for the index table.
    
    Args:
        co_id: Company ID to filter issues
        page: Page number (1-indexed)
        limit: Number of records per page
        search: Search term to filter by issue no, branch, department, expense type
    
    Returns:
        {
            "data": [...],
            "total": int,
            "page": int,
            "page_size": int
        }
    """
    try:
        # Parse query params
        q_co_id = request.query_params.get("co_id")
        q_page = request.query_params.get("page")
        q_limit = request.query_params.get("limit")
        q_search = request.query_params.get("search")

        if q_co_id is not None:
            try:
                co_id = int(q_co_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid co_id")

        if q_page is not None:
            try:
                page = int(q_page)
            except Exception:
                page = 1

        if q_limit is not None:
            try:
                limit = int(q_limit)
            except Exception:
                limit = 10

        if q_search is not None:
            search = q_search.strip() if q_search else None

        # Validate pagination
        if page < 1:
            page = 1
        if limit < 1:
            limit = 10
        if limit > 100:
            limit = 100

        offset = (page - 1) * limit
        search_like = f"%{search}%" if search else None

        # Get total count
        count_query = get_issue_table_count_query()
        count_result = db.execute(
            count_query,
            {"co_id": co_id, "search_like": search_like}
        ).fetchone()
        total = count_result.total if count_result else 0

        # Get paginated data
        data_query = get_issue_table_query()
        rows = db.execute(
            data_query,
            {
                "co_id": co_id,
                "search_like": search_like,
                "limit": limit,
                "offset": offset,
            }
        ).fetchall()

        data = []
        for row in rows:
            row_dict = dict(row._mapping)
            # Format issue date
            if row_dict.get("issue_date"):
                row_dict["issue_date"] = str(row_dict["issue_date"])
            data.append(row_dict)

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching issue table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_issue_by_id/{issue_id}")
async def get_issue_by_id(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get issue details by ID including header and line items.
    
    Args:
        issue_id: The issue ID to fetch
    
    Returns:
        Issue header with nested line items
    """
    try:
        # Get header
        header_query = get_issue_by_id_query()
        header_row = db.execute(header_query, {"issue_id": issue_id}).fetchone()

        if not header_row:
            raise HTTPException(status_code=404, detail="Issue not found")

        header = dict(header_row._mapping)
        
        # Format dates
        if header.get("issue_date"):
            header["issue_date"] = str(header["issue_date"])
        if header.get("updated_date_time"):
            header["updated_date_time"] = str(header["updated_date_time"])

        # Get line items
        details_query = get_issue_details_query()
        detail_rows = db.execute(details_query, {"issue_id": issue_id}).fetchall()
        
        lines = []
        for row in detail_rows:
            line = dict(row._mapping)
            lines.append(line)

        header["lines"] = lines

        return header

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching issue by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_issue_setup_1")
async def get_issue_setup_1(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    branch_id: int | None = None,
    co_id: int | None = None,
):
    """
    Get setup data for creating/editing an issue.
    Returns branches, departments, expense types, projects, and item groups.
    """
    try:
        from src.masters.query import get_branch_list, get_dept_list_by_branch_id, get_item_group_drodown
        from src.procurement.query import get_project, get_expense_types

        # Parse query params
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

        # Get branches
        branch_ids_list = [branch_id] if branch_id is not None else None
        branch_query = get_branch_list(branch_ids=branch_ids_list) if branch_ids_list else get_branch_list()
        branch_result = db.execute(branch_query, {"branch_ids": branch_ids_list} if branch_ids_list else {}).fetchall()
        branches = [dict(r._mapping) for r in branch_result]

        # Get departments
        dept_query = get_dept_list_by_branch_id(branch_ids_list if branch_ids_list is not None else [])
        dept_result = db.execute(dept_query, {"branch_ids": branch_ids_list, "co_id": co_id}).fetchall()
        departments = [dict(r._mapping) for r in dept_result]

        # Get projects
        projects = []
        if branch_id is not None:
            project_query = get_project(branch_id=branch_id)
            proj_result = db.execute(project_query, {"branch_id": branch_id}).fetchall()
            projects = [dict(r._mapping) for r in proj_result]

        # Get expense types
        expense_query = get_expense_types()
        exp_result = db.execute(expense_query).fetchall()
        expense_types = [dict(r._mapping) for r in exp_result]

        # Get item groups
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
        logger.error(f"Error fetching issue setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
