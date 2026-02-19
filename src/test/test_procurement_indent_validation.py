"""Tests for indent line-item validation logic.

Covers:
- determine_validation_logic mapping
- get_fy_boundaries calculation
- calculate_max_indent_qty formula
- /validate_item_for_indent endpoint (mocked DB)
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app

# Import helpers directly
from src.procurement.indent import (
    determine_validation_logic,
    get_fy_boundaries,
    calculate_max_indent_qty,
)


client = TestClient(app)


# ── Unit tests for helper functions ──────────────────────────────────

class TestDetermineValidationLogic:
    """Tests for the VALIDATION_LOGIC_MAP lookup."""

    def test_regular_general_returns_1(self):
        assert determine_validation_logic("Regular", "General") == 1

    def test_regular_maintenance_returns_1(self):
        assert determine_validation_logic("Regular", "Maintenance") == 1

    def test_regular_production_returns_1(self):
        assert determine_validation_logic("Regular", "Production") == 1

    def test_regular_overhaul_returns_1(self):
        assert determine_validation_logic("Regular", "Overhaul") == 1

    def test_regular_capital_returns_3(self):
        assert determine_validation_logic("Regular", "Capital") == 3

    def test_open_general_returns_2(self):
        assert determine_validation_logic("Open", "General") == 2

    def test_open_maintenance_returns_2(self):
        assert determine_validation_logic("Open", "Maintenance") == 2

    def test_open_production_returns_2(self):
        assert determine_validation_logic("Open", "Production") == 2

    def test_bom_general_returns_1(self):
        assert determine_validation_logic("BOM", "General") == 1

    def test_bom_capital_returns_3(self):
        assert determine_validation_logic("BOM", "Capital") == 3

    def test_bom_overhaul_returns_3(self):
        assert determine_validation_logic("BOM", "Overhaul") == 3

    def test_unknown_combination_returns_3(self):
        assert determine_validation_logic("Unknown", "Whatever") == 3

    def test_none_expense_returns_3(self):
        assert determine_validation_logic("Regular", None) == 3


class TestGetFyBoundaries:
    """Tests for financial-year boundary calculation (April 1 – March 31)."""

    def test_date_in_jan_returns_previous_april(self):
        start, end = get_fy_boundaries(date(2026, 1, 15))
        assert start == date(2025, 4, 1)
        assert end == date(2026, 3, 31)

    def test_date_in_april_returns_same_year(self):
        start, end = get_fy_boundaries(date(2026, 4, 1))
        assert start == date(2026, 4, 1)
        assert end == date(2027, 3, 31)

    def test_date_in_march_returns_previous_april(self):
        start, end = get_fy_boundaries(date(2026, 3, 31))
        assert start == date(2025, 4, 1)
        assert end == date(2026, 3, 31)

    def test_date_in_december(self):
        start, end = get_fy_boundaries(date(2025, 12, 25))
        assert start == date(2025, 4, 1)
        assert end == date(2026, 3, 31)


class TestCalculateMaxIndentQty:
    """Tests for the max indent quantity formula.

    Formula: max_indent_qty = max(maxqty - branch_stock - outstanding, min_order_qty, 0)
    """

    def test_basic_calculation(self):
        # maxqty=100, stock=30, outstanding=20 => raw=50
        # min_order_qty=10 => max(50, 10, 0) = 50
        result = calculate_max_indent_qty(100, 30, 20, 10)
        assert result == 50.0

    def test_stock_exceeds_max_returns_min_order(self):
        # maxqty=100, stock=90, outstanding=20 => raw=-10
        # min_order_qty=5 => max(-10, 5, 0) = 5
        result = calculate_max_indent_qty(100, 90, 20, 5)
        assert result == 5.0

    def test_all_zero(self):
        result = calculate_max_indent_qty(0, 0, 0, 0)
        assert result == 0.0

    def test_no_maxqty_returns_none(self):
        result = calculate_max_indent_qty(None, 50, 10, 5)
        assert result is None

    def test_no_min_order_qty_uses_zero(self):
        # maxqty=100, stock=60, outstanding=10 => raw=30
        # min_order_qty=None => max(30, 0, 0) = 30
        result = calculate_max_indent_qty(100, 60, 10, None)
        assert result == 30.0

    def test_large_outstanding_returns_zero_floor(self):
        # maxqty=50, stock=30, outstanding=25 => raw=-5
        # min_order_qty=None => max(-5, 0, 0) = 0
        result = calculate_max_indent_qty(50, 30, 25, None)
        assert result == 0.0

    def test_min_order_wins_over_raw(self):
        # maxqty=100, stock=95, outstanding=0 => raw=5
        # min_order_qty=20 => max(5, 20, 0) = 20
        result = calculate_max_indent_qty(100, 95, 0, 20)
        assert result == 20.0


# ── Endpoint tests ───────────────────────────────────────────────────

class TestValidateItemEndpoint:
    """Tests for GET /api/procurementIndent/validate_item_for_indent."""

    @patch("src.procurement.indent.get_current_user_with_refresh")
    @patch("src.procurement.indent.get_tenant_db")
    def test_missing_branch_id_returns_400(self, mock_db, mock_auth):
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        response = client.get(
            "/api/procurementIndent/validate_item_for_indent"
            "?item_id=1&indent_type=Regular&expense_type_id=1"
        )
        assert response.status_code == 400
        assert "branch_id" in response.json()["detail"].lower()

    @patch("src.procurement.indent.get_current_user_with_refresh")
    @patch("src.procurement.indent.get_tenant_db")
    def test_missing_item_id_returns_400(self, mock_db, mock_auth):
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        response = client.get(
            "/api/procurementIndent/validate_item_for_indent"
            "?branch_id=1&indent_type=Regular&expense_type_id=1"
        )
        assert response.status_code == 400
        assert "item_id" in response.json()["detail"].lower()

    @patch("src.procurement.indent.get_current_user_with_refresh")
    @patch("src.procurement.indent.get_tenant_db")
    def test_logic_3_returns_no_validation(self, mock_db, mock_auth):
        """Logic 3 (Regular+Capital) should return immediately with no warnings."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()

        # Mock expense type name lookup returning "Capital"
        expense_row = MagicMock()
        expense_row._mapping = {"expense_type_name": "Capital"}
        mock_session.execute.return_value.fetchone.return_value = expense_row

        mock_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        response = client.get(
            "/api/procurementIndent/validate_item_for_indent"
            "?branch_id=1&item_id=10&indent_type=Regular&expense_type_id=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validation_logic"] == 3
        assert data["warnings"] == []

    @patch("src.procurement.indent.get_current_user_with_refresh")
    @patch("src.procurement.indent.get_tenant_db")
    def test_logic1_no_minmax_returns_error(self, mock_db, mock_auth):
        """Logic 1 (Regular+General) should block entry when item has no min/max configured."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()

        # First call: expense type name lookup
        expense_row = MagicMock()
        expense_row._mapping = {"expense_type_name": "General"}

        # Second call: validation data with no min/max
        vdata_row = MagicMock()
        vdata_row._mapping = {
            "branch_stock": 0,
            "outstanding_indent_qty": 0,
            "minqty": None,
            "maxqty": None,
            "min_order_qty": None,
            "has_open_indent": 0,
        }

        mock_session.execute.return_value.fetchone.side_effect = [expense_row, vdata_row]
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        response = client.get(
            "/api/procurementIndent/validate_item_for_indent"
            "?branch_id=1&item_id=10&indent_type=Regular&expense_type_id=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validation_logic"] == 1
        assert data["has_minmax"] is False
        assert len(data["errors"]) > 0
        assert "min/max" in data["errors"][0].lower() or "Min/Max" in data["errors"][0]

    @patch("src.procurement.indent.get_current_user_with_refresh")
    @patch("src.procurement.indent.get_tenant_db")
    def test_logic1_with_minmax_allows_entry(self, mock_db, mock_auth):
        """Logic 1 (Regular+General) should allow entry when item has min/max configured."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()

        expense_row = MagicMock()
        expense_row._mapping = {"expense_type_name": "General"}

        vdata_row = MagicMock()
        vdata_row._mapping = {
            "branch_stock": 10,
            "outstanding_indent_qty": 5,
            "minqty": 20,
            "maxqty": 100,
            "min_order_qty": 10,
            "has_open_indent": 0,
        }

        mock_session.execute.return_value.fetchone.side_effect = [expense_row, vdata_row]
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        response = client.get(
            "/api/procurementIndent/validate_item_for_indent"
            "?branch_id=1&item_id=10&indent_type=Regular&expense_type_id=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["validation_logic"] == 1
        assert data["has_minmax"] is True
        assert data["errors"] == []
        assert data["max_indent_qty"] is not None
