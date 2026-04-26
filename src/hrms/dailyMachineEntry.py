"""
HRMS Daily Machine Entry endpoints.

Provides CRUD for tbl_daily_summ_mechine_data and a lookup against
mechine_code_master for validating mc_code.

Inputs per row: tran_date, mc_code (validated), shift_a, shift_b, shift_c.
total_mc is derived = shift_a + shift_b + shift_c.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from src.authorization.utils import get_current_user_with_refresh
from src.config.db import get_tenant_db

router = APIRouter()


# ─── SQL ────────────────────────────────────────────────────────────


def _list_query():
    return text("""
        SELECT
            d.daily_sum_mc_id,
            d.tran_date,
            d.mc_code_id,
            m.mc_code,
            m.Mechine_type_name AS mc_name,
            d.shift_a,
            d.shift_b,
            d.shift_c,
            (COALESCE(d.shift_a,0) + COALESCE(d.shift_b,0) + COALESCE(d.shift_c,0)) AS total_mc,
            d.company_id,
            d.branch_id,
            d.is_active,
            d.created_on
        FROM tbl_daily_summ_mechine_data d
        LEFT JOIN mechine_code_master m ON m.mc_code_id = d.mc_code_id
        WHERE COALESCE(d.is_active, 1) = 1
          AND d.company_id = :company_id
          AND (:search IS NULL
               OR m.mc_code LIKE :search
               OR m.Mechine_type_name LIKE :search
               OR DATE_FORMAT(d.tran_date, '%Y-%m-%d') LIKE :search)
        ORDER BY d.tran_date DESC, d.daily_sum_mc_id DESC
    """)


def _by_id_query():
    return text("""
        SELECT
            d.daily_sum_mc_id,
            d.tran_date,
            d.mc_code_id,
            m.mc_code,
            m.Mechine_type_name AS mc_name,
            d.shift_a,
            d.shift_b,
            d.shift_c,
            (COALESCE(d.shift_a,0) + COALESCE(d.shift_b,0) + COALESCE(d.shift_c,0)) AS total_mc,
            d.company_id,
            d.branch_id,
            d.is_active
        FROM tbl_daily_summ_mechine_data d
        LEFT JOIN mechine_code_master m ON m.mc_code_id = d.mc_code_id
        WHERE d.daily_sum_mc_id = :daily_sum_mc_id
    """)


# ─── Endpoints ──────────────────────────────────────────────────────


@router.get("/daily_machine_lookup_mc")
async def daily_machine_lookup_mc(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Validate an mc_code against mechine_code_master and return its id + name."""
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        mc_code = (request.query_params.get("mc_code") or "").strip()
        if not mc_code:
            raise HTTPException(status_code=400, detail="mc_code is required")

        row = db.execute(
            text("""
                SELECT mc_code_id, mc_code, Mechine_type_name AS mc_name,
                       company_id, branch_id
                FROM mechine_code_master
                WHERE mc_code = :mc_code
                  AND COALESCE(is_active, 1) = 1
                LIMIT 1
            """),
            {"mc_code": mc_code},
        ).fetchone()

        if not row:
            return {"found": False, "data": None}
        return {"found": True, "data": dict(row._mapping)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_daily_machine_table")
async def get_daily_machine_table(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Paginated list of daily machine entries."""
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        search = request.query_params.get("search")
        search_param = f"%{search}%" if search else None

        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        result = db.execute(
            _list_query(),
            {"company_id": int(co_id), "search": search_param},
        ).fetchall()

        all_data = [dict(r._mapping) for r in result]
        total = len(all_data)
        start = (page - 1) * limit
        return {
            "data": all_data[start : start + limit],
            "total": total,
            "page": page,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_daily_machine_by_id/{daily_sum_mc_id}")
async def get_daily_machine_by_id(
    daily_sum_mc_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Single daily machine entry by id."""
    try:
        row = db.execute(
            _by_id_query(), {"daily_sum_mc_id": daily_sum_mc_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Daily machine entry not found")
        return {"data": dict(row._mapping)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_decimal(value, field: str):
    """Return float for shift inputs; allow None / empty."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field} must be numeric")


def _resolve_mc_code_id(db: Session, body: dict) -> tuple[int, int | None, int | None]:
    """Return (mc_code_id, company_id, branch_id) by validating mc_code."""
    mc_code_id = body.get("mc_code_id")
    if mc_code_id:
        row = db.execute(
            text("""
                SELECT mc_code_id, company_id, branch_id
                FROM mechine_code_master
                WHERE mc_code_id = :mc_code_id
                  AND COALESCE(is_active, 1) = 1
                LIMIT 1
            """),
            {"mc_code_id": int(mc_code_id)},
        ).fetchone()
    else:
        mc_code = (body.get("mc_code") or "").strip()
        if not mc_code:
            raise HTTPException(status_code=400, detail="mc_code is required")
        row = db.execute(
            text("""
                SELECT mc_code_id, company_id, branch_id
                FROM mechine_code_master
                WHERE mc_code = :mc_code
                  AND COALESCE(is_active, 1) = 1
                LIMIT 1
            """),
            {"mc_code": mc_code},
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=400, detail="mc_code not found in machine master"
        )
    return int(row.mc_code_id), row.company_id, row.branch_id


@router.post("/daily_machine_create")
async def daily_machine_create(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Insert a daily machine entry."""
    try:
        body = await request.json()

        co_id = body.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        tran_date = body.get("tran_date")
        if not tran_date:
            raise HTTPException(status_code=400, detail="tran_date is required")

        mc_code_id, mc_company_id, mc_branch_id = _resolve_mc_code_id(db, body)

        shift_a = _parse_decimal(body.get("shift_a"), "shift_a") or 0
        shift_b = _parse_decimal(body.get("shift_b"), "shift_b") or 0
        shift_c = _parse_decimal(body.get("shift_c"), "shift_c") or 0

        # Optional duplicate-guard: same date + mc_code_id already exists
        dup = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM tbl_daily_summ_mechine_data
                WHERE tran_date = :tran_date
                  AND mc_code_id = :mc_code_id
                  AND COALESCE(is_active, 1) = 1
            """),
            {"tran_date": tran_date, "mc_code_id": mc_code_id},
        ).fetchone()
        if dup and int(dup.cnt or 0) > 0:
            raise HTTPException(
                status_code=400,
                detail="An entry already exists for this date and machine code",
            )

        branch_id = body.get("branch_id") or mc_branch_id

        db.execute(
            text("""
                INSERT INTO tbl_daily_summ_mechine_data
                    (tran_date, mc_code_id, shift_a, shift_b, shift_c,
                     company_id, branch_id, is_active, created_on)
                VALUES
                    (:tran_date, :mc_code_id, :shift_a, :shift_b, :shift_c,
                     :company_id, :branch_id, 1, :created_on)
            """),
            {
                "tran_date": tran_date,
                "mc_code_id": mc_code_id,
                "shift_a": shift_a,
                "shift_b": shift_b,
                "shift_c": shift_c,
                "company_id": int(co_id),
                "branch_id": int(branch_id) if branch_id is not None else None,
                "created_on": datetime.now(),
            },
        )
        db.commit()
        _ = mc_company_id  # unused but kept for symmetry

        return {"message": "Daily machine entry created successfully"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/daily_machine_edit/{daily_sum_mc_id}")
async def daily_machine_edit(
    daily_sum_mc_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Update a daily machine entry."""
    try:
        body = await request.json()

        existing = db.execute(
            text("""
                SELECT daily_sum_mc_id, company_id, branch_id
                FROM tbl_daily_summ_mechine_data
                WHERE daily_sum_mc_id = :id
            """),
            {"id": daily_sum_mc_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Daily machine entry not found")

        tran_date = body.get("tran_date")
        if not tran_date:
            raise HTTPException(status_code=400, detail="tran_date is required")

        mc_code_id, _mc_co, mc_branch_id = _resolve_mc_code_id(db, body)

        shift_a = _parse_decimal(body.get("shift_a"), "shift_a") or 0
        shift_b = _parse_decimal(body.get("shift_b"), "shift_b") or 0
        shift_c = _parse_decimal(body.get("shift_c"), "shift_c") or 0

        # Duplicate-guard excluding self
        dup = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM tbl_daily_summ_mechine_data
                WHERE tran_date = :tran_date
                  AND mc_code_id = :mc_code_id
                  AND daily_sum_mc_id != :id
                  AND COALESCE(is_active, 1) = 1
            """),
            {
                "tran_date": tran_date,
                "mc_code_id": mc_code_id,
                "id": daily_sum_mc_id,
            },
        ).fetchone()
        if dup and int(dup.cnt or 0) > 0:
            raise HTTPException(
                status_code=400,
                detail="An entry already exists for this date and machine code",
            )

        branch_id = body.get("branch_id") or mc_branch_id

        db.execute(
            text("""
                UPDATE tbl_daily_summ_mechine_data
                SET tran_date  = :tran_date,
                    mc_code_id = :mc_code_id,
                    shift_a    = :shift_a,
                    shift_b    = :shift_b,
                    shift_c    = :shift_c,
                    branch_id  = COALESCE(:branch_id, branch_id)
                WHERE daily_sum_mc_id = :id
            """),
            {
                "tran_date": tran_date,
                "mc_code_id": mc_code_id,
                "shift_a": shift_a,
                "shift_b": shift_b,
                "shift_c": shift_c,
                "branch_id": int(branch_id) if branch_id is not None else None,
                "id": daily_sum_mc_id,
            },
        )
        db.commit()
        return {
            "message": "Daily machine entry updated successfully",
            "daily_sum_mc_id": daily_sum_mc_id,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
