"""
Tests for Yarn Quality Master endpoints.
Tests for src/masters/yarnQuality.py
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from datetime import datetime

client = TestClient(app)


class TestYarnQualityEndpoints:
    """Tests for Yarn Quality Master API endpoints."""

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_create_setup_success(self, mock_db):
        """Should return yarn types list for create setup."""
        mock_session = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"jute_yarn_type_id": 1, "jute_yarn_type_name": "Polyester"}
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_db.return_value.__enter__.return_value = mock_session

        response = client.get("/api/yarnQualityMaster/yarn_quality_create_setup?co_id=1")
        
        assert response.status_code == 200
        assert "yarn_types" in response.json()
        assert isinstance(response.json()["yarn_types"], list)

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_create_setup_missing_co_id(self, mock_db):
        """Should return 400 when co_id is missing."""
        response = client.get("/api/yarnQualityMaster/yarn_quality_create_setup")
        
        assert response.status_code == 400
        assert "co_id" in response.json().get("detail", "").lower()

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_table_success(self, mock_db):
        """Should return yarn quality list with pagination."""
        mock_session = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "yarn_quality_id": 1,
            "quality_code": "QC001",
            "jute_yarn_type_id": 1,
            "jute_yarn_type_name": "Polyester",
            "twist_per_inch": 10.5,
            "std_count": 20.0,
            "std_doff": 100,
            "std_wt_doff": 5.5,
            "is_active": 1,
            "branch_id": 1,
            "co_id": 1,
        }
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_db.return_value.__enter__.return_value = mock_session

        response = client.get(
            "/api/yarnQualityMaster/yarn_quality_table?co_id=1&page=1&limit=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_table_missing_co_id(self, mock_db):
        """Should return 400 when co_id is missing."""
        response = client.get("/api/yarnQualityMaster/yarn_quality_table")
        
        assert response.status_code == 400
        assert "co_id" in response.json().get("detail", "").lower()

    @patch("src.masters.yarnQuality.get_tenant_db")
    @patch("src.masters.yarnQuality.optional_auth")
    def test_yarn_quality_create_success(self, mock_auth, mock_db):
        """Should create a new yarn quality record."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.fetchone.return_value = None
        
        # Mock check for duplicate
        dup_result = MagicMock()
        dup_result._mapping = {"count": 0}
        mock_session.execute.return_value.fetchone.return_value = dup_result
        
        mock_new_quality = MagicMock()
        mock_new_quality.yarn_quality_id = 1
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()
        
        mock_db.return_value.__enter__.return_value = mock_session

        payload = {
            "co_id": "1",
            "quality_code": "QC001",
            "jute_yarn_type_id": "1",
            "twist_per_inch": "10.5",
            "std_count": "20.0",
            "std_doff": "100",
            "std_wt_doff": "5.5",
            "is_active": 1,
        }

        response = client.post(
            "/api/yarnQualityMaster/yarn_quality_create",
            json=payload
        )
        
        assert response.status_code in [200, 201]
        assert "message" in response.json()

    @patch("src.masters.yarnQuality.get_tenant_db")
    @patch("src.masters.yarnQuality.optional_auth")
    def test_yarn_quality_create_missing_quality_code(self, mock_auth, mock_db):
        """Should return 400 when quality_code is missing."""
        mock_auth.return_value = {"user_id": 1}
        mock_db.return_value.__enter__.return_value = MagicMock()

        payload = {
            "co_id": "1",
            "jute_yarn_type_id": "1",
            "twist_per_inch": "10.5",
        }

        response = client.post(
            "/api/yarnQualityMaster/yarn_quality_create",
            json=payload
        )
        
        assert response.status_code == 400
        assert "required" in response.json().get("detail", "").lower()

    @patch("src.masters.yarnQuality.get_tenant_db")
    @patch("src.masters.yarnQuality.optional_auth")
    def test_yarn_quality_create_duplicate_code(self, mock_auth, mock_db):
        """Should return 409 when quality code already exists."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()
        
        # Mock duplicate check returning existing record
        dup_result = MagicMock()
        dup_result._mapping = {"count": 1}
        mock_session.execute.return_value.fetchone.return_value = dup_result
        
        mock_db.return_value.__enter__.return_value = mock_session

        payload = {
            "co_id": "1",
            "quality_code": "QC001",
            "jute_yarn_type_id": "1",
            "twist_per_inch": "10.5",
        }

        response = client.post(
            "/api/yarnQualityMaster/yarn_quality_create",
            json=payload
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "").lower()

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_edit_setup_success(self, mock_db):
        """Should return yarn quality details and types for edit."""
        mock_session = MagicMock()
        
        # Mock quality details
        quality_row = MagicMock()
        quality_row._mapping = {
            "yarn_quality_id": 1,
            "quality_code": "QC001",
            "jute_yarn_type_id": 1,
            "jute_yarn_type_name": "Polyester",
            "twist_per_inch": 10.5,
            "std_count": 20.0,
            "std_doff": 100,
            "std_wt_doff": 5.5,
            "is_active": 1,
            "branch_id": 1,
            "co_id": 1,
        }
        
        # Mock yarn types
        type_row = MagicMock()
        type_row._mapping = {"jute_yarn_type_id": 1, "jute_yarn_type_name": "Polyester"}
        
        # First call returns quality, second call returns types
        mock_session.execute.return_value.fetchall.return_value = [type_row]
        mock_session.execute.return_value.fetchone.return_value = quality_row
        
        mock_db.return_value.__enter__.return_value = mock_session

        response = client.get(
            "/api/yarnQualityMaster/yarn_quality_edit_setup?co_id=1&yarn_quality_id=1"
        )
        
        assert response.status_code == 200
        assert "yarn_quality_details" in response.json()
        assert "yarn_types" in response.json()

    @patch("src.masters.yarnQuality.get_tenant_db")
    def test_yarn_quality_edit_setup_not_found(self, mock_db):
        """Should return 404 when yarn quality not found."""
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = None
        mock_db.return_value.__enter__.return_value = mock_session

        response = client.get(
            "/api/yarnQualityMaster/yarn_quality_edit_setup?co_id=1&yarn_quality_id=999"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    @patch("src.masters.yarnQuality.get_tenant_db")
    @patch("src.masters.yarnQuality.optional_auth")
    def test_yarn_quality_edit_success(self, mock_auth, mock_db):
        """Should update an existing yarn quality record."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()
        
        # Mock existing record
        existing = MagicMock()
        existing.yarn_quality_id = 1
        existing.quality_code = "QC001"
        existing.jute_yarn_type_id = 1
        existing.twist_per_inch = 10.5
        existing.std_count = 20.0
        existing.std_doff = 100
        existing.std_wt_doff = 5.5
        existing.is_active = 1
        existing.updated_by = 1
        
        mock_session.query.return_value.filter.return_value.first.return_value = existing
        mock_session.execute.return_value.fetchone.return_value = MagicMock(_mapping={"count": 0})
        
        mock_db.return_value.__enter__.return_value = mock_session

        payload = {
            "yarn_quality_id": "1",
            "co_id": "1",
            "quality_code": "QC001_UPDATED",
            "jute_yarn_type_id": "1",
            "twist_per_inch": "11.0",
            "std_count": "21.0",
            "std_doff": "101",
            "std_wt_doff": "5.6",
            "is_active": 1,
        }

        response = client.put(
            "/api/yarnQualityMaster/yarn_quality_edit",
            json=payload
        )
        
        assert response.status_code == 200
        assert "message" in response.json()

    @patch("src.masters.yarnQuality.get_tenant_db")
    @patch("src.masters.yarnQuality.optional_auth")
    def test_yarn_quality_edit_not_found(self, mock_auth, mock_db):
        """Should return 404 when yarn quality to edit not found."""
        mock_auth.return_value = {"user_id": 1}
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.return_value.__enter__.return_value = mock_session

        payload = {
            "yarn_quality_id": "999",
            "co_id": "1",
            "quality_code": "QC001",
            "yarn_type_id": "1",
        }

        response = client.put(
            "/api/yarnQualityMaster/yarn_quality_edit",
            json=payload
        )
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
