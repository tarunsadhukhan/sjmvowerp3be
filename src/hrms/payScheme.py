"""HRMS Pay Scheme endpoints — list, detail, create, update, setup."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.models.hrms import PayComponents, PayEmployeeStructure
from .query import (
    get_pay_scheme_list,
    get_pay_scheme_by_id,
    get_pay_scheme_components,
    get_pay_scheme_create_setup,
)

router = APIRouter()


# ─── Pay Scheme List ────────────────────────────────────────────────

@router.get("/pay_scheme_list")
async def pay_scheme_list(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        search_raw = request.query_params.get("search")
        search = f"%{search_raw}%" if search_raw else None

        params = {
            "co_id": int(co_id),
            "search": search,
            "page_size": page_size,
            "offset": (page - 1) * page_size,
        }

        rows = db.execute(get_pay_scheme_list(), params).fetchall()
        data = [dict(r._mapping) for r in rows]

        return {"data": data, "page": page, "page_size": page_size}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Pay Scheme By ID ──────────────────────────────────────────────

@router.get("/pay_scheme_by_id/{scheme_id}")
async def pay_scheme_by_id(
    scheme_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        row = db.execute(
            get_pay_scheme_by_id(), {"id": scheme_id, "co_id": int(co_id)}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pay scheme not found")

        # Get components for this scheme
        components = db.execute(
            get_pay_scheme_components(), {"co_id": int(co_id)}
        ).fetchall()

        # Get structure entries for this scheme
        structure = (
            db.query(PayEmployeeStructure)
            .filter(PayEmployeeStructure.pay_scheme_id == scheme_id)
            .all()
        )

        return {
            "data": {
                "scheme": dict(row._mapping),
                "components": [dict(r._mapping) for r in components],
                "structure": [
                    {
                        "id": s.id,
                        "component_id": s.component_id,
                        "amount": s.amount,
                        "effective_from": str(s.effective_from) if s.effective_from else None,
                        "ends_on": str(s.ends_on) if s.ends_on else None,
                        "remarks": s.remarks,
                    }
                    for s in structure
                ],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Pay Scheme Create Setup ───────────────────────────────────────

@router.get("/pay_scheme_create_setup")
async def pay_scheme_create_setup(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        rows = db.execute(get_pay_scheme_create_setup(), {"co_id": int(co_id)}).fetchall()
        components = [dict(r._mapping) for r in rows]

        # Separate by type for frontend convenience
        earnings = [c for c in components if c.get("type") == 1]
        deductions = [c for c in components if c.get("type") == 2]
        summary = [c for c in components if c.get("type") == 3]
        inputs_ = [c for c in components if c.get("type") == 0]

        return {
            "data": {
                "all_components": components,
                "earnings": earnings,
                "deductions": deductions,
                "summary": summary,
                "inputs": inputs_,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Pay Scheme Create ─────────────────────────────────────────────

@router.post("/pay_scheme_create")
async def pay_scheme_create(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        body = await request.json()
        user_id = token_data.get("user_id", 0)

        scheme = PayComponents(
            code=body.get("code"),
            name=body.get("name"),
            description=body.get("description"),
            type=0,  # Pay scheme type
            co_id=int(co_id),
            status_id=1,
            updated_by=user_id,
        )
        db.add(scheme)
        db.flush()

        # Add structure components if provided
        for comp in body.get("components", []):
            structure = PayEmployeeStructure(
                pay_scheme_id=scheme.id,
                component_id=comp.get("component_id"),
                amount=comp.get("amount", 0),
                status_id=1,
                updated_by=user_id,
                eb_id=0,  # Template-level (not employee-specific)
            )
            db.add(structure)

        db.commit()
        return {"data": {"id": scheme.id, "message": "Pay scheme created successfully"}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Pay Scheme Update ─────────────────────────────────────────────

@router.put("/pay_scheme_update/{scheme_id}")
async def pay_scheme_update(
    scheme_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        body = await request.json()
        user_id = token_data.get("user_id", 0)

        scheme = (
            db.query(PayComponents)
            .filter(PayComponents.id == scheme_id, PayComponents.co_id == int(co_id))
            .first()
        )
        if not scheme:
            raise HTTPException(status_code=404, detail="Pay scheme not found")

        # Update scheme fields
        for field in ("code", "name", "description"):
            if field in body:
                setattr(scheme, field, body[field])
        scheme.updated_by = user_id

        # Update components if provided
        if "components" in body:
            # Remove existing structure for this scheme template
            db.query(PayEmployeeStructure).filter(
                PayEmployeeStructure.pay_scheme_id == scheme_id,
                PayEmployeeStructure.eb_id == 0,
            ).delete()

            for comp in body["components"]:
                structure = PayEmployeeStructure(
                    pay_scheme_id=scheme_id,
                    component_id=comp.get("component_id"),
                    amount=comp.get("amount", 0),
                    status_id=1,
                    updated_by=user_id,
                    eb_id=0,
                )
                db.add(structure)

        db.commit()
        return {"data": {"id": scheme_id, "message": "Pay scheme updated successfully"}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
