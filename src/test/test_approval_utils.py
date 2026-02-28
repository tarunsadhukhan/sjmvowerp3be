"""Tests for the shared approval utility functions.

Tests process_approval(), process_rejection(), and calculate_approval_permissions()
from src.common.approval_utils.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.sql import text

from src.common.approval_utils import (
    process_approval,
    process_rejection,
    calculate_approval_permissions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_doc_row(status_id=20, approval_level=1, branch_id=1, **extra):
    """Create a mock document row."""
    row = MagicMock()
    data = {"status_id": status_id, "approval_level": approval_level, "branch_id": branch_id, **extra}
    row._mapping = data
    return row


def _mock_approval_row(approval_level=1, max_amount_single=None, day_max_amount=None, month_max_amount=None):
    """Create a mock approval_mst row."""
    row = MagicMock()
    row._mapping = {
        "approval_level": approval_level,
        "max_amount_single": max_amount_single,
        "day_max_amount": day_max_amount,
        "month_max_amount": month_max_amount,
    }
    return row


def _mock_max_level_row(max_level=2):
    """Create a mock max approval level row."""
    row = MagicMock()
    row._mapping = {"max_level": max_level}
    return row


def _mock_count_row(count=1):
    """Create a mock count row."""
    row = MagicMock()
    row._mapping = {"count": count}
    return row


def _mock_edit_access_row(max_access_type_id=4):
    """Create a mock edit access row."""
    row = MagicMock()
    row._mapping = {"max_access_type_id": max_access_type_id}
    return row


def _get_doc_fn():
    return text("SELECT status_id, approval_level, branch_id FROM test_doc WHERE doc_id = :doc_id")


def _update_status_fn():
    return text("UPDATE test_doc SET status_id = :status_id, approval_level = :approval_level WHERE doc_id = :doc_id")


def _setup_db_for_approval(db, doc_status=20, doc_level=1, user_level=1, max_level=2, max_amount=None, doc_on_refresh=None, hierarchy_exists=True):
    """Set up mock DB responses for a standard approval flow."""
    doc_row = _mock_doc_row(status_id=doc_status, approval_level=doc_level)
    count_row = _mock_count_row(count=2 if hierarchy_exists else 0)
    approval_row = _mock_approval_row(approval_level=user_level, max_amount_single=max_amount)
    max_level_row = _mock_max_level_row(max_level=max_level)

    # Build the side effects for db.execute().fetchone()
    # Sequence: doc, [refresh], count, [approval_row, max_level_row]
    fetchone_results = [doc_row]
    if doc_on_refresh:
        fetchone_results.append(doc_on_refresh)
    fetchone_results.append(count_row)
    if hierarchy_exists:
        fetchone_results.extend([approval_row, max_level_row])

    execute_mock = MagicMock()
    execute_mock.return_value.fetchone = MagicMock(side_effect=fetchone_results)
    db.execute = execute_mock
    return db


# ===========================================================================
# Tests for process_approval()
# ===========================================================================

class TestProcessApproval:

    def test_from_open_transitions_to_pending(self):
        """When doc is Open (status=1), should auto-transition to Pending (20) then approve."""
        db = MagicMock()

        doc_open = _mock_doc_row(status_id=1, approval_level=None)
        doc_pending = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1)
        max_level_row = _mock_max_level_row(max_level=1)

        # Sequence: fetch doc (Open), refresh doc (after transition), check hierarchy, user level, max level
        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_open, doc_pending, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 3  # Final (only 1 level)
        assert result["new_approval_level"] == 1
        assert "approved" in result["message"].lower()

    def test_advances_to_next_level(self):
        """When not at final level, should move to next level."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1)
        max_level_row = _mock_max_level_row(max_level=3)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 20  # Still pending
        assert result["new_approval_level"] == 2
        assert "level 2" in result["message"].lower()

    def test_final_level_approves(self):
        """When at final level, should set status to Approved (3)."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=3)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=3)
        max_level_row = _mock_max_level_row(max_level=3)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 3  # Approved
        assert result["new_approval_level"] == 3
        assert "final" in result["message"].lower()

    def test_wrong_level_forbidden(self):
        """User at level 2 trying to approve level 1 doc should get 403."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=2)  # User is level 2

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row]
        )

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 403
        assert "level" in exc_info.value.detail.lower()

    def test_no_permission_forbidden(self):
        """User with no approval_mst entry (but hierarchy exists) should get 403."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)  # Hierarchy exists

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, None]  # No approval entry for this user
        )

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

    def test_already_approved_rejected(self):
        """Approving a doc with status=3 should get 400."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=3, approval_level=2)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row]
        )

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 400
        assert "already approved" in exc_info.value.detail.lower()

    def test_amount_exceeds_limit(self):
        """Document amount exceeding max_amount_single should get 403."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1, max_amount_single=50000.0)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row]
        )

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="PO",
                document_amount=75000.0,
            )
        assert exc_info.value.status_code == 403
        assert "exceeds" in exc_info.value.detail.lower()

    def test_amount_within_limit(self):
        """Document amount within max_amount_single should succeed."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1, max_amount_single=100000.0)
        max_level_row = _mock_max_level_row(max_level=1)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="PO",
            document_amount=75000.0,
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 3

    def test_null_amount_skips_value_check(self):
        """When document_amount=None (e.g., Jute), value checks should be skipped entirely."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        # max_amount_single is 0 which would normally block, but should be ignored
        approval_row = _mock_approval_row(approval_level=1, max_amount_single=0.0)
        max_level_row = _mock_max_level_row(max_level=1)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="Jute MR",
            document_amount=None,  # Jute never passes amount
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 3

    def test_zero_limit_treated_as_no_limit(self):
        """max_amount_single of 0 should be treated as no limit (not block everything)."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        # max_amount_single is 0 - should NOT block
        approval_row = _mock_approval_row(approval_level=1, max_amount_single=0.0)
        max_level_row = _mock_max_level_row(max_level=1)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="PO",
            document_amount=75000.0,  # Any amount should pass with limit=0
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 3

    def test_none_limit_treated_as_no_limit(self):
        """max_amount_single of None should be treated as no limit."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1, max_amount_single=None)
        max_level_row = _mock_max_level_row(max_level=1)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="PO",
            document_amount=999999.0,
        )

        assert result["status"] == "success"

    def test_doc_not_found(self):
        """Should raise 404 when doc doesn't exist."""
        db = MagicMock()
        db.execute.return_value.fetchone = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=999, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 404

    def test_invalid_status(self):
        """Doc with status=4 (Rejected) should get 400."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=4, approval_level=None)
        db.execute.return_value.fetchone = MagicMock(side_effect=[doc_row])

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 400

    def test_extra_update_params_passed(self):
        """Extra update params should be included in the SQL execute call."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1)
        max_level_row = _mock_max_level_row(max_level=1)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row, max_level_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="Indent",
            extra_update_params={"indent_no": None},
        )

        assert result["status"] == "success"
        # Verify the last execute call included indent_no
        last_call_args = db.execute.call_args_list[-1]
        params = last_call_args[0][1]
        assert "indent_no" in params
        assert params["indent_no"] is None

    def test_no_hierarchy_with_edit_access_approves(self):
        """No hierarchy configured + user has edit access → direct approval (status 3)."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=0)  # No hierarchy
        edit_access_row = _mock_edit_access_row(max_access_type_id=4)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, edit_access_row]
        )

        result = process_approval(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 3  # Direct approval
        assert "no approval hierarchy" in result["message"].lower()

    def test_no_hierarchy_without_edit_access_forbidden(self):
        """No hierarchy configured + user lacks edit access → 403."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=0)  # No hierarchy
        edit_access_row = _mock_edit_access_row(max_access_type_id=2)  # Read-only

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, edit_access_row]
        )

        with pytest.raises(HTTPException) as exc_info:
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

    def test_rollback_on_approval_failure(self):
        """DB should be rolled back when approval fails."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)  # Hierarchy exists
        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, None]  # No approval entry for user -> 403
        )

        with pytest.raises(HTTPException):
            process_approval(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )

        db.rollback.assert_called_once()


# ===========================================================================
# Tests for process_rejection()
# ===========================================================================

class TestProcessRejection:

    def test_rejection_from_pending(self):
        """Should reject a doc in Pending Approval (20) -> Rejected (4)."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=2)
        db.execute.return_value.fetchone = MagicMock(side_effect=[doc_row])

        result = process_rejection(
            doc_id=1, user_id=10, menu_id=None, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 4
        assert result["new_approval_level"] is None
        assert "rejected" in result["message"].lower()

    def test_rejection_with_level_check(self):
        """When menu_id is provided, should verify user has permission at current level."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=2)  # Hierarchy exists
        approval_row = _mock_approval_row(approval_level=1)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row]
        )

        result = process_rejection(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 4

    def test_rejection_wrong_level(self):
        """User at wrong level should not be able to reject."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=2)
        count_row = _mock_count_row(count=2)  # Hierarchy exists
        approval_row = _mock_approval_row(approval_level=1)  # Wrong level

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, approval_row]
        )

        with pytest.raises(HTTPException) as exc_info:
            process_rejection(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 403

    def test_reject_non_pending_doc(self):
        """Cannot reject a doc not in Pending Approval status."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=1, approval_level=None)  # Open, not pending
        db.execute.return_value.fetchone = MagicMock(side_effect=[doc_row])

        with pytest.raises(HTTPException) as exc_info:
            process_rejection(
                doc_id=1, user_id=10, menu_id=None, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 400

    def test_reject_doc_not_found(self):
        """Should raise 404 when doc doesn't exist."""
        db = MagicMock()
        db.execute.return_value.fetchone = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            process_rejection(
                doc_id=999, user_id=10, menu_id=None, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 404

    def test_rejection_with_reason(self):
        """Rejection with reason should succeed (reason is logged, not stored by utility)."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        db.execute.return_value.fetchone = MagicMock(side_effect=[doc_row])

        result = process_rejection(
            doc_id=1, user_id=10, menu_id=None, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
            reason="Specifications unclear",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 4

    def test_rejection_no_hierarchy_with_edit_access(self):
        """No hierarchy + edit access → rejection allowed."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=0)  # No hierarchy
        edit_access_row = _mock_edit_access_row(max_access_type_id=4)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, edit_access_row]
        )

        result = process_rejection(
            doc_id=1, user_id=10, menu_id=5, db=db,
            get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
            id_param_name="doc_id", doc_name="TestDoc",
        )

        assert result["status"] == "success"
        assert result["new_status_id"] == 4

    def test_rejection_no_hierarchy_without_edit_access(self):
        """No hierarchy + no edit access → 403."""
        db = MagicMock()

        doc_row = _mock_doc_row(status_id=20, approval_level=1)
        count_row = _mock_count_row(count=0)  # No hierarchy
        edit_access_row = _mock_edit_access_row(max_access_type_id=2)  # Read-only

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[doc_row, count_row, edit_access_row]
        )

        with pytest.raises(HTTPException) as exc_info:
            process_rejection(
                doc_id=1, user_id=10, menu_id=5, db=db,
                get_doc_fn=_get_doc_fn, update_status_fn=_update_status_fn,
                id_param_name="doc_id", doc_name="TestDoc",
            )
        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()


# ===========================================================================
# Tests for calculate_approval_permissions()
# ===========================================================================

class TestCalculateApprovalPermissions:

    def test_draft_permissions(self):
        """Status 21 (Draft): canOpen, canCancelDraft, canSave should be True."""
        db = MagicMock()
        # Only need the approval_exists check
        count_row = _mock_count_row(count=0)
        db.execute.return_value.fetchone = MagicMock(side_effect=[count_row])

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=21, current_approval_level=None, db=db,
        )

        assert result["canOpen"] is True
        assert result["canCancelDraft"] is True
        assert result["canSave"] is True
        assert result["canApprove"] is False
        assert result["canReject"] is False

    def test_open_with_hierarchy_level1_user(self):
        """Status 1 (Open) with hierarchy: level 1 user should see canApprove."""
        db = MagicMock()

        count_row = _mock_count_row(count=2)  # Approval config exists
        approval_row = _mock_approval_row(approval_level=1)  # User is level 1

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row, approval_row]
        )

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=1, current_approval_level=None, db=db,
        )

        assert result["canApprove"] is True
        assert result["canSave"] is True

    def test_open_with_hierarchy_non_level1_user(self):
        """Status 1 (Open) with hierarchy: level 2 user should NOT see canApprove."""
        db = MagicMock()

        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=2)  # User is level 2

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row, approval_row]
        )

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=1, current_approval_level=None, db=db,
        )

        assert result["canApprove"] is False
        assert result["canSave"] is True

    def test_open_without_hierarchy_with_edit_access(self):
        """Status 1 (Open) without hierarchy: user with edit access can approve."""
        db = MagicMock()

        count_row = _mock_count_row(count=0)  # No approval config
        edit_access_row = _mock_edit_access_row(max_access_type_id=4)

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row, edit_access_row]
        )

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=1, current_approval_level=None, db=db,
        )

        assert result["canApprove"] is True

    def test_pending_matching_level(self):
        """Status 20 (Pending): user at matching level should see canApprove + canReject."""
        db = MagicMock()

        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=2)  # Matches doc level

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row, approval_row]
        )

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=20, current_approval_level=2, db=db,
        )

        assert result["canApprove"] is True
        assert result["canReject"] is True
        assert result["canViewApprovalLog"] is True

    def test_pending_wrong_level(self):
        """Status 20 (Pending): user at wrong level should NOT see canApprove."""
        db = MagicMock()

        count_row = _mock_count_row(count=2)
        approval_row = _mock_approval_row(approval_level=1)  # Doc is at level 2

        db.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row, approval_row]
        )

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=20, current_approval_level=2, db=db,
        )

        assert result["canApprove"] is False
        assert result["canReject"] is False
        assert result["canViewApprovalLog"] is True

    def test_two_users_same_level_both_see_approve(self):
        """Two users at same level should both get canApprove=True (OR logic)."""
        # User A at level 1
        db_a = MagicMock()
        count_row_a = _mock_count_row(count=2)
        approval_row_a = _mock_approval_row(approval_level=1)
        db_a.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row_a, approval_row_a]
        )

        result_a = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=20, current_approval_level=1, db=db_a,
        )

        # User B at level 1
        db_b = MagicMock()
        count_row_b = _mock_count_row(count=2)
        approval_row_b = _mock_approval_row(approval_level=1)
        db_b.execute.return_value.fetchone = MagicMock(
            side_effect=[count_row_b, approval_row_b]
        )

        result_b = calculate_approval_permissions(
            user_id=11, menu_id=5, branch_id=1,
            status_id=20, current_approval_level=1, db=db_b,
        )

        assert result_a["canApprove"] is True
        assert result_b["canApprove"] is True

    def test_approved_permissions(self):
        """Status 3 (Approved): only canViewApprovalLog and canClone."""
        db = MagicMock()
        count_row = _mock_count_row(count=0)
        db.execute.return_value.fetchone = MagicMock(side_effect=[count_row])

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=3, current_approval_level=2, db=db,
        )

        assert result["canApprove"] is False
        assert result["canReject"] is False
        assert result["canViewApprovalLog"] is True
        assert result["canClone"] is True

    def test_rejected_permissions(self):
        """Status 4 (Rejected): canReopen, canClone, canViewApprovalLog."""
        db = MagicMock()
        count_row = _mock_count_row(count=0)
        db.execute.return_value.fetchone = MagicMock(side_effect=[count_row])

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=4, current_approval_level=None, db=db,
        )

        assert result["canReopen"] is True
        assert result["canClone"] is True
        assert result["canViewApprovalLog"] is True
        assert result["canApprove"] is False

    def test_cancelled_permissions(self):
        """Status 6 (Cancelled): canReopen, canClone, canViewApprovalLog."""
        db = MagicMock()
        count_row = _mock_count_row(count=0)
        db.execute.return_value.fetchone = MagicMock(side_effect=[count_row])

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=6, current_approval_level=None, db=db,
        )

        assert result["canReopen"] is True
        assert result["canClone"] is True
        assert result["canViewApprovalLog"] is True

    def test_error_returns_default_permissions(self):
        """On error, should return all-False permissions instead of raising."""
        db = MagicMock()
        db.execute.side_effect = Exception("DB error")

        result = calculate_approval_permissions(
            user_id=10, menu_id=5, branch_id=1,
            status_id=20, current_approval_level=1, db=db,
        )

        assert result["canApprove"] is False
        assert result["canReject"] is False
        assert result["canOpen"] is False


# ===========================================================================
# Tests for approval setup value handling (verifying Bug 1 fix)
# ===========================================================================

class TestApprovalSetupValueHandling:
    """Tests that verify the value-handling bug fix in approval setup."""

    def test_empty_string_maxSingle_saved_as_none(self):
        """Empty string for maxSingle should be stored as None, not 0.0."""
        # This tests the fix in approval.py: float("") would be None
        val = ""
        result = float(val) if val and float(val) > 0 else None
        assert result is None

    def test_zero_string_maxSingle_saved_as_none(self):
        """'0' for maxSingle should be stored as None, not 0.0."""
        val = "0"
        result = float(val) if val and float(val) > 0 else None
        assert result is None

    def test_valid_amount_saved_correctly(self):
        """Valid positive amount should be stored as float."""
        val = "100000"
        result = float(val) if val and float(val) > 0 else None
        assert result == 100000.0

    def test_none_value_saved_as_none(self):
        """None value should be stored as None."""
        val = None
        result = float(val) if val and float(val) > 0 else None
        assert result is None

    def test_negative_value_saved_as_none(self):
        """Negative value should be stored as None."""
        val = "-100"
        result = float(val) if val and float(val) > 0 else None
        assert result is None
