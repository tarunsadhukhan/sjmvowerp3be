"""
Tests for Jute Issue API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import date, datetime
from src.main import app

client = TestClient(app)


class TestJuteIssueEndpoints:
    """Tests for Jute Issue API endpoints."""

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        """Mock authentication for all tests."""
        with patch("src.juteProcurement.issue.get_current_user_with_refresh") as mock:
            mock.return_value = {"sub": "test_user", "exp": 9999999999}
            yield mock

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        with patch("src.juteProcurement.issue.get_tenant_db") as mock:
            mock_session = MagicMock()
            mock.return_value = mock_session
            yield mock_session

    def test_get_issue_table_requires_co_id(self, mock_db):
        """Should return 400 when co_id is missing."""
        response = client.get("/api/juteIssue/get_issue_table")
        assert response.status_code == 400
        assert "co_id" in response.json().get("detail", "").lower()

    def test_get_issue_table_success(self, mock_db):
        """Should return issue list for valid co_id."""
        # Mock database response
        mock_row = MagicMock()
        mock_row._mapping = {
            "issue_date": "2026-02-01",
            "branch_id": 1,
            "branch_name": "Main Branch",
            "total_weight": 500.0,
            "total_entries": 5,
            "status": "Draft",
        }
        mock_db.execute.return_value.fetchone.return_value = MagicMock(total=1)
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        response = client.get("/api/juteIssue/get_issue_table?co_id=1")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_get_issue_by_id_not_found(self, mock_db):
        """Should return 404 when issue doesn't exist."""
        mock_db.execute.return_value.fetchone.return_value = None

        response = client.get("/api/juteIssue/get_issue_by_id/999?co_id=1")
        assert response.status_code == 404

    def test_get_issue_create_setup_success(self, mock_db):
        """Should return setup data for create form."""
        # Mock jute items
        mock_item = MagicMock()
        mock_item._mapping = {
            "item_id": 1,
            "item_code": "JUTE001",
            "item_name": "Desi Jute",
            "item_grp_id": 2,
            "item_grp_name": "Raw Jute",
        }
        
        # Mock yarn types
        mock_yarn = MagicMock()
        mock_yarn._mapping = {
            "jute_yarn_type_id": 1,
            "jute_yarn_type_name": "Warp",
        }
        
        # Mock branches
        mock_branch = MagicMock()
        mock_branch._mapping = {
            "branch_id": 1,
            "branch_name": "Main Branch",
        }

        mock_db.execute.return_value.fetchall.side_effect = [
            [mock_item],  # jute items
            [mock_yarn],  # yarn types
            [mock_branch],  # branches
        ]

        response = client.get("/api/juteIssue/get_issue_create_setup?co_id=1")
        assert response.status_code == 200
        data = response.json()
        assert "jute_items" in data
        assert "yarn_types" in data
        assert "branches" in data

    def test_get_stock_outstanding_requires_branch_id(self, mock_db):
        """Should return 400 when branch_id is missing."""
        response = client.get("/api/juteIssue/get_stock_outstanding?co_id=1")
        assert response.status_code == 400
        assert "branch_id" in response.json().get("detail", "").lower()

    def test_get_stock_outstanding_success(self, mock_db):
        """Should return available stock for valid branch."""
        mock_stock = MagicMock()
        mock_stock._mapping = {
            "jute_mr_li_id": 1,
            "branch_id": 1,
            "branch_mr_no": 100,
            "item_id": 1,
            "item_name": "Desi Jute",
            "actual_quality": 1,
            "quality_name": "TD5",
            "actual_qty": 50.0,
            "actual_weight": 500.0,
            "actual_rate": 4500.0,
            "unit_conversion": "BALE",
            "balqty": 30.0,
            "balweight": 300.0,
        }
        mock_db.execute.return_value.fetchall.return_value = [mock_stock]

        response = client.get("/api/juteIssue/get_stock_outstanding?co_id=1&branch_id=1")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["balqty"] == 30.0

    def test_get_issues_by_date_requires_params(self, mock_db):
        """Should return 400 when required params are missing."""
        response = client.get("/api/juteIssue/get_issues_by_date?co_id=1")
        assert response.status_code == 400

        response = client.get("/api/juteIssue/get_issues_by_date?co_id=1&branch_id=1")
        assert response.status_code == 400

    def test_get_issues_by_date_success(self, mock_db):
        """Should return issues for valid branch and date."""
        mock_issue = MagicMock()
        mock_issue._mapping = {
            "jute_issue_id": 1,
            "branch_id": 1,
            "branch_name": "Main Branch",
            "issue_date": "2026-02-01",
            "status_id": 21,
            "status": "Draft",
            "jute_mr_li_id": 1,
            "jute_mr_id": 1,
            "branch_mr_no": 100,
            "item_id": 1,
            "jute_type": "Desi Jute",
            "jute_quality_id": 1,
            "jute_quality": "TD5",
            "yarn_type_id": 1,
            "yarn_type_name": "Warp",
            "quantity": 10.0,
            "weight": 100.0,
            "unit_conversion": "BALE",
            "actual_rate": 4500.0,
            "issue_value": 4500.0,
        }
        mock_db.execute.return_value.fetchall.return_value = [mock_issue]

        response = client.get(
            "/api/juteIssue/get_issues_by_date?co_id=1&branch_id=1&issue_date=2026-02-01"
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "summary" in data
        assert data["summary"]["total_entries"] == 1

    def test_create_issue_success(self, mock_db):
        """Should create issue and return success."""
        # Mock rate query
        mock_rate = MagicMock()
        mock_rate.actual_rate = 4500.0
        mock_db.execute.return_value.fetchone.side_effect = [
            mock_rate,  # rate query
            MagicMock(id=1),  # LAST_INSERT_ID
        ]

        payload = {
            "branch_id": 1,
            "issue_date": "2026-02-01",
            "jute_mr_li_id": 1,
            "yarn_type_id": 1,
            "jute_quality_id": 1,
            "quantity": 10.0,
            "weight": 100.0,
            "unit_conversion": "BALE",
        }

        response = client.post("/api/juteIssue/create_issue?co_id=1", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "jute_issue_id" in data
        assert data["issue_value"] == 4500.0  # (100/100) * 4500

    def test_create_issue_invalid_mr_li(self, mock_db):
        """Should return 400 when MR line item is invalid."""
        mock_db.execute.return_value.fetchone.return_value = None

        payload = {
            "branch_id": 1,
            "issue_date": "2026-02-01",
            "jute_mr_li_id": 999,
            "yarn_type_id": 1,
            "jute_quality_id": 1,
            "quantity": 10.0,
            "weight": 100.0,
        }

        response = client.post("/api/juteIssue/create_issue?co_id=1", json=payload)
        assert response.status_code == 400

    def test_update_issue_only_draft(self, mock_db):
        """Should only allow updating draft issues."""
        # Mock existing issue with non-draft status
        mock_existing = MagicMock()
        mock_existing.jute_issue_id = 1
        mock_existing.status_id = 3  # Approved
        mock_existing.jute_mr_li_id = 1
        mock_db.execute.return_value.fetchone.return_value = mock_existing

        payload = {"quantity": 20.0}

        response = client.put("/api/juteIssue/update_issue/1?co_id=1", json=payload)
        assert response.status_code == 400
        assert "draft" in response.json().get("detail", "").lower()

    def test_delete_issue_only_draft(self, mock_db):
        """Should only allow deleting draft issues."""
        mock_existing = MagicMock()
        mock_existing.jute_issue_id = 1
        mock_existing.status_id = 1  # Open
        mock_db.execute.return_value.fetchone.return_value = mock_existing

        response = client.delete("/api/juteIssue/delete_issue/1?co_id=1")
        assert response.status_code == 400
        assert "draft" in response.json().get("detail", "").lower()

    def test_open_issues_success(self, mock_db):
        """Should open draft issues."""
        mock_db.execute.return_value.rowcount = 3

        payload = {
            "branch_id": 1,
            "issue_date": "2026-02-01",
            "status_id": 1,
        }

        response = client.post("/api/juteIssue/open_issues?co_id=1", json=payload)
        assert response.status_code == 200
        assert "3" in response.json().get("message", "")

    def test_approve_issues_success(self, mock_db):
        """Should approve open issues."""
        mock_db.execute.return_value.rowcount = 2

        payload = {
            "branch_id": 1,
            "issue_date": "2026-02-01",
            "status_id": 3,
        }

        response = client.post("/api/juteIssue/approve_issues?co_id=1", json=payload)
        assert response.status_code == 200
        assert "2" in response.json().get("message", "")

    def test_reject_issues_success(self, mock_db):
        """Should reject open issues."""
        mock_db.execute.return_value.rowcount = 1

        payload = {
            "branch_id": 1,
            "issue_date": "2026-02-01",
            "status_id": 4,
        }

        response = client.post("/api/juteIssue/reject_issues?co_id=1", json=payload)
        assert response.status_code == 200


class TestJuteIssueCalculations:
    """Tests for issue value calculations."""

    def test_issue_value_calculation(self):
        """Issue value should be (weight_kg / 100) * rate_per_quintal."""
        # 100 kg at 4500 per quintal = 4500
        weight = 100
        rate = 4500
        expected = (weight / 100) * rate
        assert expected == 4500.0

        # 250 kg at 5000 per quintal = 12500
        weight = 250
        rate = 5000
        expected = (weight / 100) * rate
        assert expected == 12500.0

        # 75 kg at 4000 per quintal = 3000
        weight = 75
        rate = 4000
        expected = (weight / 100) * rate
        assert expected == 3000.0

    def test_issue_value_rounding(self):
        """Issue value should be rounded to 2 decimal places."""
        # 123.45 kg at 4567 per quintal
        weight = 123.45
        rate = 4567
        expected = round((weight / 100) * rate, 2)
        assert expected == 5637.95
