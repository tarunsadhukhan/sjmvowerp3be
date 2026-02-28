"""
Tests for jute sales invoice functionality.
Covers: setup (mukam_list), create with jute extension, get_by_id with jute data,
update with jute extension, and claim amount deduction.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from src.main import app
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh

client = TestClient(app)


def _mock_row(mapping: dict):
    row = MagicMock()
    row._mapping = mapping
    return row


def _setup_side_effects():
    """Return the 9 mock DB calls for get_sales_invoice_setup_1."""
    return [
        MagicMock(fetchall=lambda: [_mock_row({"branch_id": 1, "branch_name": "Main"})]),  # branches
        MagicMock(fetchall=lambda: [_mock_row({"party_id": 10, "party_name": "Customer A"})]),  # customers
        MagicMock(fetchall=lambda: []),  # customer_branches
        MagicMock(fetchall=lambda: []),  # brokers
        MagicMock(fetchall=lambda: []),  # transporters
        MagicMock(fetchall=lambda: []),  # approved_delivery_orders
        MagicMock(fetchall=lambda: [_mock_row({"item_grp_id": 5, "item_grp_name": "Jute"})]),  # item_groups
        MagicMock(fetchall=lambda: [
            _mock_row({"invoice_type_id": 1, "invoice_type_name": "Regular"}),
            _mock_row({"invoice_type_id": 3, "invoice_type_name": "Jute"}),
        ]),  # invoice_types
        MagicMock(fetchall=lambda: [
            _mock_row({"mukam_id": 1, "mukam_name": "Kolkata"}),
            _mock_row({"mukam_id": 2, "mukam_name": "Siliguri"}),
        ]),  # mukam_list
    ]


class TestSalesInvoiceJuteSetup:

    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        self._mock_session = MagicMock()
        app.dependency_overrides[get_current_user_with_refresh] = lambda: {"user_id": 1}
        app.dependency_overrides[get_tenant_db] = lambda: self._mock_session
        yield
        app.dependency_overrides.clear()

    def test_setup_returns_mukam_list(self):
        """Setup response should include mukam_list array."""
        self._mock_session.execute.side_effect = _setup_side_effects()

        response = client.get("/api/salesInvoice/get_sales_invoice_setup_1?co_id=1&branch_id=1")

        assert response.status_code == 200
        body = response.json()
        assert "mukam_list" in body
        assert len(body["mukam_list"]) == 2
        assert body["mukam_list"][0]["mukam_id"] == 1
        assert body["mukam_list"][0]["mukam_name"] == "Kolkata"
        assert body["mukam_list"][1]["mukam_id"] == 2
        assert body["mukam_list"][1]["mukam_name"] == "Siliguri"

    def test_setup_returns_empty_mukam_list(self):
        """Should return empty mukam_list when no mukam entries exist."""
        effects = _setup_side_effects()
        # Override mukam_list (9th call) to empty
        effects[8] = MagicMock(fetchall=lambda: [])
        self._mock_session.execute.side_effect = effects

        response = client.get("/api/salesInvoice/get_sales_invoice_setup_1?co_id=1")

        assert response.status_code == 200
        body = response.json()
        assert "mukam_list" in body
        assert body["mukam_list"] == []


class TestCreateJuteInvoice:

    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        self._mock_session = MagicMock()
        app.dependency_overrides[get_current_user_with_refresh] = lambda: {"user_id": 1}
        app.dependency_overrides[get_tenant_db] = lambda: self._mock_session
        yield
        app.dependency_overrides.clear()

    def test_create_jute_invoice_with_extension(self):
        """Creating a jute invoice should insert header, line items, and jute extension."""
        # Mock: branch lookup, then header insert, line item insert, jute insert
        branch_row = _mock_row({"co_id": 1})
        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: branch_row),  # branch co_id lookup
            MagicMock(lastrowid=100),  # insert header
            MagicMock(),  # insert line item 1
            MagicMock(),  # insert jute extension
        ]

        payload = {
            "branch": "1",
            "party": "10",
            "date": "2026-02-26",
            "invoice_type": 3,
            "gross_amount": 50000,
            "vehicle_no": "WB-01-1234",
            "items": [
                {
                    "item": "101",
                    "item_name": "Jute CRM",
                    "item_group": "5",
                    "uom": "kg",
                    "uom_name": "kg",
                    "quantity": 1000,
                    "rate": 50,
                    "net_amount": 50000,
                    "total_amount": 50000,
                    "qty_2": 10,
                    "uom_2": "BALE",
                },
            ],
            "jute": {
                "despatch_doc_no": "DSP-001",
                "despatched_through": "Truck",
                "mukam_id": "1",
                "unit_conversion": "BALE",
                "claim_amount": 500,
                "claim_note": "Quality deduction",
                "other_reference": "REF-123",
            },
        }

        response = client.post("/api/salesInvoice/create_sales_invoice", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["invoice_id"] == 100
        assert body["message"] == "Sales invoice created successfully"

        # Verify commit was called
        self._mock_session.commit.assert_called_once()

        # Verify 4 execute calls: branch lookup + header + line + jute
        assert self._mock_session.execute.call_count == 4

    def test_create_jute_invoice_claim_deducted_from_amount(self):
        """Invoice amount should be gross_amount minus claim_amount for jute invoices."""
        branch_row = _mock_row({"co_id": 1})
        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: branch_row),  # branch co_id lookup
            MagicMock(lastrowid=101),  # insert header
            MagicMock(),  # insert line item
            MagicMock(),  # insert jute extension
        ]

        payload = {
            "branch": "1",
            "party": "10",
            "date": "2026-02-26",
            "invoice_type": 3,
            "gross_amount": 10000,
            "items": [
                {
                    "item": "101",
                    "item_name": "Jute CRM",
                    "item_group": "5",
                    "uom": "kg",
                    "uom_name": "kg",
                    "quantity": 200,
                    "rate": 50,
                    "net_amount": 10000,
                    "total_amount": 10000,
                },
            ],
            "jute": {
                "claim_amount": 1500.50,
                "unit_conversion": "LOOSE",
            },
        }

        response = client.post("/api/salesInvoice/create_sales_invoice", json=payload)

        assert response.status_code == 200

        # Check the header insert call (2nd execute call, index 1)
        header_call_args = self._mock_session.execute.call_args_list[1]
        header_params = header_call_args[0][1]  # positional arg [1] = params dict
        # invoice_amount should be 10000 - 1500.50 = 8499.50
        assert header_params["invoice_amount"] == 8499.50

    def test_create_invoice_without_jute_data(self):
        """Creating a regular invoice without jute data should still work."""
        branch_row = _mock_row({"co_id": 1})
        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: branch_row),  # branch co_id lookup
            MagicMock(lastrowid=102),  # insert header
            MagicMock(),  # insert line item
            # No jute insert expected
        ]

        payload = {
            "branch": "1",
            "party": "10",
            "date": "2026-02-26",
            "invoice_type": 1,
            "gross_amount": 5000,
            "items": [
                {
                    "item": "50",
                    "item_name": "Widget",
                    "item_group": "2",
                    "uom": "pcs",
                    "uom_name": "pcs",
                    "quantity": 100,
                    "rate": 50,
                    "net_amount": 5000,
                    "total_amount": 5000,
                },
            ],
        }

        response = client.post("/api/salesInvoice/create_sales_invoice", json=payload)

        assert response.status_code == 200
        # Only 3 execute calls: branch lookup + header + line item (no jute insert)
        assert self._mock_session.execute.call_count == 3

    def test_create_jute_invoice_line_item_has_qty2_uom2(self):
        """Line items should include qty_2 and uom_2 params."""
        branch_row = _mock_row({"co_id": 1})
        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: branch_row),
            MagicMock(lastrowid=103),
            MagicMock(),  # line item insert
            MagicMock(),  # jute insert
        ]

        payload = {
            "branch": "1",
            "party": "10",
            "date": "2026-02-26",
            "invoice_type": 3,
            "gross_amount": 20000,
            "items": [
                {
                    "item": "101",
                    "item_name": "Jute CRM",
                    "item_group": "5",
                    "uom": "kg",
                    "uom_name": "kg",
                    "quantity": 400,
                    "rate": 50,
                    "net_amount": 20000,
                    "total_amount": 20000,
                    "qty_2": 8,
                    "uom_2": "BALE",
                },
            ],
            "jute": {
                "unit_conversion": "BALE",
            },
        }

        response = client.post("/api/salesInvoice/create_sales_invoice", json=payload)
        assert response.status_code == 200

        # Check the line item insert call (3rd execute call, index 2)
        line_call_args = self._mock_session.execute.call_args_list[2]
        line_params = line_call_args[0][1]
        assert line_params["qty_2"] == 8.0
        assert line_params["uom_2"] == "BALE"


class TestGetJuteInvoiceById:

    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        self._mock_session = MagicMock()
        app.dependency_overrides[get_current_user_with_refresh] = lambda: {"user_id": 1}
        app.dependency_overrides[get_tenant_db] = lambda: self._mock_session
        yield
        app.dependency_overrides.clear()

    def test_get_by_id_includes_jute_data(self):
        """Get by ID should return jute-specific fields when present."""
        header = _mock_row({
            "invoice_id": 100,
            "invoice_no": None,
            "invoice_date": "2026-02-26",
            "challan_no": None,
            "challan_date": None,
            "branch_id": 1,
            "branch_name": "Main",
            "branch_prefix": "MN",
            "co_id": 1,
            "co_prefix": "CO",
            "party_id": 10,
            "party_name": "Customer A",
            "sales_delivery_order_id": None,
            "broker_id": None,
            "shipping_state_code": None,
            "transporter_id": None,
            "transporter_name": None,
            "vehicle_no": "WB-01-1234",
            "eway_bill_no": None,
            "eway_bill_date": None,
            "invoice_type": 3,
            "footer_notes": None,
            "terms": None,
            "terms_conditions": None,
            "invoice_amount": 49500,
            "tax_amount": 0,
            "tax_payable": None,
            "freight_charges": 0,
            "round_off": 0,
            "status_id": 21,
            "status_name": "Draft",
            "updated_by": 1,
            "updated_date_time": "2026-02-26 10:00:00",
            "intra_inter_state": None,
        })

        detail = _mock_row({
            "invoice_line_item_id": 200,
            "invoice_id": 100,
            "delivery_line_id": None,
            "hsn_code": "5303",
            "item_id": "101",
            "item_name": "Jute CRM",
            "item_group": "5",
            "item_grp_id": 5,
            "make": None,
            "quantity": 1000,
            "uom": "kg",
            "uom_id": 7,
            "rate": 50,
            "amount_without_tax": 50000,
            "tax_amount": 0,
            "total_amount": 50000,
            "cgst_amt": 0,
            "cgst_per": 0,
            "sgst_amt": 0,
            "sgst_per": 0,
            "igst_amt": 0,
            "igst_per": 0,
            "item_description": None,
            "qty_2": 10,
            "uom_2": "BALE",
        })

        jute = _mock_row({
            "sale_invoice_jute_id": 1,
            "invoice_id": 100,
            "mr_no": None,
            "mr_id": None,
            "claim_amount": 500.00,
            "other_reference": "REF-123",
            "unit_conversion": "BALE",
            "despatch_doc_no": "DSP-001",
            "despatched_through": "Truck",
            "mukam_id": 1,
            "mukam_name": "Kolkata",
            "claim_note": "Quality deduction",
        })

        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: header),   # header query
            MagicMock(fetchall=lambda: [detail]),  # detail query
            MagicMock(fetchone=lambda: jute),      # jute query
        ]

        response = client.get("/api/salesInvoice/get_sales_invoice_by_id?invoice_id=100&co_id=1")

        assert response.status_code == 200
        body = response.json()

        # Verify jute section
        assert "jute" in body
        assert body["jute"]["claimAmount"] == 500.00
        assert body["jute"]["otherReference"] == "REF-123"
        assert body["jute"]["unitConversion"] == "BALE"
        assert body["jute"]["despatchDocNo"] == "DSP-001"
        assert body["jute"]["despatchedThrough"] == "Truck"
        assert body["jute"]["mukamId"] == 1
        assert body["jute"]["mukamName"] == "Kolkata"
        assert body["jute"]["claimNote"] == "Quality deduction"

        # Verify line items include qty2/uom2
        assert len(body["lines"]) == 1
        assert body["lines"][0]["qty2"] == 10.0
        assert body["lines"][0]["uom2"] == "BALE"

    def test_get_by_id_without_jute_data(self):
        """Get by ID for a non-jute invoice should not include jute section."""
        header = _mock_row({
            "invoice_id": 101,
            "invoice_no": 1,
            "invoice_date": "2026-02-26",
            "challan_no": None,
            "challan_date": None,
            "branch_id": 1,
            "branch_name": "Main",
            "branch_prefix": "MN",
            "co_id": 1,
            "co_prefix": "CO",
            "party_id": 10,
            "party_name": "Customer A",
            "sales_delivery_order_id": None,
            "broker_id": None,
            "shipping_state_code": None,
            "transporter_id": None,
            "transporter_name": None,
            "vehicle_no": None,
            "eway_bill_no": None,
            "eway_bill_date": None,
            "invoice_type": 1,
            "footer_notes": None,
            "terms": None,
            "terms_conditions": None,
            "invoice_amount": 5000,
            "tax_amount": 0,
            "tax_payable": None,
            "freight_charges": 0,
            "round_off": 0,
            "status_id": 1,
            "status_name": "Open",
            "updated_by": 1,
            "updated_date_time": "2026-02-26 10:00:00",
            "intra_inter_state": None,
        })

        detail = _mock_row({
            "invoice_line_item_id": 300,
            "invoice_id": 101,
            "delivery_line_id": None,
            "hsn_code": None,
            "item_id": "50",
            "item_name": "Widget",
            "item_group": "2",
            "item_grp_id": 2,
            "make": None,
            "quantity": 100,
            "uom": "pcs",
            "uom_id": 1,
            "rate": 50,
            "amount_without_tax": 5000,
            "tax_amount": 0,
            "total_amount": 5000,
            "cgst_amt": 0,
            "cgst_per": 0,
            "sgst_amt": 0,
            "sgst_per": 0,
            "igst_amt": 0,
            "igst_per": 0,
            "item_description": None,
            "qty_2": None,
            "uom_2": None,
        })

        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: header),
            MagicMock(fetchall=lambda: [detail]),
            MagicMock(fetchone=lambda: None),  # no jute data
        ]

        response = client.get("/api/salesInvoice/get_sales_invoice_by_id?invoice_id=101&co_id=1")

        assert response.status_code == 200
        body = response.json()
        assert "jute" not in body
        assert body["lines"][0]["qty2"] is None
        assert body["lines"][0]["uom2"] is None


class TestUpdateJuteInvoice:

    @pytest.fixture(autouse=True)
    def setup_overrides(self):
        self._mock_session = MagicMock()
        app.dependency_overrides[get_current_user_with_refresh] = lambda: {"user_id": 1}
        app.dependency_overrides[get_tenant_db] = lambda: self._mock_session
        yield
        app.dependency_overrides.clear()

    def test_update_jute_invoice_reinserts_extension(self):
        """Updating a jute invoice should delete and re-insert jute extension."""
        check_row = _mock_row({"invoice_id": 100, "status_id": 21, "is_active": 1})
        self._mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: check_row),  # check exists
            MagicMock(),  # update header
            MagicMock(),  # soft-delete old line items
            MagicMock(),  # re-insert line item
            MagicMock(),  # delete old jute extension
            MagicMock(),  # re-insert jute extension
        ]

        payload = {
            "id": "100",
            "branch": "1",
            "party": "10",
            "date": "2026-02-26",
            "invoice_type": 3,
            "gross_amount": 40000,
            "items": [
                {
                    "item": "101",
                    "item_name": "Jute CRM",
                    "item_group": "5",
                    "uom": "kg",
                    "uom_name": "kg",
                    "quantity": 800,
                    "rate": 50,
                    "net_amount": 40000,
                    "total_amount": 40000,
                    "qty_2": 16,
                    "uom_2": "BALE",
                },
            ],
            "jute": {
                "despatch_doc_no": "DSP-002",
                "despatched_through": "Hand Cart",
                "mukam_id": "2",
                "unit_conversion": "BALE",
                "claim_amount": 200,
                "claim_note": "Minor quality issue",
            },
        }

        response = client.put("/api/salesInvoice/update_sales_invoice", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Sales invoice updated successfully"
        self._mock_session.commit.assert_called_once()

        # 6 execute calls: check + update_hdr + delete_lines + insert_line + delete_jute + insert_jute
        assert self._mock_session.execute.call_count == 6
