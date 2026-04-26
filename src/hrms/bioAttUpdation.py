"""HRMS Bio Attendance bulk upload endpoints.

Flow:
  1. Client POSTs file to `/bio_att_upload`.
     - If `temp_bio_attendance_table` already has rows, the request is
       refused with "Another process Working".
     - Otherwise the file is parsed and bulk-inserted into the temp table
       *without any validation* (fast path).
     - A background job is queued that streams rows from the temp table,
       validates them against `bio_attendance_table` (duplicate check across
       the 10-column signature), inserts the survivors, and finally truncates
       the temp table.
  2. Client polls `/bio_att_excel_status/{job_id}` for progress.
  3. Client may call `/bio_att_clear` at any time to wipe the temp table.

Endpoints:
  - GET  /bio_att_list
  - POST /bio_att_upload
  - POST /bio_att_clear
  - GET  /bio_att_excel_status/{job_id}
"""

from __future__ import annotations

import csv
import io
import os
import traceback
import uuid
from datetime import datetime, date, time as dt_time, timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import text

from src.authorization.utils import get_current_user_with_refresh
from src.config.db import extract_subdomain_from_request, get_engine, get_tenant_db

router = APIRouter()

BATCH_SIZE = 2000  # rows per INSERT into the temp table


# ---------------------------------------------------------------------------
# Job-status persistence (bio_att_jobs table — survives across uvicorn workers)
# ---------------------------------------------------------------------------

_JOB_FIELDS = (
    "status", "total", "processed", "inserted",
    "duplicates", "invalid", "message", "error",
)

_JOB_UPSERT_SQL = text(
    """
    INSERT INTO bio_att_jobs
        (job_id, status, total, processed, inserted, duplicates, invalid, message, error)
    VALUES
        (:job_id, :status, :total, :processed, :inserted, :duplicates, :invalid, :message, :error)
    ON DUPLICATE KEY UPDATE
        status     = COALESCE(VALUES(status), status),
        total      = COALESCE(VALUES(total), total),
        processed  = COALESCE(VALUES(processed), processed),
        inserted   = COALESCE(VALUES(inserted), inserted),
        duplicates = COALESCE(VALUES(duplicates), duplicates),
        invalid    = COALESCE(VALUES(invalid), invalid),
        message    = COALESCE(VALUES(message), message),
        error      = COALESCE(VALUES(error), error)
    """
)

_JOB_SELECT_SQL = text(
    """
    SELECT job_id, status, total, processed, inserted, duplicates, invalid,
           message, error, created_at, updated_at
    FROM bio_att_jobs WHERE job_id = :job_id
    """
)


def _set_job(db: Session, job_id: str, **fields) -> None:
    """UPSERT a row in bio_att_jobs. Unspecified fields are left untouched."""
    params: dict = {f: None for f in _JOB_FIELDS}
    params.update({k: v for k, v in fields.items() if k in _JOB_FIELDS})
    params["job_id"] = job_id
    db.execute(_JOB_UPSERT_SQL, params)
    db.commit()


def _get_job(db: Session, job_id: str) -> dict | None:
    row = db.execute(_JOB_SELECT_SQL, {"job_id": job_id}).fetchone()
    if not row:
        return None
    d = dict(row._mapping)
    for ts_field in ("created_at", "updated_at"):
        v = d.get(ts_field)
        if isinstance(v, datetime):
            d[ts_field] = v.strftime("%Y-%m-%d %H:%M:%S")
    return d


# Columns that compose the duplicate signature in bio_attendance_table
DUP_COLUMNS = [
    "emp_code",
    "emp_anme",
    "bio_id",
    "log_date",
    "company_name",
    "department",
    "designation",
    "employement_type",
    "device_direction",
    "device_name",
]

# Mapping accepted column headers (lowercased) -> table column name.
# Both the device-style CSV and the table-style headers are accepted.
HEADER_ALIASES = {
    "employee code": "emp_code",
    "emp_code": "emp_code",

    "employee name": "emp_anme",
    "emp_anme": "emp_anme",
    "emp_name": "emp_anme",

    "employee code in device": "bio_id",
    "bio_id": "bio_id",

    "logdate": "log_date",
    "log date": "log_date",
    "log_date": "log_date",

    "company": "company_name",
    "company_name": "company_name",

    "department": "department",
    "designation": "designation",

    "employement type": "employement_type",
    "employment type": "employement_type",
    "employement_type": "employement_type",

    "direction": "device_direction",
    "device_direction": "device_direction",

    "device name": "device_name",
    "device_name": "device_name",
}

IGNORED_HEADERS = {"category"}


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


@router.get("/bio_att_list")
async def bio_att_list(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Paginated bio-attendance listing."""
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        search = request.query_params.get("search")
        offset = max(page - 1, 0) * limit

        params: dict = {"limit": limit, "offset": offset}
        where = ""
        if search:
            where = (
                " WHERE emp_code LIKE :s OR emp_anme LIKE :s "
                " OR device_name LIKE :s OR department LIKE :s"
            )
            params["s"] = f"%{search}%"

        rows = db.execute(
            text(f"""
                SELECT bio_att_id, emp_code, emp_anme, bio_id, log_date,
                       company_name, department, designation,
                       employement_type, device_direction, device_name
                FROM bio_attendance_table
                {where}
                ORDER BY log_date DESC, bio_att_id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()

        total = db.execute(
            text(f"SELECT COUNT(*) AS cnt FROM bio_attendance_table {where}"),
            {k: v for k, v in params.items() if k == "s"},
        ).fetchone()

        data = []
        for r in rows:
            d = dict(r._mapping)
            ld = d.get("log_date")
            if isinstance(ld, datetime):
                d["log_date"] = ld.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(ld, date):
                d["log_date"] = ld.isoformat()
            data.append(d)

        return {
            "data": data,
            "total": int(total.cnt) if total else 0,
            "page": page,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily_att_list")
async def daily_att_list(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Paginated daily_attendance_process_table listing."""
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        search = request.query_params.get("search")
        offset = max(page - 1, 0) * limit

        params: dict = {"limit": limit, "offset": offset}
        where = ""
        if search:
            where = (
                " WHERE CAST(d.eb_id AS CHAR) LIKE :s "
                " OR o.emp_code LIKE :s "
                " OR CONCAT_WS(' ', p.first_name, IFNULL(p.middle_name,''), IFNULL(p.last_name,'')) LIKE :s "
                " OR b.department LIKE :s "
                " OR b.designation LIKE :s "
                " OR d.spell_name LIKE :s "
                " OR d.attendance_type LIKE :s "
                " OR d.device_name LIKE :s "
                " OR CAST(d.attendance_date AS CHAR) LIKE :s"
            )
            params["s"] = f"%{search}%"

        rows = db.execute(
            text(f"""
                SELECT d.daily_att_proc_id, d.eb_id, d.bio_id,
                       o.emp_code AS emp_code,
                       TRIM(CONCAT_WS(' ', p.first_name,
                                          IFNULL(p.middle_name,''),
                                          IFNULL(p.last_name,''))) AS emp_name,
                       b.department AS department,
                       b.designation AS designation,
                       d.attendance_date, d.spell_name, d.attendance_type,
                       d.attendance_source, d.check_in, d.check_out,
                       d.Time_duration, d.Working_hours, d.Ot_hours,
                       d.spell_start_time, d.spell_end_time, d.spell_hours,
                       d.processed, d.device_name
                FROM daily_attendance_process_table d
                LEFT JOIN hrms_ed_official_details o ON o.eb_id = d.eb_id
                LEFT JOIN hrms_ed_personal_details p ON p.eb_id = d.eb_id
                LEFT JOIN bio_attendance_table b     ON b.bio_att_id = d.bio_id
                {where}
                ORDER BY d.attendance_date DESC, d.daily_att_proc_id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()

        total = db.execute(
            text(
                f"""SELECT COUNT(*) AS cnt
                    FROM daily_attendance_process_table d
                    LEFT JOIN hrms_ed_official_details o ON o.eb_id = d.eb_id
                    LEFT JOIN hrms_ed_personal_details p ON p.eb_id = d.eb_id
                    LEFT JOIN bio_attendance_table b     ON b.bio_att_id = d.bio_id
                    {where}"""
            ),
            {k: v for k, v in params.items() if k == "s"},
        ).fetchone()

        def _fmt(v):
            if isinstance(v, datetime):
                return v.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(v, date):
                return v.isoformat()
            if isinstance(v, timedelta):
                # MySQL TIME columns come back as timedelta in PyMySQL.
                total_seconds = int(v.total_seconds())
                h, rem = divmod(total_seconds, 3600)
                m, s = divmod(rem, 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return v

        data = [{k: _fmt(v) for k, v in r._mapping.items()} for r in rows]

        return {
            "data": data,
            "total": int(total.cnt) if total else 0,
            "page": page,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_log_date(value):
    """Parse a cell value into a datetime. Returns None if invalid."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    s = str(value).strip()
    if not s:
        return None
    fmts = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _to_int_or_none(value):
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _str_or_empty(value):
    return "" if value is None else str(value).strip()


def _resolve_header(raw):
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if key in IGNORED_HEADERS:
        return None
    return HEADER_ALIASES.get(key)


def _read_upload(file_bytes: bytes, filename: str) -> list[dict]:
    """Return parsed rows from CSV / xlsx upload. Only structural validation
    (required columns must be present); no row-level validation is done here."""
    try:
        import openpyxl
    except ImportError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"openpyxl not installed: {e}")

    is_csv = (filename or "").lower().endswith(".csv")

    if is_csv:
        try:
            text_content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text_content = file_bytes.decode("latin-1")
        reader = csv.reader(io.StringIO(text_content))
        wb = openpyxl.Workbook()
        ws = wb.active
        for csv_row in reader:
            ws.append(csv_row)
    else:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Excel file: {e}")
        ws = wb.active

    rows_iter = ws.iter_rows(values_only=False)
    try:
        header_cells = next(rows_iter)
    except StopIteration:
        raise HTTPException(status_code=400, detail="File is empty")

    col_idx: dict[str, int] = {}
    for idx, cell in enumerate(header_cells):
        db_col = _resolve_header(cell.value)
        if db_col and db_col not in col_idx:
            col_idx[db_col] = idx

    missing = [c for c in DUP_COLUMNS if c not in col_idx]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}",
        )

    rows: list[dict] = []
    for row_cells in rows_iter:
        values = [c.value for c in row_cells]
        if all((v is None or (isinstance(v, str) and not v.strip())) for v in values):
            continue

        def _val(name: str):
            i = col_idx[name]
            return values[i] if i < len(values) else None

        rows.append({
            "emp_code": _str_or_empty(_val("emp_code")) or None,
            "emp_anme": _str_or_empty(_val("emp_anme")) or None,
            "bio_id": _to_int_or_none(_val("bio_id")),
            "log_date": _parse_log_date(_val("log_date")),
            "company_name": _str_or_empty(_val("company_name")) or None,
            "department": _str_or_empty(_val("department")) or None,
            "designation": _str_or_empty(_val("designation")) or None,
            "employement_type": _str_or_empty(_val("employement_type")) or None,
            "device_direction": _str_or_empty(_val("device_direction")) or None,
            "device_name": _str_or_empty(_val("device_name")) or None,
        })
    return rows


# ---------------------------------------------------------------------------
# SQL constants
# ---------------------------------------------------------------------------

TEMP_INSERT_SQL = text(
    """
    INSERT INTO temp_bio_attendance_table
        (emp_code, emp_anme, bio_id, log_date, company_name,
         department, designation, employement_type,
         device_direction, device_name)
    VALUES
        (:emp_code, :emp_anme, :bio_id, :log_date, :company_name,
         :department, :designation, :employement_type,
         :device_direction, :device_name)
    """
)

TEMP_COUNT_SQL = text("SELECT COUNT(*) AS cnt FROM temp_bio_attendance_table")
TEMP_DELETE_SQL = text("DELETE FROM temp_bio_attendance_table")

# Only rows captured from these devices are eligible to move into
# bio_attendance_table. Anything else is treated as invalid/ignored.
ALLOWED_DEVICE_NAMES = ("AIFace(Mars) Out-F", "AIFace(Mars) In-F")

# Count rows that would be rejected as invalid (missing emp_code or log_date,
# or device_name not in the allow-list).
INVALID_COUNT_SQL = text(
    """
    SELECT COUNT(*) AS cnt
    FROM temp_bio_attendance_table
    WHERE emp_code IS NULL OR emp_code = '' OR log_date IS NULL
       OR device_name IS NULL
       OR device_name NOT IN ('AIFace(Mars) Out-F', 'AIFace(Mars) In-F')
    """
)

# Set-difference move: temp MINUS bio (NULL-safe on all 10 cols).
# Equivalent to:
#   SELECT * FROM temp
#   MINUS
#   SELECT * FROM bio
# but expressed with NOT EXISTS so MySQL can use indexes.
BULK_INSERT_SQL = text(
    """
    INSERT INTO bio_attendance_table
        (emp_code, emp_anme, bio_id, log_date, company_name,
         department, designation, employement_type,
         device_direction, device_name)
    SELECT t.emp_code, t.emp_anme, t.bio_id, t.log_date, t.company_name,
           t.department, t.designation, t.employement_type,
           t.device_direction, t.device_name
    FROM temp_bio_attendance_table t
    WHERE t.emp_code IS NOT NULL AND t.emp_code <> ''
      AND t.log_date IS NOT NULL
      AND t.device_name IN ('AIFace(Mars) Out-F', 'AIFace(Mars) In-F')
      AND NOT EXISTS (
          SELECT 1 FROM bio_attendance_table b
          WHERE b.emp_code = t.emp_code
            AND b.log_date = t.log_date
            AND b.emp_anme <=> t.emp_anme
            AND b.bio_id <=> t.bio_id
            AND b.company_name <=> t.company_name
            AND b.department <=> t.department
            AND b.designation <=> t.designation
            AND b.employement_type <=> t.employement_type
            AND b.device_direction <=> t.device_direction
            AND b.device_name <=> t.device_name
      )
    """
)


# ---------------------------------------------------------------------------
# Link-master back-fill (runs after BULK_INSERT_SQL).
#
# tbl_master_bio_link_mst columns (per user):
#   match_type   CHAR(1)        -- 'E', 'D', 'O', 'B'
#   bio_data     VARCHAR(...)   -- raw text as it appears in bio_attendance_table
#   master_id    INT            -- internal id from sjm masters
#
# Mapping:
#   E : bio_data = bio_attendance_table.emp_code     -> eb_id
#   D : bio_data = bio_attendance_table.department   -> dept_id
#   O : bio_data = bio_attendance_table.designation  -> desig_id
#   B : bio_data = bio_attendance_table.device_name  -> device_id
# ---------------------------------------------------------------------------

# (match_type, bio_attendance target column, bio_attendance source column)
_LINK_UPDATE_TEMPLATES = (
    ("E", "eb_id",     "emp_code"),
    ("D", "dept_id",   "department"),
    ("O", "desig_id",  "designation"),
    ("B", "device_id", "device_name"),
)


def _backfill_links(db: Session) -> dict:
    """Populate eb_id / dept_id / desig_id / device_id on bio_attendance_table
    using tbl_master_bio_link_mst (columns: match_type, bio_data, master_id).
    Returns rowcounts per match_type. Each UPDATE is wrapped so a failure
    on one (e.g. missing column on bio_attendance_table) doesn't abort
    the others."""
    counts: dict = {"E": 0, "D": 0, "O": 0, "B": 0, "errors": []}
    for code, target_col, match_col in _LINK_UPDATE_TEMPLATES:
        sql = text(
            f"""
            UPDATE bio_attendance_table b
            JOIN tbl_master_bio_link_mst m
                ON m.match_type = :code
               AND m.bio_data = b.{match_col}
            SET b.{target_col} = m.master_id
            """
        )
        try:
            res = db.execute(sql, {"code": code})
            counts[code] = int(res.rowcount or 0)
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            counts["errors"].append(f"{code}: {type(e).__name__}: {e}")
    return counts


# ---------------------------------------------------------------------------
# Background validate-and-move worker
# ---------------------------------------------------------------------------


def _make_session(subdomain: str) -> Session:
    tenant_url = (
        f"mysql+pymysql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}"
        f"@{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{subdomain}"
    )
    engine = get_engine(tenant_url)
    SessionTenant = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionTenant()


def _run_validate_and_move(job_id: str, subdomain: str) -> None:
    """Set-based move: ``temp MINUS bio`` -> ``bio_attendance_table``.
    The temp table is **not** deleted afterwards (use /bio_att_clear).
    Status is persisted to ``bio_att_jobs`` so any uvicorn worker can read it.
    """
    db = _make_session(subdomain)

    try:
        total = int((db.execute(TEMP_COUNT_SQL).fetchone() or {"cnt": 0}).cnt)
        _set_job(
            db, job_id,
            status="running", total=total, processed=0,
            inserted=0, duplicates=0, invalid=0,
        )

        invalid = int((db.execute(INVALID_COUNT_SQL).fetchone() or {"cnt": 0}).cnt)

        # Single statement: insert rows that exist in temp but not in bio.
        result = db.execute(BULK_INSERT_SQL)
        inserted = int(result.rowcount or 0)
        db.commit()

        duplicates = max(total - invalid - inserted, 0)

        # Back-fill eb_id / dept_id / desig_id / device_id from the
        # link master. Best-effort — failures don't abort the upload.
        try:
            link_counts = _backfill_links(db)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            link_counts = {"errors": ["backfill failed"]}

        # Wipe the staging table now that the move has been committed.
        try:
            db.execute(TEMP_DELETE_SQL)
            db.commit()
        except Exception:
            db.rollback()

        link_msg = (
            f" Linked: E={link_counts.get('E', 0)}, D={link_counts.get('D', 0)}, "
            f"O={link_counts.get('O', 0)}, B={link_counts.get('B', 0)}."
        )
        if link_counts.get("errors"):
            link_msg += f" Link errors: {'; '.join(link_counts['errors'])}"

        _set_job(
            db, job_id,
            status="completed",
            total=total,
            processed=total,
            inserted=inserted,
            duplicates=duplicates,
            invalid=invalid,
            message="Upload completed." + link_msg,
        )
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            _set_job(
                db, job_id,
                status="failed",
                error=f"{e}\n{traceback.format_exc()}"[:60000],
            )
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/bio_att_upload")
async def bio_att_upload(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Bulk-load the uploaded file into the temp table, then queue a
    background job that validates and moves the data into the main table."""
    co_id = request.query_params.get("co_id")
    if not co_id:
        raise HTTPException(status_code=400, detail="co_id is required")

    # Refuse if a previous batch is still parked in the temp table.
    existing = db.execute(TEMP_COUNT_SQL).fetchone()
    if existing and int(existing.cnt) > 0:
        raise HTTPException(status_code=409, detail="Another process Working")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    rows = _read_upload(file_bytes, file.filename or "")
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found")

    # Bulk insert into temp table in batches (no row-level validation).
    try:
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            db.execute(TEMP_INSERT_SQL, batch)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed loading temp table: {e}")

    subdomain = extract_subdomain_from_request(request)
    job_id = uuid.uuid4().hex
    _set_job(
        db, job_id,
        status="queued",
        total=len(rows),
        processed=0,
        inserted=0,
        duplicates=0,
        invalid=0,
    )
    background_tasks.add_task(_run_validate_and_move, job_id, subdomain)

    return {
        "message": "Upload accepted",
        "job_id": job_id,
        "queued": len(rows),
    }


@router.post("/bio_att_clear")
async def bio_att_clear(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Wipe the temp table. Manual override for stuck batches."""
    co_id = request.query_params.get("co_id")
    if not co_id:
        raise HTTPException(status_code=400, detail="co_id is required")

    try:
        existing = db.execute(TEMP_COUNT_SQL).fetchone()
        deleted = int(existing.cnt) if existing else 0
        db.execute(TEMP_DELETE_SQL)
        db.commit()
        return {"message": "Temp table cleared", "deleted": deleted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bio_att_excel_status/{job_id}")
async def bio_att_excel_status(
    job_id: str,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    job = _get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


@router.get("/bio_att_temp_count")
async def bio_att_temp_count(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Return current row count of temp_bio_attendance_table."""
    co_id = request.query_params.get("co_id")
    if not co_id:
        raise HTTPException(status_code=400, detail="co_id is required")
    try:
        row = db.execute(TEMP_COUNT_SQL).fetchone()
        return {"count": int(row.cnt) if row else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Bio-attendance -> daily_attendance_process_table  (Process button)
# =============================================================================
#
# Algorithm (per emp x date):
#   * Validate emp_code against hrms_ed_official_details (active=1) -> eb_id.
#       Unmatched emp_codes for the date are returned as an XLSX download
#       and the entire process is aborted.
#   * Spell A:  IN-time window 05:30..09:59:59,  work window 06:00..14:00
#   * Spell B:  IN-time window 13:30..15:59:59,  work window 14:00..22:00
#       (No Spell C / night shift.)
#   * Working day vs weekly off:
#       - tbl_off_day_mst.day_off stores int 0..6 (Sun..Sat).
#       - If the attendance_date weekday matches a day_off row -> off day.
#       - Off day spell row: attendance_type = 'O'
#       - Working day spell row: attendance_type = 'P'
#   * Overtime split:
#       - Only on working days.
#       - If raw duration > 8.5h, additionally insert one row with
#         spell_name = same A/B, attendance_type = 'O',
#         Working_hours = duration - 8.0,  Ot_hours = duration - 8.0.
#   * Re-run on same date = DELETE existing rows for that date, re-insert.

SPELL_A_IN_FROM = "05:30:00"
SPELL_A_IN_TO   = "10:00:00"  # exclusive
SPELL_A_START   = "06:00:00"
SPELL_A_END     = "14:00:00"

SPELL_B_IN_FROM = "13:30:00"
SPELL_B_IN_TO   = "16:00:00"  # exclusive
SPELL_B_START   = "14:00:00"
SPELL_B_END     = "22:00:00"

SPELL_HOURS = 8.0
OT_THRESHOLD_HOURS = 8.5


def _log_sql(label: str, stmt, params: dict | None = None) -> None:
    """Print a SQL statement + bind params to stdout (uvicorn console).
    Used for live debugging the Process endpoint."""
    try:
        sql_str = str(getattr(stmt, "text", stmt))
    except Exception:
        sql_str = repr(stmt)
    print(f"\n[bio_att_process] === {label} ===", flush=True)
    print(sql_str.strip(), flush=True)
    if params is not None:
        print(f"[bio_att_process] params = {params}", flush=True)


# 1. Find rows on :tran_date that are NOT fully linked
#    (any of eb_id / dept_id / desig_id / device_id is NULL).
#    These are reported as the "unmatched" xlsx and skipped during processing.
UNMATCHED_EMP_CODES_SQL = text(
    """
    SELECT b.emp_code, b.emp_anme, b.bio_id, b.log_date,
           b.company_name, b.department, b.designation,
           b.employement_type, b.device_direction, b.device_name
    FROM bio_attendance_table b
    WHERE DATE(b.log_date) = :tran_date
      AND (b.eb_id IS NULL
        OR b.dept_id IS NULL
        OR b.desig_id IS NULL
        OR b.device_id IS NULL)
    ORDER BY b.emp_code, b.log_date
    """
)

# 2. Did weekday match a day_off row? (Returns count > 0 if it's a weekly-off day.)
#    DAYOFWEEK(d) -> 1=Sun..7=Sat  =>  -1 normalises to 0..6 like the spec.
IS_OFF_DAY_SQL = text(
    "SELECT COUNT(*) AS cnt FROM tbl_off_day_mst WHERE day_off = (DAYOFWEEK(:tran_date) - 1)"
)

# 3. Wipe re-run rows for the date.
DELETE_DAY_ROWS_SQL = text(
    "DELETE FROM daily_attendance_process_table WHERE attendance_date = :tran_date"
)

# 4. Fetch all punches for the spell window. We then pair them in Python
#    (1st=IN, 2nd=OUT, 3rd=IN, 4th=OUT, ...) and only count pairs whose
#    duration is at least 1 hour as Working_hours. check_in is the first
#    punch, check_out is the last punch.
#
#    Only rows where ALL four link ids (eb_id, dept_id, desig_id, device_id)
#    are populated are considered. Window: punches between :in_from and
#    :spell_end (inclusive of in_from, inclusive of spell_end+OT slack).
FETCH_SPELL_PUNCHES_SQL = text(
    """
    SELECT b.eb_id,
           b.bio_att_id,
           b.dept_id,
           b.desig_id,
           TIME(b.log_date)   AS punch_time,
           b.log_date         AS log_date
    FROM bio_attendance_table b
    WHERE DATE(b.log_date) = :tran_date
      AND b.eb_id     IS NOT NULL
      AND b.dept_id   IS NOT NULL
      AND b.desig_id  IS NOT NULL
      AND b.device_id IS NOT NULL
      AND TIME(b.log_date) >= :in_from
      AND TIME(b.log_date) <= :window_end
    ORDER BY b.eb_id, b.log_date
    """
)

# Insert one daily row per employee using bound params.
INSERT_SPELL_ROW_SQL = text(
    """
    INSERT INTO daily_attendance_process_table
        (eb_id, bio_id, dept_id, desig_id,
         attendance_date, spell_name, attendance_type,
         attendance_source, check_in, check_out,
         Time_duration, Working_hours, Ot_hours,
         spell_start_time, spell_end_time, spell_hours, processed)
    VALUES
        (:eb_id, :bio_id, :dept_id, :desig_id,
         :tran_date, :spell_name, :attendance_type,
         'BIO', :check_in, :check_out,
         :time_duration, :working_hours, :ot_hours,
         :spell_start, :spell_end, :spell_hours, 1)
    """
)

# Minimum pair duration that counts toward Working_hours.
MIN_PAIR_SECONDS = 3600  # 1 hour


def _parse_hms(s: str) -> dt_time:
    """Parse 'HH:MM:SS' into datetime.time."""
    h, m, sec = (int(x) for x in s.split(":"))
    return dt_time(h, m, sec)


def _to_seconds(t) -> int:
    """Convert a datetime.time / timedelta-ish value to seconds-of-day."""
    if isinstance(t, timedelta):
        return int(t.total_seconds())
    if isinstance(t, dt_time):
        return t.hour * 3600 + t.minute * 60 + t.second
    # Fallback: parse string 'HH:MM:SS'
    return _to_seconds(_parse_hms(str(t)))


def _process_one_spell(
    db: Session,
    *,
    tran_date: str,
    spell_name: str,
    in_from: str,
    in_to: str,
    spell_start: str,
    spell_end: str,
    is_off_day: bool,
) -> tuple[int, int]:
    """Build daily_attendance_process_table rows for this spell.

    Logic:
      * Pull every punch (per emp) in [in_from .. spell_end+slack] for the date.
      * The employee belongs to this spell iff their first punch is within
        [in_from .. in_to).
      * Pair punches: (0,1), (2,3), ... -- 1st=IN, 2nd=OUT, etc.
      * Working_hours = sum of pair durations that are >= 1 hour.
      * check_in = first punch, check_out = last punch.
      * Time_duration = (check_out - check_in) in hours.
      * If Working_hours > OT_THRESHOLD_HOURS (and not an off day),
        insert a parallel 'O' row for the overflow.

    Returns (regular_inserted, ot_inserted).
    """
    in_from_sec = _to_seconds(_parse_hms(in_from))
    in_to_sec   = _to_seconds(_parse_hms(in_to))

    # Slack so that a late check-out after spell_end is still captured.
    OT_SLACK_HOURS = 6
    spell_end_t = _parse_hms(spell_end)
    window_end_dt = (datetime.combine(date.min, spell_end_t)
                     + timedelta(hours=OT_SLACK_HOURS))
    # cap at 23:59:59 (we don't cross midnight here)
    if window_end_dt.day != date.min.day:
        window_end = "23:59:59"
    else:
        window_end = window_end_dt.time().strftime("%H:%M:%S")

    fetch_params = {
        "tran_date": tran_date,
        "in_from": in_from,
        "window_end": window_end,
    }
    _log_sql(f"FETCH_SPELL_PUNCHES_SQL [spell={spell_name}]",
             FETCH_SPELL_PUNCHES_SQL, fetch_params)
    rows = db.execute(FETCH_SPELL_PUNCHES_SQL, fetch_params).fetchall()
    print(f"[bio_att_process]   -> fetched {len(rows)} punch row(s)", flush=True)

    # Group punches per employee, preserving SQL ORDER BY (eb_id, log_date).
    # Each tuple: (punch_time, bio_att_id, dept_id, desig_id).
    by_emp: dict[int, list[tuple]] = {}
    for r in rows:
        m = r._mapping
        by_emp.setdefault(m["eb_id"], []).append(
            (m["punch_time"], m["bio_att_id"], m["dept_id"], m["desig_id"])
        )

    inserted_reg = 0
    inserted_ot  = 0
    base_attendance_type = "O" if is_off_day else "P"

    for eb_id, punches in by_emp.items():
        if not punches:
            continue
        first_time, first_bio, first_dept, first_desig = punches[0]
        first_sec = _to_seconds(first_time)
        # Employee only belongs to this spell if first punch is inside IN window.
        if not (in_from_sec <= first_sec < in_to_sec):
            continue

        last_time, _, _, _ = punches[-1]
        last_sec = _to_seconds(last_time)

        # Pair the punches -- (0,1), (2,3), ...
        working_secs = 0
        for i in range(0, len(punches) - 1, 2):
            in_t,  _, _, _ = punches[i]
            out_t, _, _, _ = punches[i + 1]
            diff = _to_seconds(out_t) - _to_seconds(in_t)
            if diff >= MIN_PAIR_SECONDS:
                working_secs += diff

        if working_secs < MIN_PAIR_SECONDS:
            # Total qualified working time is less than 1 hour -- skip row.
            continue

        working_hours  = round(working_secs / 3600.0, 2)
        capped_working = round(min(SPELL_HOURS, working_hours), 2)
        # OT: only on working days, when working_hours exceeds threshold.
        if (not is_off_day) and working_hours > OT_THRESHOLD_HOURS:
            ot_hours = round(working_hours - SPELL_HOURS, 2)
        else:
            ot_hours = 0
        # Time_duration = total of working + OT (always == working_hours by definition).
        time_duration = round(capped_working + ot_hours, 2)

        reg_params = {
            "eb_id": int(eb_id),
            "bio_id": int(first_bio) if first_bio is not None else None,
            "dept_id": int(first_dept) if first_dept is not None else None,
            "desig_id": int(first_desig) if first_desig is not None else None,
            "tran_date": tran_date,
            "spell_name": spell_name,
            "attendance_type": base_attendance_type,
            "check_in": first_time if isinstance(first_time, dt_time)
                        else str(first_time),
            "check_out": last_time if isinstance(last_time, dt_time)
                         else str(last_time),
            "time_duration": time_duration,
            "working_hours": capped_working,
            "ot_hours": ot_hours,
            "spell_start": spell_start,
            "spell_end": spell_end,
            "spell_hours": SPELL_HOURS,
        }
        _log_sql(f"INSERT_SPELL_ROW_SQL [spell={spell_name} eb_id={eb_id}]",
                 INSERT_SPELL_ROW_SQL, reg_params)
        db.execute(INSERT_SPELL_ROW_SQL, reg_params)
        inserted_reg += 1

    inserted_ot = 0  # OT no longer creates a separate row.
    print(f"[bio_att_process]   -> rows inserted = {inserted_reg}", flush=True)
    return inserted_reg, inserted_ot


def _build_unmatched_xlsx(rows) -> bytes:
    """Build an xlsx workbook listing the raw bio rows for unmatched emp_codes."""
    try:
        import openpyxl
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"openpyxl not installed: {e}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Unmatched Emp Codes"
    headers = [
        "emp_code", "emp_anme", "bio_id", "log_date", "company_name",
        "department", "designation", "employement_type",
        "device_direction", "device_name",
    ]
    ws.append(headers)
    for r in rows:
        m = r._mapping
        ws.append([
            m.get("emp_code"),
            m.get("emp_anme"),
            m.get("bio_id"),
            str(m.get("log_date") or ""),
            m.get("company_name"),
            m.get("department"),
            m.get("designation"),
            m.get("employement_type"),
            m.get("device_direction"),
            m.get("device_name"),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


@router.post("/bio_att_process")
async def bio_att_process(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Process raw bio_attendance_table rows for a date into
    daily_attendance_process_table.

    Request body: ``{"tran_date": "YYYY-MM-DD"}``.

    Behaviour:
      * If any emp_code on that date is unknown to ``hrms_ed_official_details``,
        responds with an XLSX attachment listing those raw rows and aborts —
        no inserts are made.
      * Otherwise wipes existing rows for that date and re-inserts spell A,
        spell B, and OT rows. Returns JSON stats.
    """
    co_id = request.query_params.get("co_id")
    if not co_id:
        raise HTTPException(status_code=400, detail="co_id is required")

    try:
        body = await request.json()
    except Exception:
        body = {}
    tran_date = (body or {}).get("tran_date")
    if not tran_date:
        raise HTTPException(status_code=400, detail="tran_date is required")
    try:
        # Validate format.
        datetime.strptime(tran_date, "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="tran_date must be YYYY-MM-DD")

    try:
        # Step 1: collect emp_codes that punched on this date but aren't in the
        # employee master. We don't abort — they're just skipped (the INSERT
        # JOINs against hrms_ed_official_details, so unmatched rows fall out
        # naturally). The list is returned as an xlsx attachment.
        try:
            _log_sql("UNMATCHED_EMP_CODES_SQL", UNMATCHED_EMP_CODES_SQL, {"tran_date": tran_date})
            unmatched = db.execute(
                UNMATCHED_EMP_CODES_SQL, {"tran_date": tran_date}
            ).fetchall()
            print(f"[bio_att_process] unmatched rows: {len(unmatched)}", flush=True)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed reading bio_attendance_table / hrms_ed_official_details. "
                    f"Original error: {e}"
                ),
            )
        unique_codes = {r._mapping.get("emp_code") for r in unmatched}

        # Step 2: weekly-off check. Fail-soft — if tbl_off_day_mst doesn't
        # exist or has unexpected schema, treat the day as a working day.
        try:
            _log_sql("IS_OFF_DAY_SQL", IS_OFF_DAY_SQL, {"tran_date": tran_date})
            off_row = db.execute(IS_OFF_DAY_SQL, {"tran_date": tran_date}).fetchone()
            is_off_day = bool(off_row and int(off_row.cnt) > 0)
            print(f"[bio_att_process] is_off_day = {is_off_day}", flush=True)
        except Exception as e:
            print(f"[bio_att_process] IS_OFF_DAY_SQL failed (treating as working day): {e}", flush=True)
            try:
                db.rollback()
            except Exception:
                pass
            is_off_day = False

        # Step 3: wipe existing rows for this date (re-run safe).
        try:
            _log_sql("DELETE_DAY_ROWS_SQL", DELETE_DAY_ROWS_SQL, {"tran_date": tran_date})
            db.execute(DELETE_DAY_ROWS_SQL, {"tran_date": tran_date})
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=(
                    "daily_attendance_process_table not accessible. "
                    "Create the table (see DDL in repo notes). "
                    f"Original error: {e}"
                ),
            )

        # Step 4: process Spell A and Spell B for matched employees only.
        try:
            a_reg, a_ot = _process_one_spell(
                db, tran_date=tran_date, spell_name="A",
                in_from=SPELL_A_IN_FROM, in_to=SPELL_A_IN_TO,
                spell_start=SPELL_A_START, spell_end=SPELL_A_END,
                is_off_day=is_off_day,
            )
            b_reg, b_ot = _process_one_spell(
                db, tran_date=tran_date, spell_name="B",
                in_from=SPELL_B_IN_FROM, in_to=SPELL_B_IN_TO,
                spell_start=SPELL_B_START, spell_end=SPELL_B_END,
                is_off_day=is_off_day,
            )
            db.commit()
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Spell processing failed: {e}",
            )

        total = a_reg + a_ot + b_reg + b_ot
        message = (
            f"Processed {total} row(s) for {tran_date} "
            f"(A: {a_reg} regular + {a_ot} OT, "
            f"B: {b_reg} regular + {b_ot} OT, "
            f"day_off: {is_off_day}, "
            f"unmatched_emp_codes: {len(unique_codes)})."
        )

        # If any emp_codes were unmatched, stream the xlsx report alongside
        # success — stats travel in headers so the UI can still show them.
        if unmatched:
            xlsx_bytes = _build_unmatched_xlsx(unmatched)
            return Response(
                content=xlsx_bytes,
                status_code=200,
                media_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="unmatched_emp_codes_{tran_date}.xlsx"'
                    ),
                    "Access-Control-Expose-Headers": (
                        "Content-Disposition, X-Unmatched-Count, X-Unmatched-Rows, "
                        "X-Processed, X-Process-Message"
                    ),
                    "X-Unmatched-Count": str(len(unique_codes)),
                    "X-Unmatched-Rows": str(len(unmatched)),
                    "X-Processed": str(total),
                    "X-Process-Message": message,
                },
            )

        return {
            "message": message,
            "processed": total,
            "tran_date": tran_date,
            "is_off_day": is_off_day,
            "spell_a_regular": a_reg,
            "spell_a_ot": a_ot,
            "spell_b_regular": b_reg,
            "spell_b_ot": b_ot,
            "unmatched_emp_codes": 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        # Log the full traceback so we can see it in uvicorn console.
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Final Process: copy daily_attendance_process_table -> daily_attendance.
# ---------------------------------------------------------------------------
# Spell rule (per user spec):
#   * Default: spell A if 06:00 <= ref_time < 14:00, spell B if 14:00 <= ref_time < 22:00.
#   * ref_time = check_out when ot_hours > 0, else check_in.
# Only rows with processed = 1 are copied; copied rows are marked processed = 2.

FINAL_FETCH_SQL = text(
    """
    SELECT daily_att_proc_id, eb_id, bio_id, dept_id, desig_id,
           attendance_date, spell_name, attendance_type, attendance_source,
           check_in, check_out, Time_duration, Working_hours, Ot_hours,
           spell_start_time, spell_end_time, spell_hours, device_name
      FROM daily_attendance_process_table
     WHERE attendance_date = :tran_date
       AND processed = 1
    """
)

FINAL_INSERT_SQL = text(
    """
    INSERT INTO daily_attendance
      (attendance_date, attendance_source, attendance_type, attendance_mark,
       eb_id, bio_id, branch_id, status_id,
       worked_department_id, worked_designation_id,
       entry_time, exit_time,
       working_hours, idle_hours, spell, spell_hours,
       is_active, update_date_time)
    VALUES
      (:attendance_date, :attendance_source, :attendance_type, 3,
       :eb_id, :bio_id, :branch_id, 1,
       :worked_department_id, :worked_designation_id,
       :entry_time, :exit_time,
       :working_hours, 0, :spell, :spell_hours,
       1, NOW())
    """
)

FINAL_MARK_PROCESSED_SQL = text(
    """
    UPDATE daily_attendance_process_table
       SET processed = 2
     WHERE attendance_date = :tran_date
       AND processed = 1
    """
)


def _resolve_spell_by_time(check_in, check_out, ot_hours) -> str | None:
    """Return 'A' / 'B' based on time-of-day rule.

    ref = check_out when ot_hours > 0 else check_in.
    A: 06:00 <= ref < 14:00 ; otherwise B.
    """
    try:
        ot_val = float(ot_hours or 0)
    except Exception:
        ot_val = 0.0
    ref = check_out if ot_val > 0 else check_in
    if ref is None:
        return None
    # Normalise to time-of-day seconds.
    if isinstance(ref, datetime):
        secs = ref.hour * 3600 + ref.minute * 60 + ref.second
    elif isinstance(ref, dt_time):
        secs = ref.hour * 3600 + ref.minute * 60 + ref.second
    elif isinstance(ref, timedelta):
        total = int(ref.total_seconds()) % 86400
        secs = total
    else:
        # Last-ditch: try to parse "HH:MM[:SS]".
        try:
            parts = str(ref).split(":")
            secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + (int(parts[2]) if len(parts) > 2 else 0)
        except Exception:
            return None
    if 6 * 3600 <= secs < 14 * 3600:
        return "A"
    return "B"


@router.post("/bio_att_final_process")
async def bio_att_final_process(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Move processed=1 rows from daily_attendance_process_table into
    daily_attendance for a given date, recomputing spell by time-of-day.
    """
    co_id = request.query_params.get("co_id")
    if not co_id:
        raise HTTPException(status_code=400, detail="co_id is required")

    try:
        body = await request.json()
    except Exception:
        body = {}
    tran_date = (body or {}).get("tran_date")
    if not tran_date:
        raise HTTPException(status_code=400, detail="tran_date is required")
    try:
        datetime.strptime(tran_date, "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="tran_date must be YYYY-MM-DD")

    branch_id_raw = (body or {}).get("branch_id")
    if branch_id_raw in (None, ""):
        raise HTTPException(status_code=400, detail="branch_id is required")
    try:
        branch_id = int(branch_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="branch_id must be an integer")

    try:
        _log_sql("FINAL_FETCH_SQL", FINAL_FETCH_SQL, {"tran_date": tran_date})
        rows = db.execute(FINAL_FETCH_SQL, {"tran_date": tran_date}).fetchall()
        print(f"[bio_att_final_process] fetched {len(rows)} row(s)", flush=True)

        inserted = 0
        skipped = 0
        for r in rows:
            m = r._mapping
            spell = _resolve_spell_by_time(
                m.get("check_in"), m.get("check_out"), m.get("Ot_hours")
            )
            if spell is None:
                skipped += 1
                print(
                    f"[bio_att_final_process] skip eb_id={m.get('eb_id')} "
                    f"check_in={m.get('check_in')} check_out={m.get('check_out')} "
                    f"ot={m.get('Ot_hours')} {spell} (out of A/B window)",
                    flush=True,
                )
                continue

            base_params = {
                "attendance_date": m.get("attendance_date"),
                "attendance_source": m.get("attendance_source") or "BIO",
                "eb_id": m.get("eb_id"),
                "bio_id": m.get("bio_id"),
                "branch_id": branch_id,
                "worked_department_id": m.get("dept_id"),
                "worked_designation_id": m.get("desig_id"),
                "entry_time": m.get("check_in"),
                "exit_time": m.get("check_out"),
                "spell": spell,
                "spell_hours": m.get("spell_hours"),
            }

            try:
                wh = float(m.get("Working_hours") or 0)
            except Exception:
                wh = 0.0
            try:
                ot = float(m.get("Ot_hours") or 0)
            except Exception:
                ot = 0.0

            inserts: list[tuple[str, float]] = []
            if wh > 0 and ot > 0:
                inserts.append(("P", wh))
                inserts.append(("O", ot))
            elif wh > 0:
                inserts.append(("P", wh))
            elif ot > 0:
                inserts.append(("O", ot))
            else:
                skipped += 1
                print(
                    f"[bio_att_final_process] skip eb_id={m.get('eb_id')} "
                    f"working_hours=0 ot_hours=0",
                    flush=True,
                )
                continue

            for att_type, hours in inserts:
                params = {
                    **base_params,
                    "attendance_type": att_type,
                    "working_hours": hours,
                }
                _log_sql(
                    f"FINAL_INSERT_SQL [eb_id={m.get('eb_id')} spell={spell} type={att_type}]",
                    FINAL_INSERT_SQL, params,
                )
                db.execute(FINAL_INSERT_SQL, params)
                inserted += 1

        _log_sql("FINAL_MARK_PROCESSED_SQL", FINAL_MARK_PROCESSED_SQL, {"tran_date": tran_date})
        db.execute(FINAL_MARK_PROCESSED_SQL, {"tran_date": tran_date})
        db.commit()

        return {
            "message": (
                f"Final processed {inserted} row(s) for {tran_date} "
                f"(skipped {skipped} out-of-window)."
            ),
            "tran_date": tran_date,
            "inserted": inserted,
            "skipped": skipped,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
