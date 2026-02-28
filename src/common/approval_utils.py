"""Shared approval utility functions.

Provides generic approval processing, rejection, and permission calculation
that can be used across all modules (procurement, sales, jute, etc.).

Each module passes in its own get_doc_fn and update_status_fn callables
so the core approval logic remains module-agnostic.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.common.approval_query import (
    get_user_approval_level,
    get_max_approval_level,
    check_approval_mst_exists,
    get_user_edit_access,
)

logger = logging.getLogger(__name__)


def process_approval(
    doc_id: int,
    user_id: int,
    menu_id: int,
    db: Session,
    get_doc_fn,
    update_status_fn,
    id_param_name: str,
    doc_name: str,
    document_amount: float | None = None,
    extra_update_params: dict | None = None,
) -> dict:
    """Generic approval processing for any document type.

    Handles the full approval lifecycle: auto-transition from Open (1) to
    Pending Approval (20), level-based approval checks, optional value-based
    limits, and final approval (status 3) when the last level is reached.

    Args:
        doc_id: The document primary key value.
        user_id: The approving user's ID.
        menu_id: The menu ID for approval lookup.
        db: Database session.
        get_doc_fn: Callable that returns a text() query. The query must
            return columns: status_id, approval_level, branch_id.
        update_status_fn: Callable that returns a text() query for updating
            status_id and approval_level. Must accept bind params:
            {id_param_name}, status_id, approval_level, updated_by,
            updated_date_time.
        id_param_name: The bind parameter name for the document ID
            (e.g., 'indent_id', 'po_id', 'sales_quotation_id').
        doc_name: Human-readable document name for error messages
            (e.g., 'Indent', 'Purchase Order', 'Quotation').
        document_amount: Optional amount for value-based approval checks.
            When None, amount checks are skipped entirely.
        extra_update_params: Optional dict of additional bind parameters
            to include in update_status_fn calls (e.g., {'indent_no': None}).

    Returns:
        Dict with keys: status, new_status_id, new_approval_level, message.
    """
    try:
        merged_extra = extra_update_params or {}

        # 1. Fetch the document
        doc_query = get_doc_fn()
        doc_result = db.execute(doc_query, {id_param_name: doc_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail=f"{doc_name} not found")

        doc = dict(doc_result._mapping)
        current_status_id = doc.get("status_id")
        current_approval_level = doc.get("approval_level") or 0
        branch_id = doc.get("branch_id")

        # 2. Guard: already approved
        if current_status_id == 3:
            raise HTTPException(
                status_code=400,
                detail=f"{doc_name} is already approved."
            )

        # 3. Auto-transition from Open (1) to Pending Approval (20)
        if current_status_id == 1:
            updated_at = datetime.utcnow()
            update_q = update_status_fn()
            params = {
                id_param_name: doc_id,
                "status_id": 20,
                "approval_level": 1,
                "updated_by": user_id,
                "updated_date_time": updated_at,
                **merged_extra,
            }
            db.execute(update_q, params)
            db.commit()
            current_status_id = 20
            current_approval_level = 1
            # Refresh document data after status change
            doc_result = db.execute(doc_query, {id_param_name: doc_id}).fetchone()
            if doc_result:
                doc = dict(doc_result._mapping)

        # 4. Must be in Pending Approval (20) to proceed
        if current_status_id != 20:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot approve {doc_name} with status_id {current_status_id}. "
                    f"Expected 20 (Pending Approval) or 1 (Open)."
                )
            )

        # 5. Check if approval hierarchy exists for this menu/branch
        approval_exists_query = check_approval_mst_exists()
        approval_exists_result = db.execute(
            approval_exists_query,
            {"menu_id": menu_id, "branch_id": branch_id}
        ).fetchone()
        approval_exists = False
        if approval_exists_result:
            approval_exists = (dict(approval_exists_result._mapping).get("count") or 0) > 0

        if approval_exists:
            # 6a. Hierarchy exists — use level-based approval
            user_level_query = get_user_approval_level()
            user_level_result = db.execute(
                user_level_query,
                {"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
            ).fetchone()

            if not user_level_result:
                raise HTTPException(
                    status_code=403,
                    detail="User does not have approval permission for this menu and branch."
                )

            user_data = dict(user_level_result._mapping)
            user_approval_level = user_data.get("approval_level")

            # 7. Level mismatch check
            if user_approval_level != current_approval_level:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"User approval level ({user_approval_level}) does not match "
                        f"current {doc_name} approval level ({current_approval_level})."
                    )
                )

            # 8. Value-based checks (only when document_amount is provided)
            if document_amount is not None:
                max_amount_single = user_data.get("max_amount_single")
                if (
                    max_amount_single is not None
                    and max_amount_single > 0
                    and document_amount > max_amount_single
                ):
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            f"Document amount ({document_amount}) exceeds maximum "
                            f"single approval amount ({max_amount_single})."
                        )
                    )

            # 9. Get max approval level for this menu/branch
            max_level_query = get_max_approval_level()
            max_level_result = db.execute(
                max_level_query,
                {"menu_id": menu_id, "branch_id": branch_id}
            ).fetchone()
            max_approval_level = (
                dict(max_level_result._mapping).get("max_level")
                if max_level_result
                else user_approval_level
            )

            # 10-11. Determine next status
            if user_approval_level >= max_approval_level:
                new_status_id = 3  # Approved (final)
                new_approval_level = user_approval_level
                message = f"{doc_name} approved (final level)."
            else:
                new_status_id = 20  # Still Pending Approval
                new_approval_level = current_approval_level + 1
                message = f"{doc_name} moved to approval level {new_approval_level}."
        else:
            # 6b. No hierarchy — fall back to edit-access check
            if not _user_has_edit_access(user_id, branch_id, menu_id, db):
                raise HTTPException(
                    status_code=403,
                    detail="User does not have approval permission for this menu and branch."
                )
            # Direct approval — no levels to traverse
            new_status_id = 3  # Approved (final)
            new_approval_level = current_approval_level
            message = f"{doc_name} approved (no approval hierarchy configured)."

        # 12. Update document status
        updated_at = datetime.utcnow()
        update_q = update_status_fn()
        params = {
            id_param_name: doc_id,
            "status_id": new_status_id,
            "approval_level": new_approval_level,
            "updated_by": user_id,
            "updated_date_time": updated_at,
            **merged_extra,
        }
        db.execute(update_q, params)

        # 13. Commit
        db.commit()

        # 14. Return result
        return {
            "status": "success",
            "new_status_id": new_status_id,
            "new_approval_level": new_approval_level,
            "message": message,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Error processing approval for {doc_name}")
        raise HTTPException(status_code=500, detail=str(e))


def process_rejection(
    doc_id: int,
    user_id: int,
    menu_id: int | None,
    db: Session,
    get_doc_fn,
    update_status_fn,
    id_param_name: str,
    doc_name: str,
    reason: str | None = None,
    extra_update_params: dict | None = None,
) -> dict:
    """Generic rejection processing for any document type.

    Rejects a document that is currently in Pending Approval (status 20),
    setting its status to Rejected (4) and clearing the approval level.

    Args:
        doc_id: The document primary key value.
        user_id: The rejecting user's ID.
        menu_id: The menu ID for approval lookup. When provided, the
            function verifies the user has approval permission at the
            current level before allowing rejection.
        db: Database session.
        get_doc_fn: Callable that returns a text() query. The query must
            return columns: status_id, approval_level, branch_id.
        update_status_fn: Callable that returns a text() query for updating
            status_id and approval_level.
        id_param_name: The bind parameter name for the document ID.
        doc_name: Human-readable document name for error messages.
        reason: Optional rejection reason (logged but not stored by this
            function — callers may store it separately).
        extra_update_params: Optional dict of additional bind parameters
            to include in update_status_fn calls.

    Returns:
        Dict with keys: status, new_status_id, new_approval_level, message.
    """
    try:
        merged_extra = extra_update_params or {}

        # 1. Fetch the document
        doc_query = get_doc_fn()
        doc_result = db.execute(doc_query, {id_param_name: doc_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail=f"{doc_name} not found")

        doc = dict(doc_result._mapping)
        current_status_id = doc.get("status_id")
        current_approval_level = doc.get("approval_level")
        branch_id = doc.get("branch_id")

        # Must be in Pending Approval (20)
        if current_status_id != 20:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot reject {doc_name} with status_id {current_status_id}. "
                    f"Expected 20 (Pending Approval)."
                )
            )

        # 2. If menu_id provided, verify user has approval permission at current level
        if menu_id is not None:
            # Check if approval hierarchy exists for this menu/branch
            approval_exists_query = check_approval_mst_exists()
            approval_exists_result = db.execute(
                approval_exists_query,
                {"menu_id": menu_id, "branch_id": branch_id}
            ).fetchone()
            approval_exists = False
            if approval_exists_result:
                approval_exists = (dict(approval_exists_result._mapping).get("count") or 0) > 0

            if approval_exists:
                # Hierarchy exists — use level-based check
                user_level_query = get_user_approval_level()
                user_level_result = db.execute(
                    user_level_query,
                    {"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
                ).fetchone()

                if not user_level_result:
                    raise HTTPException(
                        status_code=403,
                        detail="User does not have approval permission for this menu and branch."
                    )

                user_approval_level = dict(user_level_result._mapping).get("approval_level")
                if user_approval_level != current_approval_level:
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            f"User approval level ({user_approval_level}) does not match "
                            f"current {doc_name} approval level ({current_approval_level})."
                        )
                    )
            else:
                # No hierarchy — fall back to edit-access check
                if not _user_has_edit_access(user_id, branch_id, menu_id, db):
                    raise HTTPException(
                        status_code=403,
                        detail="User does not have rejection permission for this menu and branch."
                    )

        # 3. Update status to Rejected (4), clear approval_level
        updated_at = datetime.utcnow()
        update_q = update_status_fn()
        params = {
            id_param_name: doc_id,
            "status_id": 4,  # Rejected
            "approval_level": None,
            "updated_by": user_id,
            "updated_date_time": updated_at,
            **merged_extra,
        }
        db.execute(update_q, params)

        # 4. Commit
        db.commit()

        if reason:
            logger.info(f"{doc_name} {doc_id} rejected by user {user_id}. Reason: {reason}")

        # 5. Return result
        return {
            "status": "success",
            "new_status_id": 4,
            "new_approval_level": None,
            "message": f"{doc_name} has been rejected.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Error processing rejection for {doc_name}")
        raise HTTPException(status_code=500, detail=str(e))


def calculate_approval_permissions(
    user_id: int,
    menu_id: int,
    branch_id: int,
    status_id: int,
    current_approval_level: int | None,
    db: Session,
) -> dict:
    """Calculate approval permissions for a user based on document status and approval configuration.

    Returns a dict of boolean permission flags that the frontend uses to
    show/hide action buttons (Approve, Reject, Open, Cancel Draft, etc.).

    Args:
        user_id: The user ID.
        menu_id: The menu ID.
        branch_id: The branch ID.
        status_id: Current status ID of the document.
        current_approval_level: Current approval level (only relevant when status_id = 20).
        db: Database session.

    Returns:
        Dict with permission flags: canApprove, canReject, canOpen,
        canSendForApproval, canCancelDraft, canReopen, canViewApprovalLog,
        canClone, canSave.
    """
    permissions = {
        "canApprove": False,
        "canReject": False,
        "canOpen": False,
        "canSendForApproval": False,
        "canCancelDraft": False,
        "canReopen": False,
        "canViewApprovalLog": False,
        "canClone": False,
        "canSave": False,
    }

    try:
        # Check if approval_mst has entries for this menu/branch
        approval_exists_query = check_approval_mst_exists()
        approval_exists_result = db.execute(
            approval_exists_query,
            {"menu_id": menu_id, "branch_id": branch_id}
        ).fetchone()
        approval_exists = False
        if approval_exists_result:
            result_dict = dict(approval_exists_result._mapping)
            approval_exists = (result_dict.get("count") or 0) > 0

        # Status-based permissions
        if status_id == 21:  # Drafted
            permissions["canOpen"] = True
            permissions["canCancelDraft"] = True
            permissions["canSave"] = True
        elif status_id == 1:  # Open
            permissions["canSave"] = True
            if approval_exists:
                # Approval hierarchy exists — check if user has approval level 1
                user_level_query = get_user_approval_level()
                user_level_result = db.execute(
                    user_level_query,
                    {"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
                ).fetchone()

                if user_level_result:
                    user_approval_level = dict(user_level_result._mapping).get("approval_level")
                    if user_approval_level == 1:
                        permissions["canApprove"] = True
            else:
                # No approval hierarchy — check if user has edit access
                permissions["canApprove"] = _user_has_edit_access(
                    user_id, branch_id, menu_id, db
                )
        elif status_id == 6:  # Cancelled
            permissions["canReopen"] = True
            permissions["canClone"] = True
            permissions["canViewApprovalLog"] = True
        elif status_id == 4:  # Rejected
            permissions["canReopen"] = True
            permissions["canClone"] = True
            permissions["canViewApprovalLog"] = True
        elif status_id == 3:  # Approved
            permissions["canViewApprovalLog"] = True
            permissions["canClone"] = True
        elif status_id == 5:  # Closed
            permissions["canViewApprovalLog"] = True

        # Approval/Reject permissions (only for status_id = 20)
        if status_id == 20:  # Pending Approval
            permissions["canViewApprovalLog"] = True

            if approval_exists:
                # Approval hierarchy exists — check if user's level matches current level
                if current_approval_level is not None:
                    user_level_query = get_user_approval_level()
                    user_level_result = db.execute(
                        user_level_query,
                        {"menu_id": menu_id, "branch_id": branch_id, "user_id": user_id}
                    ).fetchone()

                    if user_level_result:
                        user_approval_level = dict(user_level_result._mapping).get("approval_level")
                        if user_approval_level == current_approval_level:
                            permissions["canApprove"] = True
                            permissions["canReject"] = True
            else:
                # No approval hierarchy — check if user has edit access
                has_edit = _user_has_edit_access(user_id, branch_id, menu_id, db)
                if has_edit:
                    permissions["canApprove"] = True
                    permissions["canReject"] = True

        return permissions
    except Exception as e:
        logger.exception("Error calculating approval permissions")
        # Return default permissions (all False) on error
        return permissions


def _user_has_edit_access(
    user_id: int,
    branch_id: int,
    menu_id: int,
    db: Session,
) -> bool:
    """Check if user has edit access (access_type_id >= 4) for a menu and branch."""
    edit_access_query = get_user_edit_access()
    edit_access_result = db.execute(
        edit_access_query,
        {"user_id": user_id, "branch_id": branch_id, "menu_id": menu_id}
    ).fetchone()

    if edit_access_result:
        max_access_type = dict(edit_access_result._mapping).get("max_access_type_id")
        if max_access_type is not None and max_access_type >= 4:
            return True
    return False
