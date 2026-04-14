from fastapi import Depends, Request, HTTPException, APIRouter, Query
import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from datetime import datetime
from src.common.utils import now_ist
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.masters.query import get_branch_list, get_item_group_drodown
from src.procurement.indent import (
    calculate_financial_year,
    format_indent_no,
)
from src.procurement.query import (
    get_item_by_group_id_purchaseable,
    get_item_make_by_group_id,
    get_item_uom_by_group_id,
)
from src.sales.quotation import (
    to_int,
    to_float,
    to_positive_float,
    format_date,
    get_fy_boundaries,
)
from src.common.approval_utils import (
    process_approval,
    process_rejection,
    calculate_approval_permissions,
)
from src.sales.query import (
    get_customers_for_sales,
    get_customer_branches_bulk,
    get_brokers_for_sales,
    get_transporters_for_sales,
    get_approved_delivery_orders_query,
    get_delivery_order_lines_for_invoice,
    get_sales_order_lines_for_invoice,
    get_invoice_table_query,
    get_invoice_table_count_query,
    get_invoice_by_id_query,
    get_invoice_dtl_by_id_query,
    insert_sales_invoice,
    insert_invoice_line_item,
    update_sales_invoice,
    delete_invoice_line_items,
    update_invoice_status,
    get_invoice_with_approval_info,
    get_max_invoice_no_for_branch_fy,
    get_mukam_list,
    # GST (separate table)
    insert_sales_invoice_dtl_gst,
    delete_sales_invoice_dtl_gst,
    get_sales_invoice_dtl_gst_by_invoice_id,
    # Jute header (new table)
    insert_sales_invoice_jute,
    delete_sales_invoice_jute,
    get_sales_invoice_jute_by_id,
    # Jute detail (new table)
    insert_sales_invoice_jute_dtl,
    delete_sales_invoice_jute_dtl,
    get_sales_invoice_jute_dtl_by_invoice_id,
    # Govt SKG header
    insert_sales_invoice_govtskg,
    delete_sales_invoice_govtskg,
    get_sales_invoice_govtskg_by_id,
    # Govt SKG detail
    insert_sale_invoice_govtskg_dtl,
    delete_sale_invoice_govtskg_dtl,
    get_sale_invoice_govtskg_dtl_by_invoice_id,
    # Hessian detail
    insert_sales_invoice_hessian_dtl,
    delete_sales_invoice_hessian_dtl,
    get_sales_invoice_hessian_dtl_by_invoice_id,
    # Sales orders for invoice
    get_approved_sales_orders_for_invoice,
    # E-invoice functions
    get_transporter_branches,
    get_e_invoice_submission_history,
    # SO extension data for invoice pre-fill
    get_sales_order_govtskg_by_id,
    get_sales_order_additional_by_id,
)
from src.sales.constants import SALES_DOC_TYPES

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SETUP ENDPOINTS
# =============================================================================


@router.get("/get_sales_invoice_setup_1")
async def get_sales_invoice_setup_1(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Return branches, customers, transporters, approved DOs, and item groups for invoice creation."""
    try:
        q_branch_id = request.query_params.get("branch_id")
        q_co_id = request.query_params.get("co_id")
        branch_id = None
        co_id = None

        if q_branch_id is not None:
            try:
                branch_id = int(q_branch_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid branch_id")
        if q_co_id is not None:
            try:
                co_id = int(q_co_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid co_id")

        if co_id is None:
            raise HTTPException(status_code=400, detail="co_id is required")

        # Branches
        branch_ids_list = [branch_id] if branch_id is not None else None
        branchquery = get_branch_list(branch_ids=branch_ids_list) if branch_ids_list else get_branch_list()
        branch_result = db.execute(branchquery, {"branch_ids": branch_ids_list} if branch_ids_list else {}).fetchall()
        branches = [dict(r._mapping) for r in branch_result]

        # Customers
        customer_query = get_customers_for_sales(co_id=co_id)
        customer_result = db.execute(customer_query, {"co_id": co_id}).fetchall()
        customers = [dict(r._mapping) for r in customer_result]

        # Customer branches in bulk
        cust_branches_query = get_customer_branches_bulk(co_id=co_id)
        cust_branches_result = db.execute(cust_branches_query, {"co_id": co_id}).fetchall()
        branches_by_party: dict[int, list[dict]] = {}
        for row in cust_branches_result:
            bd = dict(row._mapping)
            pid = bd.get("party_id")
            if pid is not None:
                if pid not in branches_by_party:
                    branches_by_party[pid] = []
                branches_by_party[pid].append(bd)
        for cust in customers:
            cust["branches"] = branches_by_party.get(cust.get("party_id"), [])

        # Brokers
        broker_query = get_brokers_for_sales(co_id=co_id)
        broker_result = db.execute(broker_query, {"co_id": co_id}).fetchall()
        brokers = [dict(r._mapping) for r in broker_result]

        # Transporters
        transporter_query = get_transporters_for_sales(co_id=co_id)
        transporter_result = db.execute(transporter_query, {"co_id": co_id}).fetchall()
        transporters = [dict(r._mapping) for r in transporter_result]

        # Approved delivery orders for dropdown (optional reference)
        ado_query = get_approved_delivery_orders_query()
        ado_result = db.execute(ado_query, {"branch_id": branch_id, "co_id": co_id}).fetchall()
        approved_delivery_orders = []
        for row in ado_result:
            mapped = dict(row._mapping)
            raw_no = mapped.get("delivery_order_no")
            formatted_no = ""
            if raw_no is not None:
                try:
                    formatted_no = format_indent_no(
                        indent_no=int(raw_no) if raw_no else None,
                        co_prefix=mapped.get("co_prefix"),
                        branch_prefix=mapped.get("branch_prefix"),
                        indent_date=mapped.get("delivery_order_date"),
                        document_type=SALES_DOC_TYPES.get("DELIVERY_ORDER", "DO"),
                    )
                except Exception:
                    formatted_no = str(raw_no) if raw_no else ""
            approved_delivery_orders.append({
                "sales_delivery_order_id": mapped.get("sales_delivery_order_id"),
                "delivery_order_no": formatted_no,
                "delivery_order_date": format_date(mapped.get("delivery_order_date")),
                "party_id": mapped.get("party_id"),
                "party_name": mapped.get("party_name"),
                "net_amount": mapped.get("net_amount"),
                "sales_order_id": mapped.get("sales_order_id"),
                "sales_order_date": format_date(mapped.get("sales_order_date")),
                "sales_order_no": mapped.get("sales_order_no"),
                "invoice_type": mapped.get("invoice_type"),
                "billing_to_id": mapped.get("billing_to_id"),
                "shipping_to_id": mapped.get("shipping_to_id"),
                "transporter_id": mapped.get("transporter_id"),
            })

        # Item groups (for manual entry without delivery order)
        itemgrp_query = get_item_group_drodown(co_id=co_id)
        itemgrp_result = db.execute(itemgrp_query, {"co_id": co_id}).fetchall()
        item_groups = [dict(r._mapping) for r in itemgrp_result]

        # Invoice types mapped to company
        invoice_types_result = db.execute(
            text("""
                SELECT itm.invoice_type_id, itm.invoice_type_name
                FROM invoice_type_co_map itcm
                JOIN invoice_type_mst itm ON itm.invoice_type_id = itcm.invoice_type_id
                WHERE itcm.co_id = :co_id AND itcm.active = 1
                ORDER BY itm.invoice_type_name
            """),
            {"co_id": co_id},
        ).fetchall()
        invoice_types = [dict(r._mapping) for r in invoice_types_result]

        # Mukam list (for jute invoices)
        mukam_query = get_mukam_list()
        mukam_result = db.execute(mukam_query).fetchall()
        mukam_list = [dict(r._mapping) for r in mukam_result]

        # Approved sales orders for dropdown
        aso_query = get_approved_sales_orders_for_invoice()
        aso_result = db.execute(aso_query, {"branch_id": branch_id, "co_id": co_id}).fetchall()
        approved_sales_orders = []
        for row in aso_result:
            mapped = dict(row._mapping)
            raw_no = mapped.get("sales_no")
            formatted_no = ""
            if raw_no is not None:
                try:
                    formatted_no = format_indent_no(
                        indent_no=int(raw_no) if raw_no else None,
                        co_prefix=mapped.get("co_prefix"),
                        branch_prefix=mapped.get("branch_prefix"),
                        indent_date=mapped.get("sales_order_date"),
                        document_type=SALES_DOC_TYPES.get("SALES_ORDER", "SO"),
                    )
                except Exception:
                    formatted_no = str(raw_no) if raw_no else ""
            approved_sales_orders.append({
                "sales_order_id": mapped.get("sales_order_id"),
                "sales_order_no": formatted_no,
                "sales_order_date": format_date(mapped.get("sales_order_date")),
                "party_id": mapped.get("party_id"),
                "party_name": mapped.get("party_name"),
                "payment_terms": mapped.get("payment_terms"),
                "invoice_type": mapped.get("invoice_type"),
                "broker_id": mapped.get("broker_id"),
                "billing_to_id": mapped.get("billing_to_id"),
                "shipping_to_id": mapped.get("shipping_to_id"),
                "transporter_id": mapped.get("transporter_id"),
                "buyer_order_no": mapped.get("buyer_order_no"),
                "buyer_order_date": format_date(mapped.get("buyer_order_date")),
            })

        # Additional charges master
        from src.sales.query import get_additional_charges_dropdown
        charges_result = db.execute(get_additional_charges_dropdown()).fetchall()
        additional_charges_master = [dict(r._mapping) for r in charges_result]

        # Transport charge rates for Govt Sacking
        from src.sales.query import get_govtskg_transport_charge_rates
        transport_rates_result = db.execute(get_govtskg_transport_charge_rates()).fetchall()
        transport_charge_rates = [dict(r._mapping) for r in transport_rates_result]

        # Company details for invoice header
        co_result = db.execute(
            text("""
                SELECT cm.co_name, cm.co_logo, cm.co_address1, cm.co_address2, cm.co_zipcode,
                       cm.co_cin_no, cm.co_email_id, cm.co_pan_no,
                       cm.state_id, sm.state AS state_name, sm.state_code
                FROM co_mst cm
                LEFT JOIN state_mst sm ON sm.state_id = cm.state_id
                WHERE cm.co_id = :co_id
            """),
            {"co_id": co_id},
        ).fetchone()
        company = dict(co_result._mapping) if co_result else {}

        # Bank details for dropdown
        bank_result = db.execute(
            text("""
                SELECT b.bank_detail_id, b.bank_name, b.bank_branch, b.acc_no, b.ifsc_code
                FROM bank_details_mst b
                WHERE b.co_id = :co_id AND b.active = 1
                ORDER BY b.bank_name
            """),
            {"co_id": co_id},
        ).fetchall()
        bank_details = [dict(r._mapping) for r in bank_result]

        return {
            "branches": branches,
            "customers": customers,
            "brokers": brokers,
            "transporters": transporters,
            "approved_delivery_orders": approved_delivery_orders,
            "item_groups": item_groups,
            "invoice_types": invoice_types,
            "mukam_list": mukam_list,
            "approved_sales_orders": approved_sales_orders,
            "additional_charges_master": additional_charges_master,
            "transport_charge_rates": transport_charge_rates,
            "company": company,
            "bank_details": bank_details,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching sales invoice setup 1")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_sales_invoice_setup_2")
async def get_sales_invoice_setup_2(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Return items, makes, and UOMs by item_group_id."""
    try:
        q_item_group = request.query_params.get("item_group")
        if q_item_group is None:
            raise HTTPException(status_code=400, detail="item_group is required")

        try:
            item_group_id = int(q_item_group)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid item_group")

        items_query = get_item_by_group_id_purchaseable(item_group_id=item_group_id)
        items_result = db.execute(items_query, {"item_group_id": item_group_id}).fetchall()
        items = [dict(r._mapping) for r in items_result]

        makes_query = get_item_make_by_group_id(item_group_id=item_group_id)
        makes_result = db.execute(makes_query, {"item_group_id": item_group_id}).fetchall()
        makes = [dict(r._mapping) for r in makes_result]

        uoms_query = get_item_uom_by_group_id(item_group_id=item_group_id)
        uoms_result = db.execute(uoms_query, {"item_group_id": item_group_id}).fetchall()
        uoms = [dict(r._mapping) for r in uoms_result]

        return {"items": items, "makes": makes, "uoms": uoms}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_delivery_order_lines")
async def get_delivery_order_lines(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Get delivery order line items plus linked SO extension data to pre-fill a new invoice.

    Returns line items and, when a linked sales order exists, also returns
    govtskg header/detail and additional charges from the SO — so the
    frontend receives everything it needs in a single call.
    """
    try:
        q_id = request.query_params.get("sales_delivery_order_id")
        if q_id is None:
            raise HTTPException(status_code=400, detail="sales_delivery_order_id is required")

        sales_delivery_order_id = int(q_id)

        # 1. Line items
        query = get_delivery_order_lines_for_invoice()
        result = db.execute(query, {"sales_delivery_order_id": sales_delivery_order_id}).fetchall()
        data = [dict(r._mapping) for r in result]

        response: dict = {"data": data}

        # 2. Look up linked SO from the DO header
        do_header = db.execute(
            text("SELECT sales_order_id, invoice_type FROM sales_delivery_order WHERE sales_delivery_order_id = :id"),
            {"id": sales_delivery_order_id},
        ).fetchone()

        if do_header:
            do_hdr = dict(do_header._mapping)
            so_id = do_hdr.get("sales_order_id")
            inv_type = do_hdr.get("invoice_type")

            if inv_type is not None:
                response["invoice_type"] = inv_type

            if so_id:
                # 3a. Govtskg header (PCSO, mode of transport, etc.)
                govtskg_row = db.execute(
                    get_sales_order_govtskg_by_id(), {"sales_order_id": so_id}
                ).fetchone()
                if govtskg_row:
                    g = dict(govtskg_row._mapping)
                    response["so_govtskg"] = {
                        "pcso_no": g.get("pcso_no"),
                        "pcso_date": str(g["pcso_date"]) if g.get("pcso_date") else None,
                        "mode_of_transport": g.get("mode_of_transport"),
                        "administrative_office_address": g.get("administrative_office_address"),
                        "destination_rail_head": g.get("destination_rail_head"),
                        "loading_point": g.get("loading_point"),
                    }

                # 3b. SO additional charges (with GST)
                additional_results = db.execute(
                    get_sales_order_additional_by_id(), {"sales_order_id": so_id}
                ).fetchall()
                if additional_results:
                    response["so_additional_charges"] = [dict(r._mapping) for r in additional_results]

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_sales_order_lines")
async def get_sales_order_lines(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Get sales order line items plus SO extension data to pre-fill a new invoice."""
    try:
        q_id = request.query_params.get("sales_order_id")
        if q_id is None:
            raise HTTPException(status_code=400, detail="sales_order_id is required")

        sales_order_id = int(q_id)
        query = get_sales_order_lines_for_invoice()
        result = db.execute(query, {"sales_order_id": sales_order_id}).fetchall()
        data = [dict(r._mapping) for r in result]

        response: dict = {"data": data}

        # SO header — invoice_type (so the frontend can align the invoice type)
        so_header = db.execute(
            text("SELECT invoice_type FROM sales_order WHERE sales_order_id = :id"),
            {"id": sales_order_id},
        ).fetchone()
        if so_header:
            inv_type = dict(so_header._mapping).get("invoice_type")
            if inv_type is not None:
                response["invoice_type"] = inv_type

        # SO extension data — govtskg header
        govtskg_row = db.execute(
            get_sales_order_govtskg_by_id(), {"sales_order_id": sales_order_id}
        ).fetchone()
        if govtskg_row:
            g = dict(govtskg_row._mapping)
            response["so_govtskg"] = {
                "pcso_no": g.get("pcso_no"),
                "pcso_date": str(g["pcso_date"]) if g.get("pcso_date") else None,
                "mode_of_transport": g.get("mode_of_transport"),
                "administrative_office_address": g.get("administrative_office_address"),
                "destination_rail_head": g.get("destination_rail_head"),
                "loading_point": g.get("loading_point"),
            }

        # SO additional charges (with GST)
        additional_results = db.execute(
            get_sales_order_additional_by_id(), {"sales_order_id": sales_order_id}
        ).fetchall()
        if additional_results:
            response["so_additional_charges"] = [dict(r._mapping) for r in additional_results]

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CRUD ENDPOINTS
# =============================================================================


@router.get("/get_sales_invoice_table")
async def get_sales_invoice_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
    co_id: int | None = None,
    branch_id: int | None = None,
):
    """Return paginated sales invoice list."""
    try:
        page = max(page, 1)
        limit = max(min(limit, 100), 1)
        offset = (page - 1) * limit
        search_like = f"%{search.strip()}%" if search else None

        params = {"co_id": co_id, "branch_id": branch_id, "search_like": search_like, "limit": limit, "offset": offset}

        list_query = get_invoice_table_query()
        rows = db.execute(list_query, params).fetchall()
        data = []
        for row in rows:
            mapped = dict(row._mapping)
            raw_no = mapped.get("invoice_no")
            formatted_no = ""
            if raw_no is not None:
                try:
                    formatted_no = format_indent_no(
                        indent_no=int(raw_no) if raw_no else None,
                        co_prefix=mapped.get("co_prefix"),
                        branch_prefix=mapped.get("branch_prefix"),
                        indent_date=mapped.get("invoice_date"),
                        document_type=SALES_DOC_TYPES.get("INVOICE", "SI"),
                    )
                except Exception:
                    formatted_no = str(raw_no) if raw_no else ""

            data.append({
                "invoice_id": mapped.get("invoice_id"),
                "invoice_no": formatted_no,
                "invoice_date": format_date(mapped.get("invoice_date")),
                "branch_id": mapped.get("branch_id"),
                "branch_name": mapped.get("branch_name"),
                "party_name": mapped.get("party_name"),
                "sales_delivery_order_id": mapped.get("sales_delivery_order_id"),
                "invoice_amount": mapped.get("invoice_amount"),
                "status": mapped.get("status_name"),
                "status_id": mapped.get("status_id"),
            })

        count_query = get_invoice_table_count_query()
        count_result = db.execute(count_query, {"co_id": co_id, "branch_id": branch_id, "search_like": search_like}).scalar()
        total = int(count_result) if count_result is not None else 0

        return {"data": data, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching sales invoice table")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_transporter_branches")
async def get_transporter_branches_endpoint(
    request: Request,
    transporter_id: int = Query(..., description="Transporter party ID"),
    co_id: int = Query(..., description="Company ID"),
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Fetch all branches for a transporter party.
    Used to populate transporter branch dropdown and retrieve GST number.
    """
    try:
        if not transporter_id or not co_id:
            raise HTTPException(status_code=400, detail="transporter_id and co_id are required")

        query = get_transporter_branches(int(transporter_id))
        result = db.execute(query, {"transporter_id": int(transporter_id)}).fetchall()

        branches = [dict(r._mapping) for r in result]

        return {"data": branches}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching transporter branches")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_sales_invoice_by_id")
async def get_sales_invoice_by_id(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Return invoice details by ID with line items."""
    try:
        q_id = request.query_params.get("invoice_id")
        q_co_id = request.query_params.get("co_id")
        if q_id is None:
            raise HTTPException(status_code=400, detail="invoice_id is required")
        if q_co_id is None:
            raise HTTPException(status_code=400, detail="co_id is required")

        try:
            invoice_id = int(q_id)
            co_id = int(q_co_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid invoice_id or co_id")

        # Header
        header_query = get_invoice_by_id_query()
        header_result = db.execute(header_query, {"invoice_id": invoice_id, "co_id": co_id}).fetchone()
        if not header_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found or access denied")
        header = dict(header_result._mapping)

        # Details
        detail_query = get_invoice_dtl_by_id_query()
        detail_results = db.execute(detail_query, {"invoice_id": invoice_id}).fetchall()
        details = [dict(r._mapping) for r in detail_results]

        # Format invoice number
        raw_no = header.get("invoice_no")
        formatted_no = ""
        if raw_no is not None:
            try:
                formatted_no = format_indent_no(
                    indent_no=int(raw_no) if raw_no else None,
                    co_prefix=header.get("co_prefix"),
                    branch_prefix=header.get("branch_prefix"),
                    indent_date=header.get("invoice_date"),
                    document_type=SALES_DOC_TYPES.get("INVOICE", "SI"),
                )
            except Exception:
                formatted_no = str(raw_no) if raw_no else ""

        status_id = header.get("status_id")
        branch_id = header.get("branch_id")

        # Permissions
        q_menu_id = request.query_params.get("menu_id")
        permissions = None
        if q_menu_id is not None and branch_id is not None and status_id is not None:
            try:
                permissions = calculate_approval_permissions(
                    user_id=int(token_data.get("user_id")),
                    menu_id=int(q_menu_id),
                    branch_id=branch_id,
                    status_id=status_id,
                    current_approval_level=None,
                    db=db,
                )
            except Exception:
                logger.exception("Error calculating permissions")

        response = {
            "id": str(header.get("invoice_id", "")),
            "invoiceNo": formatted_no,
            "invoiceDate": format_date(header.get("invoice_date")),
            "challanNo": header.get("challan_no"),
            "challanDate": format_date(header.get("challan_date")),
            "branchId": str(header.get("branch_id", "")) if header.get("branch_id") else "",
            "salesDeliveryOrderId": header.get("sales_delivery_order_id"),
            "brokerId": header.get("broker_id"),
            "billingTo": header.get("billing_to_id"),
            "billingAddress": header.get("billing_address"),
            "billingGstNo": header.get("billing_gst_no"),
            "billingStateId": header.get("billing_state_id"),
            "billingStateName": header.get("billing_state_name"),
            "billingContactPerson": header.get("billing_contact_person"),
            "billingContactNo": header.get("billing_contact_no"),
            "shippingTo": header.get("shipping_to_id"),
            "shippingAddress": header.get("shipping_address"),
            "shippingGstNo": header.get("shipping_gst_no"),
            "shippingStateId": header.get("shipping_state_id"),
            "shippingStateName": header.get("shipping_state_name"),
            "shippingContactPerson": header.get("shipping_contact_person"),
            "shippingContactNo": header.get("shipping_contact_no"),
            "party": str(header.get("party_id", "")) if header.get("party_id") else "",
            "partyName": header.get("party_name"),
            "shippingStateCode": header.get("shipping_state_code"),
            "transporter": str(header.get("transporter_id", "")) if header.get("transporter_id") else None,
            "transporterName": header.get("transporter_name"),
            "transporterNameStored": header.get("transporter_name_stored"),
            "transporterAddress": header.get("transporter_address"),
            "transporterStateCode": header.get("transporter_state_code"),
            "transporterStateName": header.get("transporter_state_name"),
            "transporterBranchId": header.get("transporter_branch_id"),
            "transporterGstNo": header.get("transporter_gst_no"),
            "transporterDocNo": header.get("transporter_doc_no"),
            "transporterDocDate": format_date(header.get("transporter_doc_date")),
            "buyerOrderNo": header.get("buyer_order_no"),
            "buyerOrderDate": format_date(header.get("buyer_order_date")),
            "irn": header.get("irn"),
            "ackNo": header.get("ack_no"),
            "ackDate": format_date(header.get("ack_date")),
            "qrCode": header.get("qr_code"),
            "vehicleNo": header.get("vehicle_no"),
            "ewayBillNo": header.get("eway_bill_no"),
            "ewayBillDate": format_date(header.get("eway_bill_date")),
            "invoiceType": header.get("invoice_type"),
            "footerNote": header.get("footer_notes"),
            "internalNote": header.get("internal_note"),
            "termsConditions": header.get("terms_conditions"),
            "grossAmount": header.get("invoice_amount"),
            "taxAmount": header.get("tax_amount"),
            "taxPayable": header.get("tax_payable"),
            "freightCharges": header.get("freight_charges"),
            "roundOff": header.get("round_off"),
            "intraInterState": header.get("intra_inter_state"),
            "dueDate": format_date(header.get("due_date")),
            "typeOfSale": header.get("type_of_sale"),
            "taxId": header.get("tax_id"),
            "containerNo": header.get("container_no"),
            "contractNo": header.get("contract_no"),
            "contractDate": format_date(header.get("contract_date")),
            "consignmentNo": header.get("consignment_no"),
            "consignmentDate": format_date(header.get("consignment_date")),
            "paymentTerms": header.get("payment_terms"),
            "salesOrderId": header.get("sales_order_id"),
            "salesOrderDate": format_date(header.get("sales_order_date")),
            "salesOrderNo": header.get("sales_order_no"),
            "billingStateCode": header.get("billing_state_code"),
            "bankDetailId": header.get("bank_detail_id"),
            "bankName": header.get("bank_name"),
            "bankAccNo": header.get("bank_acc_no"),
            "bankIfscCode": header.get("bank_ifsc_code"),
            "bankBranchName": header.get("bank_branch_name"),
            "companyName": header.get("co_name"),
            "companyLogo": header.get("co_logo"),
            "companyAddress1": header.get("co_address1"),
            "companyAddress2": header.get("co_address2"),
            "companyZipcode": header.get("co_zipcode"),
            "companyCinNo": header.get("co_cin_no"),
            "companyPanNo": header.get("co_pan_no"),
            "companyStateName": header.get("co_state_name"),
            "companyStateCode": header.get("co_state_code"),
            "branchAddress1": header.get("branch_address1"),
            "branchAddress2": header.get("branch_address2"),
            "branchZipcode": header.get("branch_zipcode"),
            "branchGstNo": header.get("branch_gst_no"),
            "branchStateName": header.get("branch_state_name"),
            "branchStateCode": header.get("branch_state_code"),
            "status": header.get("status_name"),
            "statusId": status_id,
            "updatedBy": str(header.get("updated_by", "")) if header.get("updated_by") else None,
            "updatedAt": str(header.get("updated_date_time")) if header.get("updated_date_time") else None,
            "lines": [],
        }

        if permissions is not None:
            response["permissions"] = permissions

        # Fetch GST data from separate table and build lookup map
        gst_results = db.execute(
            get_sales_invoice_dtl_gst_by_invoice_id(), {"invoice_id": invoice_id}
        ).fetchall()
        gst_map = {}
        for g in gst_results:
            gd = dict(g._mapping)
            gst_map[gd["invoice_line_item_id"]] = gd

        # Fetch jute header data from new table
        try:
            jute_result = db.execute(
                get_sales_invoice_jute_by_id(), {"invoice_id": invoice_id}
            ).fetchone()
            if jute_result:
                jute = dict(jute_result._mapping)
                response["jute"] = {
                    "mrNo": jute.get("mr_no"),
                    "mrId": jute.get("mr_id"),
                    "claimAmount": float(jute["claim_amount"]) if jute.get("claim_amount") is not None else None,
                    "otherReference": jute.get("other_reference"),
                    "unitConversion": jute.get("unit_conversion"),
                    "claimDescription": jute.get("claim_description"),
                    "mukamId": jute.get("mukam_id"),
                    "mukamName": jute.get("mukam_name"),
                }
        except Exception:
            pass

        # Fetch jute detail data from new table and build lookup map
        jute_dtl_map = {}
        try:
            jute_dtl_results = db.execute(
                get_sales_invoice_jute_dtl_by_invoice_id(), {"invoice_id": invoice_id}
            ).fetchall()
            for jd in jute_dtl_results:
                jdd = dict(jd._mapping)
                jute_dtl_map[jdd["invoice_line_item_id"]] = jdd
        except Exception:
            pass

        # Fetch govt SKG header data
        try:
            govtskg_result = db.execute(
                get_sales_invoice_govtskg_by_id(), {"invoice_id": invoice_id}
            ).fetchone()
            if govtskg_result:
                govtskg = dict(govtskg_result._mapping)
                response["govtskg"] = {
                    "pcsoNo": govtskg.get("pcso_no"),
                    "pcsoDate": str(govtskg["pcso_date"]) if govtskg.get("pcso_date") else None,
                    "administrativeOfficeAddress": govtskg.get("administrative_office_address"),
                    "destinationRailHead": govtskg.get("destination_rail_head"),
                    "loadingPoint": govtskg.get("loading_point"),
                    "modeOfTransport": govtskg.get("mode_of_transport"),
                    "packSheet": float(govtskg["pack_sheet"]) if govtskg.get("pack_sheet") is not None else None,
                    "netWeight": float(govtskg["net_weight"]) if govtskg.get("net_weight") is not None else None,
                    "totalWeight": float(govtskg["total_weight"]) if govtskg.get("total_weight") is not None else None,
                }
        except Exception:
            pass

        # Fetch hessian detail data and build lookup map
        hessian_dtl_map = {}
        try:
            hessian_dtl_results = db.execute(
                get_sales_invoice_hessian_dtl_by_invoice_id(), {"invoice_id": invoice_id}
            ).fetchall()
            for hd in hessian_dtl_results:
                hdd = dict(hd._mapping)
                hessian_dtl_map[hdd["invoice_line_item_id"]] = hdd
        except Exception:
            pass

        # Fetch govt sacking detail data and build lookup map
        govtskg_dtl_map = {}
        try:
            govtskg_dtl_results = db.execute(
                get_sale_invoice_govtskg_dtl_by_invoice_id(), {"invoice_id": invoice_id}
            ).fetchall()
            for gd in govtskg_dtl_results:
                gdd = dict(gd._mapping)
                govtskg_dtl_map[gdd["invoice_line_item_id"]] = gdd
        except Exception:
            pass

        # Load additional charges
        try:
            from src.sales.query import get_sales_invoice_additional_by_id
            additional_results = db.execute(get_sales_invoice_additional_by_id(), {"invoice_id": invoice_id}).fetchall()
            response["additionalCharges"] = [dict(r._mapping) for r in additional_results]
        except Exception:
            response["additionalCharges"] = []

        for detail in details:
            lineitem_id = detail.get("invoice_line_item_id")
            gst_data = gst_map.get(lineitem_id)
            jute_dtl_data = jute_dtl_map.get(lineitem_id)
            hessian_dtl_data = hessian_dtl_map.get(lineitem_id)
            govtskg_dtl_data = govtskg_dtl_map.get(lineitem_id)

            line = {
                "id": str(lineitem_id) if lineitem_id else "",
                "hsnCode": detail.get("hsn_code"),
                "itemGroup": str(detail.get("item_grp_id", "")) if detail.get("item_grp_id") else "",
                "item": str(detail.get("item_id", "")) if detail.get("item_id") else "",
                "itemName": detail.get("item_name"),
                "fullItemCode": detail.get("full_item_code") or detail.get("item_code") or "",
                "itemMake": str(detail.get("item_make_id", "")) if detail.get("item_make_id") else None,
                "quantity": float(detail.get("quantity", 0)) if detail.get("quantity") is not None else 0,
                "uom": str(detail.get("uom_id", "")) if detail.get("uom_id") else "",
                "uomName": detail.get("uom_name"),
                "rate": detail.get("rate"),
                "discountType": detail.get("discount_type"),
                "discountedRate": detail.get("discounted_rate"),
                "discountAmount": detail.get("discount_amount"),
                "netAmount": detail.get("amount_without_tax"),
                "totalAmount": detail.get("total_amount"),
                "salesWeight": detail.get("sales_weight"),
                "remarks": detail.get("remarks"),
                "deliveryOrderDtlId": detail.get("delivery_order_dtl_id"),
                "salesOrderDtlId": detail.get("sales_order_dtl_id"),
            }

            # GST from separate table
            if gst_data:
                line["gst"] = {
                    "taxPercentage": gst_data.get("tax_percentage"),
                    "igstAmount": gst_data.get("igst_amount"),
                    "igstPercent": gst_data.get("igst_percentage"),
                    "cgstAmount": gst_data.get("cgst_amount"),
                    "cgstPercent": gst_data.get("cgst_percentage"),
                    "sgstAmount": gst_data.get("sgst_amount"),
                    "sgstPercent": gst_data.get("sgst_percentage"),
                    "taxAmount": gst_data.get("tax_amount"),
                }
            else:
                line["gst"] = None

            # Jute detail from separate table
            if jute_dtl_data:
                line["juteDtl"] = {
                    "claimAmountDtl": jute_dtl_data.get("claim_amount_dtl"),
                    "claimDesc": jute_dtl_data.get("claim_desc"),
                    "claimRate": jute_dtl_data.get("claim_rate"),
                    "unitConversion": jute_dtl_data.get("unit_conversion"),
                    "qtyUnitConversion": jute_dtl_data.get("qty_untit_conversion"),
                }
            else:
                line["juteDtl"] = None

            # Hessian detail from separate table
            if hessian_dtl_data:
                line["hessianDtl"] = {
                    "qtyBales": hessian_dtl_data.get("qty_bales"),
                    "ratePerBale": hessian_dtl_data.get("rate_per_bale"),
                    "billingRateMt": hessian_dtl_data.get("billing_rate_mt"),
                    "billingRateBale": hessian_dtl_data.get("billing_rate_bale"),
                }
            else:
                line["hessianDtl"] = None

            # Govt sacking detail from separate table
            if govtskg_dtl_data:
                line["govtskgDtl"] = {
                    "packSheet": govtskg_dtl_data.get("pack_sheet"),
                    "netWeight": govtskg_dtl_data.get("net_weight"),
                    "totalWeight": govtskg_dtl_data.get("total_weight"),
                }
            else:
                line["govtskgDtl"] = None

            response["lines"].append(line)

        # Get e-invoice submission history if any
        try:
            history_query = get_e_invoice_submission_history(int(invoice_id))
            history_result = db.execute(history_query, {"invoice_id": int(invoice_id)}).fetchall()
            response["e_invoice_submission_history"] = [dict(r._mapping) for r in history_result]
        except Exception:
            response["e_invoice_submission_history"] = []

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching sales invoice by ID")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create_sales_invoice")
async def create_sales_invoice(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Create a sales invoice with line items. Delivery order reference is optional."""
    try:
        branch_id = to_int(payload.get("branch"), "branch", required=True)
        party_id = to_int(payload.get("party"), "party", required=True)

        date_str = payload.get("date")
        if not date_str:
            raise HTTPException(status_code=400, detail="date is required")
        try:
            invoice_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            raise HTTPException(status_code=400, detail="At least one item row is required")

        user_id = to_int(token_data.get("user_id"), "user_id")

        # Optional fields
        transporter_id = to_int(payload.get("transporter"), "transporter")
        sales_delivery_order_id = to_int(payload.get("sales_delivery_order_id"), "sales_delivery_order_id")
        broker_id = to_int(payload.get("broker_id") or payload.get("broker"), "broker_id")
        billing_to_id = to_int(payload.get("billing_to"), "billing_to")
        shipping_to_id = to_int(payload.get("shipping_to"), "shipping_to")

        gross_amount = to_float(payload.get("gross_amount"), "gross_amount")
        freight_charges = to_float(payload.get("freight_charges"), "freight_charges")
        round_off = to_float(payload.get("round_off"), "round_off")
        tax_amount = to_float(payload.get("tax_amount"), "tax_amount")
        tax_payable = to_float(payload.get("tax_payable"), "tax_payable")

        challan_date = None
        if payload.get("challan_date"):
            try:
                challan_date = datetime.strptime(str(payload["challan_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        eway_bill_date = None
        if payload.get("eway_bill_date"):
            try:
                eway_bill_date = datetime.strptime(str(payload["eway_bill_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        due_date = None
        if payload.get("due_date"):
            try:
                due_date = datetime.strptime(str(payload["due_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        contract_date = None
        if payload.get("contract_date"):
            try:
                contract_date = datetime.strptime(str(payload["contract_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        consignment_date = None
        if payload.get("consignment_date"):
            try:
                consignment_date = datetime.strptime(str(payload["consignment_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        # Extract 9 new fields for e-invoice
        transporter_branch_id = to_int(payload.get("transporter_branch_id"), "transporter_branch_id")
        transporter_doc_no = payload.get("transporter_doc_no")
        transporter_doc_date = None
        if payload.get("transporter_doc_date"):
            try:
                transporter_doc_date = datetime.strptime(str(payload["transporter_doc_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass
        buyer_order_no = payload.get("buyer_order_no")
        buyer_order_date = None
        if payload.get("buyer_order_date"):
            try:
                buyer_order_date = datetime.strptime(str(payload["buyer_order_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass
        irn = payload.get("irn")
        ack_no = payload.get("ack_no")
        ack_date = None
        if payload.get("ack_date"):
            try:
                ack_date = datetime.strptime(str(payload["ack_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass
        qr_code = payload.get("qr_code")

        # Look up co_id from branch
        branch_row = db.execute(
            text("SELECT co_id FROM branch_mst WHERE branch_id = :branch_id"),
            {"branch_id": branch_id},
        ).fetchone()
        co_id = dict(branch_row._mapping).get("co_id") if branch_row else None

        # Normalize items — sales_invoice_dtl uses int columns for item_id, item_make_id, uom_id
        normalized_items = []
        for idx, item in enumerate(raw_items, start=1):
            item_val = item.get("item")
            if not item_val:
                raise HTTPException(status_code=400, detail=f"items[{idx}].item is required")
            uom_val = item.get("uom")
            if not uom_val:
                raise HTTPException(status_code=400, detail=f"items[{idx}].uom is required")

            qty = to_positive_float(item.get("quantity"), f"items[{idx}].quantity")
            rate = to_float(item.get("rate"), f"items[{idx}].rate")

            # Calculate line amounts
            amount_without_tax = to_float(item.get("net_amount"), f"items[{idx}].net_amount")
            if amount_without_tax is None and qty and rate:
                amount_without_tax = round(qty * rate, 2)

            gst = item.get("gst") or {}
            cgst_amt = to_float(gst.get("cgst_amount"), "cgst_amount")
            sgst_amt = to_float(gst.get("sgst_amount"), "sgst_amount")
            igst_amt = to_float(gst.get("igst_amount"), "igst_amount")

            line_total_amount = to_float(item.get("total_amount"), f"items[{idx}].total_amount")
            if line_total_amount is None and amount_without_tax is not None:
                line_tax = (cgst_amt or 0) + (sgst_amt or 0) + (igst_amt or 0)
                line_total_amount = round((amount_without_tax or 0) + line_tax, 2)

            normalized_items.append({
                "hsn_code": item.get("hsn_code"),
                "item_id": to_int(item_val, f"items[{idx}].item"),
                "item_make_id": to_int(item.get("item_make"), f"items[{idx}].item_make"),
                "quantity": qty,
                "uom_id": to_int(uom_val, f"items[{idx}].uom"),
                "rate": rate,
                "discount_type": to_int(item.get("discount_type"), f"items[{idx}].discount_type"),
                "discounted_rate": to_float(item.get("discounted_rate"), f"items[{idx}].discounted_rate"),
                "discount_amount": to_float(item.get("discount_amount"), f"items[{idx}].discount_amount"),
                "amount_without_tax": amount_without_tax,
                "total_amount": line_total_amount,
                "sales_weight": to_float(item.get("sales_weight"), f"items[{idx}].sales_weight"),
                "gst": gst if gst else None,
                "jute_dtl": item.get("jute_dtl") or None,
                "remarks": item.get("remarks"),
                "delivery_order_dtl_id": to_int(item.get("delivery_order_dtl_id"), f"items[{idx}].delivery_order_dtl_id"),
                "sales_order_dtl_id": to_int(item.get("sales_order_dtl_id"), f"items[{idx}].sales_order_dtl_id"),
            })

        invoice_type = to_int(payload.get("invoice_type"), "invoice_type")
        jute_data = payload.get("jute") or {}
        govtskg_data = payload.get("govtskg") or {}

        # Compute claim_amount as sum of line item claim_amount_dtl values
        claim_amount_from_lines = sum(
            to_float((item.get("jute_dtl") or {}).get("claim_amount_dtl"), "claim_amount_dtl") or 0
            for item in normalized_items
            if item.get("jute_dtl")
        )
        if claim_amount_from_lines:
            claim_amount = round(claim_amount_from_lines, 2)
        else:
            claim_amount = to_float(jute_data.get("claim_amount"), "claim_amount")

        # For jute invoices, invoice_amount = gross_amount - claim_amount
        effective_amount = gross_amount or 0
        if invoice_type and jute_data and claim_amount:
            effective_amount = round((gross_amount or 0) - claim_amount, 2)

        # Insert header
        insert_hdr = insert_sales_invoice()
        header_params = {
            "invoice_date": invoice_date,
            "invoice_no": None,
            "branch_id": branch_id,
            "party_id": party_id,
            "sales_delivery_order_id": sales_delivery_order_id,
            "broker_id": broker_id,
            "billing_to_id": billing_to_id,
            "shipping_to_id": shipping_to_id,
            "challan_no": payload.get("challan_no"),
            "challan_date": challan_date,
            "transporter_id": transporter_id,
            "vehicle_no": payload.get("vehicle_no"),
            "transporter_name": payload.get("transporter_name"),
            "transporter_address": payload.get("transporter_address"),
            "transporter_state_code": payload.get("transporter_state_code"),
            "transporter_state_name": payload.get("transporter_state_name"),
            "eway_bill_no": payload.get("eway_bill_no"),
            "eway_bill_date": eway_bill_date,
            "invoice_type": invoice_type,
            "footer_notes": payload.get("footer_note"),
            "internal_note": payload.get("internal_note"),
            "terms": payload.get("terms"),
            "terms_conditions": payload.get("terms_conditions"),
            "invoice_amount": gross_amount or 0,
            "tax_amount": tax_amount or 0,
            "tax_payable": tax_payable,
            "freight_charges": freight_charges or 0,
            "round_off": round_off or 0,
            "shipping_state_code": to_int(payload.get("shipping_state_code"), "shipping_state_code"),
            "intra_inter_state": payload.get("intra_inter_state"),
            "due_date": due_date,
            "type_of_sale": payload.get("type_of_sale"),
            "tax_id": to_int(payload.get("tax_id"), "tax_id"),
            "container_no": payload.get("container_no"),
            "contract_no": to_int(payload.get("contract_no"), "contract_no"),
            "contract_date": contract_date,
            "consignment_no": payload.get("consignment_no"),
            "consignment_date": consignment_date,
            "payment_terms": to_int(payload.get("payment_terms"), "payment_terms"),
            "sales_order_id": to_int(payload.get("sales_order_id"), "sales_order_id"),
            "billing_state_code": to_int(payload.get("billing_state_code"), "billing_state_code"),
            "bank_detail_id": to_int(payload.get("bank_detail_id"), "bank_detail_id"),
            "transporter_branch_id": transporter_branch_id,
            "transporter_doc_no": transporter_doc_no,
            "transporter_doc_date": transporter_doc_date,
            "buyer_order_no": buyer_order_no,
            "buyer_order_date": buyer_order_date,
            "irn": irn,
            "ack_no": ack_no,
            "ack_date": ack_date,
            "qr_code": qr_code,
            "status_id": 21,
            "active": 1,
            "updated_by": user_id,
        }

        result = db.execute(insert_hdr, header_params)
        invoice_id = result.lastrowid
        if not invoice_id:
            raise HTTPException(status_code=500, detail="Failed to create sales invoice header")

        # Insert line items + GST + type-specific detail
        line_query = insert_invoice_line_item()
        gst_query = insert_sales_invoice_dtl_gst()
        jute_dtl_query = insert_sales_invoice_jute_dtl()
        hessian_dtl_query = insert_sales_invoice_hessian_dtl()
        govtskg_dtl_query = insert_sale_invoice_govtskg_dtl()
        for item in normalized_items:
            dtl_result = db.execute(line_query, {
                "invoice_id": invoice_id,
                "hsn_code": item["hsn_code"],
                "item_id": item["item_id"],
                "item_make_id": item["item_make_id"],
                "quantity": item["quantity"] or 0,
                "uom_id": item["uom_id"],
                "rate": item["rate"] or 0,
                "discount_type": item["discount_type"],
                "discounted_rate": item["discounted_rate"],
                "discount_amount": item["discount_amount"],
                "amount_without_tax": item["amount_without_tax"] or 0,
                "total_amount": item["total_amount"] or 0,
                "sales_weight": item["sales_weight"],
                "remarks": item["remarks"],
                "delivery_order_dtl_id": item["delivery_order_dtl_id"],
                "sales_order_dtl_id": item["sales_order_dtl_id"],
            })
            lineitem_id = dtl_result.lastrowid

            # Insert GST into separate table
            gst_data = item.get("gst")
            if gst_data and isinstance(gst_data, dict) and lineitem_id:
                db.execute(gst_query, {
                    "invoice_line_item_id": lineitem_id,
                    "tax_percentage": to_float(gst_data.get("tax_percentage"), "tax_percentage"),
                    "cgst_amount": to_float(gst_data.get("cgst_amount"), "cgst_amount") or 0,
                    "cgst_percentage": to_float(gst_data.get("cgst_percent"), "cgst_percent") or 0,
                    "sgst_amount": to_float(gst_data.get("sgst_amount"), "sgst_amount") or 0,
                    "sgst_percentage": to_float(gst_data.get("sgst_percent"), "sgst_percent") or 0,
                    "igst_amount": to_float(gst_data.get("igst_amount"), "igst_amount") or 0,
                    "igst_percentage": to_float(gst_data.get("igst_percent"), "igst_percent") or 0,
                    "tax_amount": to_float(gst_data.get("tax_amount"), "gst_tax_amount") or 0,
                })

            # Insert jute detail into separate table
            jute_dtl_data = item.get("jute_dtl")
            if jute_dtl_data and isinstance(jute_dtl_data, dict) and lineitem_id:
                db.execute(jute_dtl_query, {
                    "invoice_line_item_id": lineitem_id,
                    "claim_amount_dtl": to_float(jute_dtl_data.get("claim_amount_dtl"), "claim_amount_dtl"),
                    "claim_desc": jute_dtl_data.get("claim_desc"),
                    "claim_rate": to_float(jute_dtl_data.get("claim_rate"), "claim_rate"),
                    "unit_conversion": jute_dtl_data.get("unit_conversion"),
                    "qty_untit_conversion": to_int(jute_dtl_data.get("qty_untit_conversion"), "qty_untit_conversion"),
                })

            # Insert hessian detail into separate table
            hessian_dtl_data = item.get("hessian_dtl")
            if hessian_dtl_data and isinstance(hessian_dtl_data, dict) and lineitem_id:
                db.execute(hessian_dtl_query, {
                    "invoice_line_item_id": lineitem_id,
                    "qty_bales": to_float(hessian_dtl_data.get("qty_bales"), "qty_bales"),
                    "rate_per_bale": to_float(hessian_dtl_data.get("rate_per_bale"), "rate_per_bale"),
                    "billing_rate_mt": to_float(hessian_dtl_data.get("billing_rate_mt"), "billing_rate_mt"),
                    "billing_rate_bale": to_float(hessian_dtl_data.get("billing_rate_bale"), "billing_rate_bale"),
                    "updated_by": user_id,
                })

            # Insert govt sacking detail into separate table
            govtskg_dtl_data = item.get("govtskg_dtl")
            if govtskg_dtl_data and isinstance(govtskg_dtl_data, dict) and lineitem_id:
                db.execute(govtskg_dtl_query, {
                    "invoice_line_item_id": lineitem_id,
                    "pack_sheet": to_float(govtskg_dtl_data.get("pack_sheet"), "pack_sheet"),
                    "net_weight": to_float(govtskg_dtl_data.get("net_weight"), "net_weight"),
                    "total_weight": to_float(govtskg_dtl_data.get("total_weight"), "total_weight"),
                    "updated_by": user_id,
                })

        # Insert jute header data if provided
        if jute_data:
            db.execute(insert_sales_invoice_jute(), {
                "invoice_id": invoice_id,
                "mr_no": jute_data.get("mr_no"),
                "mr_id": to_int(jute_data.get("mr_id"), "mr_id"),
                "claim_amount": claim_amount,
                "other_reference": jute_data.get("other_reference"),
                "unit_conversion": jute_data.get("unit_conversion"),
                "claim_description": jute_data.get("claim_description"),
                "mukam_id": to_int(jute_data.get("mukam_id"), "mukam_id"),
            })

        # Insert govt SKG header data if provided
        if govtskg_data:
            db.execute(insert_sales_invoice_govtskg(), {
                "invoice_id": invoice_id,
                "pcso_no": govtskg_data.get("pcso_no"),
                "pcso_date": format_date(govtskg_data.get("pcso_date")),
                "administrative_office_address": govtskg_data.get("administrative_office_address"),
                "destination_rail_head": govtskg_data.get("destination_rail_head"),
                "loading_point": govtskg_data.get("loading_point"),
                "mode_of_transport": govtskg_data.get("mode_of_transport"),
                "pack_sheet": to_float(govtskg_data.get("pack_sheet"), "pack_sheet"),
                "net_weight": to_float(govtskg_data.get("net_weight"), "net_weight"),
                "total_weight": to_float(govtskg_data.get("total_weight"), "total_weight"),
            })

        # Insert additional charges
        additional_charges_list = payload.get("additional_charges") or []
        if additional_charges_list:
            from src.sales.query import insert_sales_invoice_additional, insert_sales_invoice_additional_gst
            add_query = insert_sales_invoice_additional()
            add_gst_query = insert_sales_invoice_additional_gst()
            for charge in additional_charges_list:
                charge_result = db.execute(add_query, {
                    "invoice_id": invoice_id,
                    "additional_charges_id": to_int(charge.get("additional_charges_id"), "additional_charges_id"),
                    "qty": to_float(charge.get("qty"), "qty"),
                    "rate": to_float(charge.get("rate"), "rate"),
                    "net_amount": to_float(charge.get("net_amount"), "net_amount"),
                    "remarks": charge.get("remarks"),
                    "updated_by": user_id,
                    "updated_date_time": created_at,
                })
                charge_id = charge_result.lastrowid
                gst_data = charge.get("gst")
                if gst_data and isinstance(gst_data, dict) and charge_id:
                    db.execute(add_gst_query, {
                        "sales_invoice_additional_id": charge_id,
                        "igst_amount": to_float(gst_data.get("igst_amount"), "igst_amount"),
                        "igst_percent": to_float(gst_data.get("igst_percent"), "igst_percent"),
                        "cgst_amount": to_float(gst_data.get("cgst_amount"), "cgst_amount"),
                        "cgst_percent": to_float(gst_data.get("cgst_percent"), "cgst_percent"),
                        "sgst_amount": to_float(gst_data.get("sgst_amount"), "sgst_amount"),
                        "sgst_percent": to_float(gst_data.get("sgst_percent"), "sgst_percent"),
                        "gst_total": to_float(gst_data.get("gst_total"), "gst_total"),
                    })

        db.commit()
        return {"message": "Sales invoice created successfully", "invoice_id": invoice_id}
    except HTTPException as exc:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error creating sales invoice")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_sales_invoice")
async def update_sales_invoice_endpoint(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Update a sales invoice with line items (delete-reinsert pattern)."""
    try:
        invoice_id = to_int(payload.get("id"), "id", required=True)
        branch_id = to_int(payload.get("branch"), "branch", required=True)
        party_id = to_int(payload.get("party"), "party", required=True)

        date_str = payload.get("date")
        if not date_str:
            raise HTTPException(status_code=400, detail="date is required")
        try:
            invoice_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            raise HTTPException(status_code=400, detail="At least one item row is required")

        # Verify exists
        check_query = text("SELECT invoice_id, status_id, active FROM sales_invoice WHERE invoice_id = :id AND (active = 1 OR active IS NULL)")
        check_result = db.execute(check_query, {"id": invoice_id}).fetchone()
        if not check_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found or inactive")

        user_id = to_int(token_data.get("user_id"), "user_id")

        transporter_id = to_int(payload.get("transporter"), "transporter")
        sales_delivery_order_id = to_int(payload.get("sales_delivery_order_id"), "sales_delivery_order_id")
        broker_id = to_int(payload.get("broker_id") or payload.get("broker"), "broker_id")
        billing_to_id = to_int(payload.get("billing_to_id"), "billing_to_id")
        shipping_to_id = to_int(payload.get("shipping_to_id"), "shipping_to_id")

        gross_amount = to_float(payload.get("gross_amount"), "gross_amount")
        freight_charges = to_float(payload.get("freight_charges"), "freight_charges")
        round_off = to_float(payload.get("round_off"), "round_off")
        tax_amount = to_float(payload.get("tax_amount"), "tax_amount")
        tax_payable = to_float(payload.get("tax_payable"), "tax_payable")

        challan_date = None
        if payload.get("challan_date"):
            try:
                challan_date = datetime.strptime(str(payload["challan_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        eway_bill_date = None
        if payload.get("eway_bill_date"):
            try:
                eway_bill_date = datetime.strptime(str(payload["eway_bill_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        # Jute-specific: extract fields and adjust invoice_amount for claim deduction
        invoice_type = to_int(payload.get("invoice_type"), "invoice_type")
        jute_data = payload.get("jute") or {}
        govtskg_data = payload.get("govtskg") or {}

        due_date = None
        if payload.get("due_date"):
            try:
                due_date = datetime.strptime(str(payload["due_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        contract_date = None
        if payload.get("contract_date"):
            try:
                contract_date = datetime.strptime(str(payload["contract_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        consignment_date = None
        if payload.get("consignment_date"):
            try:
                consignment_date = datetime.strptime(str(payload["consignment_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass

        # Extract 9 new fields for e-invoice
        transporter_branch_id = to_int(payload.get("transporter_branch_id"), "transporter_branch_id")
        transporter_doc_no = payload.get("transporter_doc_no")
        transporter_doc_date = None
        if payload.get("transporter_doc_date"):
            try:
                transporter_doc_date = datetime.strptime(str(payload["transporter_doc_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass
        buyer_order_no = payload.get("buyer_order_no")
        buyer_order_date = None
        if payload.get("buyer_order_date"):
            try:
                buyer_order_date = datetime.strptime(str(payload["buyer_order_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass
        irn = payload.get("irn")
        ack_no = payload.get("ack_no")
        ack_date = None
        if payload.get("ack_date"):
            try:
                ack_date = datetime.strptime(str(payload["ack_date"]), "%Y-%m-%d").date()
            except ValueError:
                pass
        qr_code = payload.get("qr_code")

        # Update header
        update_hdr = update_sales_invoice()
        db.execute(update_hdr, {
            "invoice_id": invoice_id,
            "invoice_date": invoice_date,
            "branch_id": branch_id,
            "party_id": party_id,
            "sales_delivery_order_id": sales_delivery_order_id,
            "broker_id": broker_id,
            "billing_to_id": billing_to_id,
            "shipping_to_id": shipping_to_id,
            "challan_no": payload.get("challan_no"),
            "challan_date": challan_date,
            "transporter_id": transporter_id,
            "vehicle_no": payload.get("vehicle_no"),
            "transporter_name": payload.get("transporter_name"),
            "transporter_address": payload.get("transporter_address"),
            "transporter_state_code": payload.get("transporter_state_code"),
            "transporter_state_name": payload.get("transporter_state_name"),
            "eway_bill_no": payload.get("eway_bill_no"),
            "eway_bill_date": eway_bill_date,
            "invoice_type": invoice_type,
            "footer_notes": payload.get("footer_note"),
            "internal_note": payload.get("internal_note"),
            "terms": payload.get("terms"),
            "terms_conditions": payload.get("terms_conditions"),
            "invoice_amount": gross_amount or 0,
            "tax_amount": tax_amount or 0,
            "tax_payable": tax_payable,
            "freight_charges": freight_charges or 0,
            "round_off": round_off or 0,
            "shipping_state_code": to_int(payload.get("shipping_state_code"), "shipping_state_code"),
            "intra_inter_state": payload.get("intra_inter_state"),
            "due_date": due_date,
            "type_of_sale": payload.get("type_of_sale"),
            "tax_id": to_int(payload.get("tax_id"), "tax_id"),
            "container_no": payload.get("container_no"),
            "contract_no": to_int(payload.get("contract_no"), "contract_no"),
            "contract_date": contract_date,
            "consignment_no": payload.get("consignment_no"),
            "consignment_date": consignment_date,
            "payment_terms": to_int(payload.get("payment_terms"), "payment_terms"),
            "sales_order_id": to_int(payload.get("sales_order_id"), "sales_order_id"),
            "billing_state_code": to_int(payload.get("billing_state_code"), "billing_state_code"),
            "bank_detail_id": to_int(payload.get("bank_detail_id"), "bank_detail_id"),
            "transporter_branch_id": transporter_branch_id,
            "transporter_doc_no": transporter_doc_no,
            "transporter_doc_date": transporter_doc_date,
            "buyer_order_no": buyer_order_no,
            "buyer_order_date": buyer_order_date,
            "irn": irn,
            "ack_no": ack_no,
            "ack_date": ack_date,
            "qr_code": qr_code,
            "updated_by": user_id,
        })

        # Delete old GST, jute detail, jute header, govtskg, and hessian detail before re-inserting
        db.execute(delete_sales_invoice_dtl_gst(), {"invoice_id": invoice_id})
        db.execute(delete_sales_invoice_jute_dtl(), {"invoice_id": invoice_id})
        db.execute(delete_sales_invoice_jute(), {"invoice_id": invoice_id})
        db.execute(delete_sales_invoice_govtskg(), {"invoice_id": invoice_id})
        db.execute(delete_sale_invoice_govtskg_dtl(), {"invoice_id": invoice_id})
        db.execute(delete_sales_invoice_hessian_dtl(), {"invoice_id": invoice_id})

        # Delete old additional charges
        from src.sales.query import delete_sales_invoice_additional_gst, delete_sales_invoice_additional
        db.execute(delete_sales_invoice_additional_gst(), {"invoice_id": invoice_id})
        db.execute(delete_sales_invoice_additional(), {"invoice_id": invoice_id})

        # Soft-delete old line items
        delete_q = delete_invoice_line_items()
        db.execute(delete_q, {"invoice_id": invoice_id})

        # Re-insert line items + GST + type-specific detail
        line_query = insert_invoice_line_item()
        gst_query = insert_sales_invoice_dtl_gst()
        jute_dtl_query = insert_sales_invoice_jute_dtl()
        hessian_dtl_query = insert_sales_invoice_hessian_dtl()
        govtskg_dtl_query = insert_sale_invoice_govtskg_dtl()
        normalized_items = []
        for idx, item in enumerate(raw_items, start=1):
            item_val = item.get("item")
            if not item_val:
                raise HTTPException(status_code=400, detail=f"items[{idx}].item is required")
            uom_val = item.get("uom")
            if not uom_val:
                raise HTTPException(status_code=400, detail=f"items[{idx}].uom is required")

            qty = to_positive_float(item.get("quantity"), f"items[{idx}].quantity")
            rate = to_float(item.get("rate"), f"items[{idx}].rate")

            amount_without_tax = to_float(item.get("net_amount"), f"items[{idx}].net_amount")
            if amount_without_tax is None and qty and rate:
                amount_without_tax = round(qty * rate, 2)

            gst = item.get("gst") or {}
            cgst_amt = to_float(gst.get("cgst_amount"), "cgst_amount")
            sgst_amt = to_float(gst.get("sgst_amount"), "sgst_amount")
            igst_amt = to_float(gst.get("igst_amount"), "igst_amount")

            line_total = to_float(item.get("total_amount"), f"items[{idx}].total_amount")
            if line_total is None and amount_without_tax is not None:
                line_tax = (cgst_amt or 0) + (sgst_amt or 0) + (igst_amt or 0)
                line_total = round((amount_without_tax or 0) + line_tax, 2)

            dtl_result = db.execute(line_query, {
                "invoice_id": invoice_id,
                "hsn_code": item.get("hsn_code"),
                "item_id": to_int(item_val, f"items[{idx}].item"),
                "item_make_id": to_int(item.get("item_make"), f"items[{idx}].item_make"),
                "quantity": qty,
                "uom_id": to_int(uom_val, f"items[{idx}].uom"),
                "rate": rate,
                "discount_type": item.get("discount_type"),
                "discounted_rate": to_float(item.get("discounted_rate"), f"items[{idx}].discounted_rate"),
                "discount_amount": to_float(item.get("discount_amount"), f"items[{idx}].discount_amount"),
                "amount_without_tax": amount_without_tax,
                "total_amount": line_total,
                "sales_weight": to_float(item.get("sales_weight"), f"items[{idx}].sales_weight"),
                "remarks": item.get("remarks"),
                "delivery_order_dtl_id": to_int(item.get("delivery_order_dtl_id"), f"items[{idx}].delivery_order_dtl_id"),
                "sales_order_dtl_id": to_int(item.get("sales_order_dtl_id"), f"items[{idx}].sales_order_dtl_id"),
            })
            lineitem_id = dtl_result.lastrowid

            # Insert GST into separate table
            gst_data = gst if gst else None
            if gst_data and isinstance(gst_data, dict) and lineitem_id:
                db.execute(gst_query, {
                    "invoice_line_item_id": lineitem_id,
                    "tax_percentage": to_float(gst_data.get("tax_percentage"), "tax_percentage"),
                    "cgst_amount": to_float(gst_data.get("cgst_amount"), "cgst_amount") or 0,
                    "cgst_percentage": to_float(gst_data.get("cgst_percent"), "cgst_percent") or 0,
                    "sgst_amount": to_float(gst_data.get("sgst_amount"), "sgst_amount") or 0,
                    "sgst_percentage": to_float(gst_data.get("sgst_percent"), "sgst_percent") or 0,
                    "igst_amount": to_float(gst_data.get("igst_amount"), "igst_amount") or 0,
                    "igst_percentage": to_float(gst_data.get("igst_percent"), "igst_percent") or 0,
                    "tax_amount": to_float(gst_data.get("tax_amount"), "gst_tax_amount") or 0,
                })

            # Insert jute detail into separate table
            jute_dtl_data = item.get("jute_dtl") or None
            if jute_dtl_data and isinstance(jute_dtl_data, dict) and lineitem_id:
                db.execute(jute_dtl_query, {
                    "invoice_line_item_id": lineitem_id,
                    "claim_amount_dtl": to_float(jute_dtl_data.get("claim_amount_dtl"), "claim_amount_dtl"),
                    "claim_desc": jute_dtl_data.get("claim_desc"),
                    "claim_rate": to_float(jute_dtl_data.get("claim_rate"), "claim_rate"),
                    "unit_conversion": jute_dtl_data.get("unit_conversion"),
                    "qty_untit_conversion": to_int(jute_dtl_data.get("qty_untit_conversion"), "qty_untit_conversion"),
                })

            # Insert hessian detail into separate table
            hessian_dtl_data = item.get("hessian_dtl") or None
            if hessian_dtl_data and isinstance(hessian_dtl_data, dict) and lineitem_id:
                db.execute(hessian_dtl_query, {
                    "invoice_line_item_id": lineitem_id,
                    "qty_bales": to_float(hessian_dtl_data.get("qty_bales"), "qty_bales"),
                    "rate_per_bale": to_float(hessian_dtl_data.get("rate_per_bale"), "rate_per_bale"),
                    "billing_rate_mt": to_float(hessian_dtl_data.get("billing_rate_mt"), "billing_rate_mt"),
                    "billing_rate_bale": to_float(hessian_dtl_data.get("billing_rate_bale"), "billing_rate_bale"),
                    "updated_by": user_id,
                })

            # Insert govt sacking detail into separate table
            govtskg_dtl_data = item.get("govtskg_dtl") or None
            if govtskg_dtl_data and isinstance(govtskg_dtl_data, dict) and lineitem_id:
                db.execute(govtskg_dtl_query, {
                    "invoice_line_item_id": lineitem_id,
                    "pack_sheet": to_float(govtskg_dtl_data.get("pack_sheet"), "pack_sheet"),
                    "net_weight": to_float(govtskg_dtl_data.get("net_weight"), "net_weight"),
                    "total_weight": to_float(govtskg_dtl_data.get("total_weight"), "total_weight"),
                    "updated_by": user_id,
                })

            normalized_items.append(item)

        # Re-insert jute header data if provided
        if jute_data:
            # Compute claim_amount as sum of line item claim_amount_dtl values
            claim_amount_from_lines = sum(
                to_float((it.get("jute_dtl") or {}).get("claim_amount_dtl"), "claim_amount_dtl") or 0
                for it in normalized_items
                if it.get("jute_dtl")
            )
            if claim_amount_from_lines:
                claim_amount = round(claim_amount_from_lines, 2)
            else:
                claim_amount = to_float(jute_data.get("claim_amount"), "claim_amount")

            db.execute(insert_sales_invoice_jute(), {
                "invoice_id": invoice_id,
                "mr_no": jute_data.get("mr_no"),
                "mr_id": to_int(jute_data.get("mr_id"), "mr_id"),
                "claim_amount": claim_amount,
                "other_reference": jute_data.get("other_reference"),
                "unit_conversion": jute_data.get("unit_conversion"),
                "claim_description": jute_data.get("claim_description"),
                "mukam_id": to_int(jute_data.get("mukam_id"), "mukam_id"),
            })

        # Re-insert govt SKG header data if provided
        if govtskg_data:
            db.execute(insert_sales_invoice_govtskg(), {
                "invoice_id": invoice_id,
                "pcso_no": govtskg_data.get("pcso_no"),
                "pcso_date": format_date(govtskg_data.get("pcso_date")),
                "administrative_office_address": govtskg_data.get("administrative_office_address"),
                "destination_rail_head": govtskg_data.get("destination_rail_head"),
                "loading_point": govtskg_data.get("loading_point"),
                "mode_of_transport": govtskg_data.get("mode_of_transport"),
                "pack_sheet": to_float(govtskg_data.get("pack_sheet"), "pack_sheet"),
                "net_weight": to_float(govtskg_data.get("net_weight"), "net_weight"),
                "total_weight": to_float(govtskg_data.get("total_weight"), "total_weight"),
            })

        # Re-insert additional charges
        additional_charges_list = payload.get("additional_charges") or []
        if additional_charges_list:
            from src.sales.query import insert_sales_invoice_additional, insert_sales_invoice_additional_gst
            add_query = insert_sales_invoice_additional()
            add_gst_query = insert_sales_invoice_additional_gst()
            for charge in additional_charges_list:
                charge_result = db.execute(add_query, {
                    "invoice_id": invoice_id,
                    "additional_charges_id": to_int(charge.get("additional_charges_id"), "additional_charges_id"),
                    "qty": to_float(charge.get("qty"), "qty"),
                    "rate": to_float(charge.get("rate"), "rate"),
                    "net_amount": to_float(charge.get("net_amount"), "net_amount"),
                    "remarks": charge.get("remarks"),
                    "updated_by": user_id,
                    "updated_date_time": updated_at,
                })
                charge_id = charge_result.lastrowid
                gst_data = charge.get("gst")
                if gst_data and isinstance(gst_data, dict) and charge_id:
                    db.execute(add_gst_query, {
                        "sales_invoice_additional_id": charge_id,
                        "igst_amount": to_float(gst_data.get("igst_amount"), "igst_amount"),
                        "igst_percent": to_float(gst_data.get("igst_percent"), "igst_percent"),
                        "cgst_amount": to_float(gst_data.get("cgst_amount"), "cgst_amount"),
                        "cgst_percent": to_float(gst_data.get("cgst_percent"), "cgst_percent"),
                        "sgst_amount": to_float(gst_data.get("sgst_amount"), "sgst_amount"),
                        "sgst_percent": to_float(gst_data.get("sgst_percent"), "sgst_percent"),
                        "gst_total": to_float(gst_data.get("gst_total"), "gst_total"),
                    })

        db.commit()
        return {"message": "Sales invoice updated successfully", "invoice_id": invoice_id}
    except HTTPException as exc:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error updating sales invoice")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================


@router.post("/open_sales_invoice")
async def open_sales_invoice(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Open a sales invoice (21 -> 1). Generates document number."""
    try:
        invoice_id = to_int(payload.get("invoice_id"), "invoice_id", required=True)
        branch_id = to_int(payload.get("branch_id"), "branch_id", required=True)
        user_id = int(token_data.get("user_id"))

        doc_query = get_invoice_with_approval_info()
        doc_result = db.execute(doc_query, {"invoice_id": invoice_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found")
        doc = dict(doc_result._mapping)

        if doc.get("status_id") != 21:
            raise HTTPException(status_code=400, detail=f"Cannot open invoice with status {doc.get('status_id')}. Expected 21 (Draft).")

        invoice_date = doc.get("invoice_date")
        if not invoice_date:
            raise HTTPException(status_code=400, detail="Invoice date is required to generate document number.")

        current_no = doc.get("invoice_no")
        new_no = None
        new_no_string = None
        if current_no is None or current_no == "" or current_no == 0:
            fy_start, fy_end = get_fy_boundaries(invoice_date)
            max_query = get_max_invoice_no_for_branch_fy()
            max_result = db.execute(max_query, {"branch_id": branch_id, "fy_start_date": fy_start, "fy_end_date": fy_end}).fetchone()
            max_no = dict(max_result._mapping).get("max_doc_no") or 0 if max_result else 0
            new_no = int(max_no) + 1

            # Get prefixes for formatted number string
            branch_row = db.execute(
                text("SELECT bm.branch_prefix, cm.co_prefix FROM branch_mst bm LEFT JOIN co_mst cm ON cm.co_id = bm.co_id WHERE bm.branch_id = :branch_id"),
                {"branch_id": branch_id},
            ).fetchone()
            if branch_row:
                bdata = dict(branch_row._mapping)
                try:
                    new_no_string = format_indent_no(
                        indent_no=new_no,
                        co_prefix=bdata.get("co_prefix"),
                        branch_prefix=bdata.get("branch_prefix"),
                        indent_date=invoice_date,
                        document_type=SALES_DOC_TYPES.get("INVOICE", "SI"),
                    )
                except Exception:
                    new_no_string = str(new_no)

        update_q = update_invoice_status()
        db.execute(update_q, {
            "invoice_id": invoice_id,
            "status_id": 1,
            "approval_level": None,
            "invoice_no": new_no,
            "updated_by": user_id,
            "updated_date_time": now_ist(),
        })
        db.commit()

        return {
            "status": "success",
            "new_status_id": 1,
            "message": "Sales invoice opened successfully.",
            "invoice_no": new_no_string if new_no_string else str(current_no) if current_no else None,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error opening sales invoice")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel_draft_sales_invoice")
async def cancel_draft_sales_invoice(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Cancel a draft sales invoice (21 -> 6)."""
    try:
        invoice_id = to_int(payload.get("invoice_id"), "invoice_id", required=True)
        user_id = int(token_data.get("user_id"))

        doc_query = get_invoice_with_approval_info()
        doc_result = db.execute(doc_query, {"invoice_id": invoice_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found")
        if dict(doc_result._mapping).get("status_id") != 21:
            raise HTTPException(status_code=400, detail="Cannot cancel. Expected status 21 (Draft).")

        update_q = update_invoice_status()
        db.execute(update_q, {
            "invoice_id": invoice_id,
            "status_id": 6,
            "approval_level": None,
            "invoice_no": None,
            "updated_by": user_id,
            "updated_date_time": now_ist(),
        })
        db.commit()
        return {"status": "success", "new_status_id": 6, "message": "Draft cancelled successfully."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send_sales_invoice_for_approval")
async def send_sales_invoice_for_approval(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Send sales invoice for approval (1 -> 20, level=1)."""
    try:
        invoice_id = to_int(payload.get("invoice_id"), "invoice_id", required=True)
        user_id = int(token_data.get("user_id"))

        doc_query = get_invoice_with_approval_info()
        doc_result = db.execute(doc_query, {"invoice_id": invoice_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found")
        if dict(doc_result._mapping).get("status_id") != 1:
            raise HTTPException(status_code=400, detail="Cannot send for approval. Expected status 1 (Open).")

        update_q = update_invoice_status()
        db.execute(update_q, {
            "invoice_id": invoice_id,
            "status_id": 20,
            "approval_level": 1,
            "invoice_no": None,
            "updated_by": user_id,
            "updated_date_time": now_ist(),
        })
        db.commit()
        return {"status": "success", "new_status_id": 20, "new_approval_level": 1, "message": "Sales invoice sent for approval."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve_sales_invoice")
async def approve_sales_invoice(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Approve a sales invoice."""
    try:
        invoice_id = to_int(payload.get("invoice_id"), "invoice_id", required=True)
        menu_id = to_int(payload.get("menu_id"), "menu_id", required=True)
        user_id = int(token_data.get("user_id"))

        doc_query = get_invoice_with_approval_info()
        doc_result = db.execute(doc_query, {"invoice_id": invoice_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found")
        document_amount = float(dict(doc_result._mapping).get("invoice_amount", 0) or 0)

        result = process_approval(
            doc_id=invoice_id,
            user_id=user_id,
            menu_id=menu_id,
            db=db,
            get_doc_fn=get_invoice_with_approval_info,
            update_status_fn=update_invoice_status,
            id_param_name="invoice_id",
            doc_name="Sales invoice",
            document_amount=document_amount,
            extra_update_params={"invoice_no": None},
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject_sales_invoice")
async def reject_sales_invoice(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Reject a sales invoice (20 -> 4)."""
    try:
        invoice_id = to_int(payload.get("invoice_id"), "invoice_id", required=True)
        menu_id = to_int(payload.get("menu_id"), "menu_id")
        user_id = int(token_data.get("user_id"))
        reason = payload.get("reason")

        result = process_rejection(
            doc_id=invoice_id,
            user_id=user_id,
            menu_id=menu_id,
            db=db,
            get_doc_fn=get_invoice_with_approval_info,
            update_status_fn=update_invoice_status,
            id_param_name="invoice_id",
            doc_name="Sales invoice",
            reason=reason,
            extra_update_params={"invoice_no": None},
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reopen_sales_invoice")
async def reopen_sales_invoice(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """Reopen a cancelled (6 -> 21) or rejected (4 -> 1) sales invoice."""
    try:
        invoice_id = to_int(payload.get("invoice_id"), "invoice_id", required=True)
        user_id = int(token_data.get("user_id"))

        doc_query = get_invoice_with_approval_info()
        doc_result = db.execute(doc_query, {"invoice_id": invoice_id}).fetchone()
        if not doc_result:
            raise HTTPException(status_code=404, detail="Sales invoice not found")
        current_status = dict(doc_result._mapping).get("status_id")

        if current_status == 6:
            new_status_id = 21
        elif current_status == 4:
            new_status_id = 1
        else:
            raise HTTPException(status_code=400, detail=f"Cannot reopen with status {current_status}. Only 6 or 4.")

        update_q = update_invoice_status()
        db.execute(update_q, {
            "invoice_id": invoice_id,
            "status_id": new_status_id,
            "approval_level": None,
            "invoice_no": None,
            "updated_by": user_id,
            "updated_date_time": now_ist(),
        })
        db.commit()
        return {"status": "success", "new_status_id": new_status_id, "message": f"Sales invoice reopened (status: {new_status_id})."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
