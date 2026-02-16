# VoWERP3 Backend - Developer Guide for Claude

## Project Overview

VoWERP3 Backend is a **multi-tenant ERP system** built with **FastAPI** and **SQLAlchemy**. This backend serves a Next.js frontend (vowerp3ui) and handles complex business operations including procurement, inventory, sales, and jute/yarn management.

**Tech Stack:**
- Python 3.12+
- FastAPI 0.115.11
- SQLAlchemy 2.0.38 / SQLModel
- MySQL with PyMySQL
- JWT authentication with refresh tokens
- Docker containerization
- Pytest for testing

**Current Branch:** `ssbe1.2` | **Main Branch:** `main`

---

## Critical Architecture Principles

### 1. Multi-Tenancy (MOST IMPORTANT)

**Single Source of Truth:** `src/config/db.py`

Every request must be isolated to its tenant's database. The system automatically routes requests based on headers:

**Tenant Resolution Priority:**
1. `x-forwarded-host` header (from proxy)
2. `host` header
3. `referer` header
4. Explicit `subdomain` header
5. Default fallback

**Database Naming Convention:**
- Main DB: `{subdomain}` (e.g., `demo`, `client1`)
- Secondary DBs: `{subdomain}_c`, `{subdomain}_c_1`, `{subdomain}_c_2`, `{subdomain}_c_3`

**ALWAYS use the dependency:**
```python
@router.get("/endpoint")
async def endpoint(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh)
):
    co_id = request.query_params.get("co_id")
    # db is automatically bound to correct tenant
```

**❌ NEVER:**
- Hardcode database names
- Skip `get_tenant_db` dependency
- Share database connections between tenants

### 2. Database Access Patterns

**Two Approaches (Use Both as Appropriate):**

#### A. ORM Models (Preferred for Simple CRUD)
**Location:** `src/models/`
- **Authoritative source** for database schema
- Use for straightforward operations
- Models organized by domain: `item.py`, `procurement.py`, `jute.py`, `inventory.py`, `sales.py`, `mst.py`

```python
from src.models.procurement import ProcInward, ProcInwardDtl

inward = db.query(ProcInward).filter(ProcInward.co_id == co_id).first()
```

#### B. Raw SQL (For Complex Queries)
**Location:** `src/{module}/query.py`
- Use `sqlalchemy.text()` with named bind parameters
- Required for complex joins, aggregations, conditional logic

```python
# In query.py
def get_item_table(co_id: int = None):
    sql = """
    SELECT * FROM item_mst
    WHERE co_id = :co_id
    AND (:search IS NULL OR item_code LIKE :search)
    """
    return text(sql)

# In router
query = get_item_table(int(co_id))
result = db.execute(query, {"co_id": int(co_id), "search": search}).fetchall()
data = [dict(r._mapping) for r in result]
```

**CRITICAL SQL Binding Rules:**
- ✅ Use `None` for SQL NULL: `{"item_id": None}`
- ❌ Never use string "null": `{"item_id": "null"}`
- ✅ Match parameter names exactly: `:co_id` → `{"co_id": value}`
- ✅ Always type-cast: `{"co_id": int(co_id)}`

### 3. API Response Format (MANDATORY)

**Standard Response Wrapper:**
```python
from src.common.utils import create_response

# Simple response
return {"data": results}

# With master data
return {"data": records, "master": options}

# Using helper
return create_response(data=results, master=options)
```

**❌ NEVER return raw lists:**
```python
return [{"id": 1}]  # WRONG
```

**✅ ALWAYS wrap in object:**
```python
return {"data": [{"id": 1}]}  # CORRECT
```

### 4. Authentication & Authorization

**Standard Dependency:**
```python
token_data: dict = Depends(get_current_user_with_refresh)
```

**What it does:**
- Validates JWT access token
- Auto-refreshes using refresh token from default DB
- Returns user dict with `user_id` field
- Raises `HTTPException(401)` if invalid

**Dev Mode Bypass:**
```python
ENV=development  # Auto-bypass in .env
BYPASS_AUTH=1    # Explicit bypass flag
```

**Cookie Storage:**
- Cookie name: `access_token`
- Production domain: `.vowerp.co.in`

### 5. Error Handling Standards

**Always follow this pattern:**
```python
try:
    # 1. Validate required parameters FIRST
    co_id = request.query_params.get("co_id")
    if not co_id:
        raise HTTPException(status_code=400, detail="co_id is required")

    # 2. Type conversion with error handling
    try:
        branch_id = int(request.query_params.get("branch_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid branch_id format")

    # 3. Execute business logic
    result = db.execute(query, {"co_id": int(co_id)}).fetchall()

    # 4. Return standardized response
    return {"data": [dict(r._mapping) for r in result]}

except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    # Log the error (add logging if not present)
    raise HTTPException(status_code=500, detail=str(e))
```

**HTTP Status Code Standards:**
- `400` - Missing/invalid required parameters
- `401` - Authentication failures (handled by auth dependency)
- `403` - Authorization failures (permission denied)
- `404` - Resource not found
- `500` - Server errors, unexpected exceptions

---

## Module Structure Pattern

**Every feature module follows this convention:**

```
src/{module}/
├── {feature}.py      # FastAPI router with endpoints (APIRouter)
├── query.py          # SQL query functions returning text() objects
├── models.py         # SQLAlchemy ORM models (optional, may be in src/models/)
├── schemas.py        # Pydantic request/response schemas (optional)
└── constants.py      # Enums, status IDs, constants (optional)
```

**Example: Procurement Module**
```
src/procurement/
├── indent.py         # Procurement indent endpoints
├── po.py             # Purchase order endpoints
├── inward.py         # Goods receipt endpoints
├── query.py          # Shared SQL queries
└── constants.py      # INDENT_STATUS_IDS, PO_TYPES, etc.
```

**Router Registration (in `src/main.py`):**
```python
from src.procurement.indent import router as indent_router

app.include_router(
    indent_router,
    prefix="/api/procurementIndent",
    tags=["procurement-indent"]
)
```

---

## Naming Conventions

### Variables & Functions
**Use snake_case:**
- `co_id` (company ID)
- `item_grp_id` (item group ID)
- `get_item_table()`
- `check_duplicate_item()`

### Classes & Models
**Use PascalCase:**
- `ItemGrpMst` (Item Group Master)
- `ProcInward` (Procurement Inward)
- `YarnQualityMst` (Yarn Quality Master)

**Model Suffixes:**
- `*Mst` - Master tables (reference data)
- `*Dtl` - Detail/line item tables
- `*Response` - Pydantic response schemas
- `*Request` - Pydantic request schemas

### SQL Bind Parameters
**Standard parameter names:**
- `:co_id` - Company ID (most common)
- `:item_id` - Item ID
- `:item_grp_id` - Item Group ID
- `:branch_id` - Branch ID
- `:search` - Search term for LIKE queries
- `:user_id` - User ID

**Keep consistent across all queries!**

---

## Testing Requirements (MANDATORY)

### When to Write Tests
**ALWAYS write tests for:**
1. ✅ New API endpoints - request/response validation, auth, error cases
2. ✅ Query functions - parameter binding, SQL correctness, edge cases
3. ✅ Business logic functions - input/output validation, error handling
4. ✅ Bug fixes - add regression test before fixing

### Test Structure
**Location:** `src/test/`
**Naming:** `test_{module}_{feature}.py`

**Example: Testing an Endpoint**
```python
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app

client = TestClient(app)

class TestYarnQualityEndpoints:
    @patch("src.masters.yarnQuality.get_tenant_db")
    @patch("src.masters.yarnQuality.get_current_user_with_refresh")
    def test_yarn_quality_create_setup_success(self, mock_auth, mock_db):
        # Setup mocks
        mock_session = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"jute_yarn_type_id": 1, "jute_yarn_type_name": "Polyester"}
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_db.return_value.__enter__.return_value = mock_session
        mock_auth.return_value = {"user_id": 1}

        # Execute request
        response = client.get("/api/yarnQualityMaster/yarn_quality_create_setup?co_id=1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "yarn_types" in data
        assert len(data["yarn_types"]) > 0

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_missing_co_id(self, mock_db):
        response = client.get("/api/yarnQualityMaster/yarn_quality_create_setup")
        assert response.status_code == 400
        assert "co_id" in response.json()["detail"].lower()
```

### Running Tests
```bash
# Activate virtual environment
source C:/code/vowerp3be/.venv/Scripts/activate

# Run all tests
pytest src/test/ -v

# Run specific file
pytest src/test/test_yarn_quality.py -v

# Run with pattern match
pytest src/test/ -k "test_po" -v

# Run with coverage
pytest src/test/ --cov=src --cov-report=html
```

---

## Common Pitfalls & How to Avoid Them

### 1. SQL NULL Handling
❌ **Wrong:**
```python
db.execute(query, {"item_id": "null", "search": "null"})
```

✅ **Correct:**
```python
db.execute(query, {"item_id": None, "search": None})
```

### 2. Schema Source Truth
❌ **Wrong:** Using `dbqueries/*.sql` files as reference (may be outdated)
✅ **Correct:** Use `src/models/*.py` ORM models as authoritative schema

### 3. Response Format
❌ **Wrong:**
```python
return items  # Returns list directly
```

✅ **Correct:**
```python
return {"data": items}
```

### 4. Multi-Tenant Isolation
❌ **Wrong:**
```python
db = SessionLocal()  # Direct session creation
```

✅ **Correct:**
```python
db: Session = Depends(get_tenant_db)  # Use dependency
```

### 5. Parameter Binding Mismatch
❌ **Wrong:**
```python
sql = "WHERE co_id = :company_id"
db.execute(text(sql), {"co_id": 1})  # Name mismatch!
```

✅ **Correct:**
```python
sql = "WHERE co_id = :co_id"
db.execute(text(sql), {"co_id": 1})  # Names match
```

---

## Key Documentation Files

**Read these files for deep understanding:**

| File | Purpose | Priority |
|------|---------|----------|
| `.github/copilot-instructions.md` | AI agent guide with patterns | ⭐⭐⭐ ESSENTIAL |
| `.github/WORKSPACE-INSTRUCTIONS.md` | Repo structure, legacy vs current | ⭐⭐⭐ ESSENTIAL |
| `DOCUMENTATION_INDEX.md` | Navigation guide to all docs | ⭐⭐ Important |
| `src/config/db.py` | Multi-tenant database config | ⭐⭐⭐ ESSENTIAL |
| `src/authorization/utils.py` | JWT, password hashing | ⭐⭐ Important |
| `src/common/utils.py` | Shared utilities | ⭐ Reference |
| `README.md` | Setup, Docker commands | ⭐ Reference |

---

## Quick Reference: Adding a New Endpoint

**Step-by-step guide:**

### 1. Create Query Function (if needed)
**File:** `src/{module}/query.py`
```python
def get_my_data(co_id: int):
    sql = """
    SELECT * FROM my_table
    WHERE co_id = :co_id
    AND (:search IS NULL OR name LIKE :search)
    """
    return text(sql)
```

### 2. Create Endpoint
**File:** `src/{module}/{feature}.py`
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from .query import get_my_data

router = APIRouter()

@router.get("/my_endpoint")
async def my_endpoint(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh)
):
    try:
        # 1. Validate required parameters
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="co_id is required")

        search = request.query_params.get("search")

        # 2. Execute query
        query = get_my_data(int(co_id))
        result = db.execute(
            query,
            {"co_id": int(co_id), "search": search if search else None}
        ).fetchall()

        # 3. Format response
        data = [dict(r._mapping) for r in result]

        # 4. Return standardized format
        return {"data": data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. Register Router
**File:** `src/main.py`
```python
from src.{module}.{feature} import router as my_router

app.include_router(my_router, prefix="/api/myModule", tags=["my-feature"])
```

### 4. Write Tests
**File:** `src/test/test_{module}_{feature}.py`
```python
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app

client = TestClient(app)

class TestMyEndpoint:
    @patch("src.{module}.{feature}.get_tenant_db")
    @patch("src.{module}.{feature}.get_current_user_with_refresh")
    def test_my_endpoint_success(self, mock_auth, mock_db):
        # Setup mocks
        mock_session = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"id": 1, "name": "Test"}
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_db.return_value.__enter__.return_value = mock_session
        mock_auth.return_value = {"user_id": 1}

        # Test
        response = client.get("/api/myModule/my_endpoint?co_id=1")
        assert response.status_code == 200
        assert "data" in response.json()
```

### 5. Run and Verify
```bash
# Run tests
pytest src/test/test_{module}_{feature}.py -v

# Start dev server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Test manually
curl "http://localhost:8000/api/myModule/my_endpoint?co_id=1"
```

---

## Environment Configuration

**Files:**
- `env/database.env` - Database credentials
- `.env` or `env/keys.env` - Secret keys

**Required Variables:**
```bash
# Database
DATABASE_USER=root
DATABASE_PASSWORD=yourpassword
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_DEFAULT=default_db_name

# Environment
ENV=development  # or production
BYPASS_AUTH=1    # Optional: skip auth in dev

# JWT
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Development Workflow

### Setup
```bash
# Clone repo
cd c:\code\vowerp3be

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running
```bash
# Development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-compose up --build
```

### Before Committing
```bash
# 1. Run tests
pytest src/test/ -v

# 2. Check code quality
# (Add linting if available: black, flake8, mypy)

# 3. Verify no debug code
# Remove print statements, console.logs, breakpoints
```

---

## Best Practices Summary

### DO ✅
- Use `get_tenant_db` dependency for all database access
- Validate all required parameters before processing
- Return responses in `{"data": [...]}` format
- Use `None` for SQL NULL values
- Write tests for all new endpoints and logic
- Use ORM models as schema reference
- Follow snake_case for functions/variables
- Follow PascalCase for classes/models
- Type-cast parameters before passing to queries
- Handle exceptions with appropriate HTTP status codes

### DON'T ❌
- Hardcode database names
- Skip parameter validation
- Return raw lists from endpoints
- Use string "null" in SQL parameters
- Skip writing tests
- Use outdated `dbqueries/*.sql` as schema reference
- Mix naming conventions
- Trust user input without validation
- Catch exceptions without re-raising or proper handling
- Commit code without running tests

---

## Support & Resources

**For Questions:**
1. Check `.github/copilot-instructions.md` first
2. Review `DOCUMENTATION_INDEX.md` for specific topics
3. Look at existing similar endpoints as examples
4. Check test files for usage patterns

**Common Examples:**
- **Simple CRUD:** `src/masters/items.py`
- **Complex Transactions:** `src/procurement/indent.py`
- **Multi-table Queries:** `src/procurement/query.py`
- **Authentication Patterns:** `src/authorization/routers.py`
- **Testing Patterns:** `src/test/test_yarn_quality.py`

---

## Version Info
- Python: 3.12+
- FastAPI: 0.115.11
- SQLAlchemy: 2.0.38
- Current Branch: `ssbe1.2`
- Main Branch: `main`

**Last Updated:** 2026-02-13
