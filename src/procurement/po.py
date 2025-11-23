from fastapi import Depends, Request, HTTPException, APIRouter
import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from datetime import datetime
from typing import Optional
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.procurement.query import (
	get_po_table_query,
	get_po_table_count_query,
	get_suppliers_with_party_type_1,
	get_supplier_branches,
	get_company_branch_addresses,
	get_indent_line_items_for_po,
	insert_proc_po,
	insert_proc_po_dtl,
	insert_proc_po_additional,
	insert_po_gst,
	update_proc_po,
	delete_proc_po_dtl,
	delete_proc_po_additional,
	delete_po_gst,
	get_po_by_id_query,
	get_po_dtl_by_id_query,
	get_po_additional_by_id_query,
	get_po_gst_by_id_query,
	get_max_po_no_for_branch_fy,
	get_po_with_approval_info,
	update_po_status,
	get_item_by_group_id_purchaseable,
	get_item_make_by_group_id,
	get_item_uom_by_group_id,
	get_expense_types,
	get_project,
)
from src.masters.query import (
	get_branch_list,
	get_dept_list_by_branch_id,
	get_item_group_drodown,
)
from src.common.companyAdmin.query import get_co_config_by_id_query
from src.procurement.indent import (
	format_indent_no,
	calculate_financial_year,
	calculate_approval_permissions,
)
from src.procurement.query import (
	get_approval_flow_by_menu_branch,
	get_user_approval_level,
	get_max_approval_level,
	get_user_consumed_amounts,
	check_approval_mst_exists,
	get_user_edit_access,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_po_setup_1")
async def get_po_setup_1(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
	branch_id: int | None = None,
	co_id: int | None = None,
):
	"""Return branches, suppliers, projects, expense types (category types), co_config, and branch addresses for PO creation."""
	try:
		# Get query parameters
		q_branch_id = request.query_params.get("branch_id")
		q_co_id = request.query_params.get("co_id")
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

		# Branch list
		branch_ids_list = [branch_id] if branch_id is not None else None
		branchquery = get_branch_list(branch_ids=branch_ids_list) if branch_ids_list else get_branch_list()
		branch_result = db.execute(branchquery, {"branch_ids": branch_ids_list} if branch_ids_list else {}).fetchall()
		branches = [dict(r._mapping) for r in branch_result]

		# Suppliers (party_type_id contains 1)
		supplier_query = get_suppliers_with_party_type_1(co_id=co_id)
		supplier_result = db.execute(supplier_query, {"co_id": co_id}).fetchall()
		suppliers = [dict(r._mapping) for r in supplier_result]

		# Projects (expects branch_id)
		projects = []
		if branch_id is not None:
			project_query = get_project(branch_id=branch_id)
			proj_result = db.execute(project_query, {"branch_id": branch_id}).fetchall()
			projects = [dict(r._mapping) for r in proj_result]

		# Expense types (category types)
		expense_query = get_expense_types()
		exp_result = db.execute(expense_query).fetchall()
		expense_types = [dict(r._mapping) for r in exp_result]

		# Co config
		co_config_query = get_co_config_by_id_query(co_id)
		co_config_result = db.execute(co_config_query, {"co_id": co_id}).fetchone()
		co_config = dict(co_config_result._mapping) if co_config_result else {}

		# Company branch addresses (for billing and shipping)
		# Filter by co_id only (not branch_id) to show all company branch addresses
		branch_addresses_query = get_company_branch_addresses(co_id=co_id, branch_id=None)
		branch_addresses_result = db.execute(branch_addresses_query, {"co_id": co_id, "branch_id": None}).fetchall()
		branch_addresses = [dict(r._mapping) for r in branch_addresses_result]
		
		# Get supplier branch addresses for all suppliers (for shipping addresses)
		supplier_branch_addresses = []
		for supplier in suppliers:
			supplier_id = supplier.get("party_id")
			if supplier_id:
				try:
					supplier_branch_query = get_supplier_branches(party_id=supplier_id)
					supplier_branch_result = db.execute(supplier_branch_query, {"party_id": supplier_id}).fetchall()
					supplier_branches = [dict(r._mapping) for r in supplier_branch_result]
					# Add supplier branches to supplier object
					supplier["branches"] = supplier_branches
				except Exception as e:
					logger.exception(f"Error fetching branches for supplier {supplier_id}")
					supplier["branches"] = []

		return {
			"branches": branches,
			"suppliers": suppliers,  # Now includes full supplier details and their branch addresses
			"projects": projects,
			"expense_types": expense_types,
			"co_config": co_config,
			"branch_addresses": branch_addresses,  # Company branch addresses for billing and shipping
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching PO setup 1")
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_po_setup_2")
async def get_po_setup_2(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Return items, makes, and UOMs by item_group_id (reuse from indent setup)."""
	try:
		q_item_group = request.query_params.get("item_group")
		if q_item_group is None:
			try:
				body = await request.json()
				q_item_group = body.get("item_group") if isinstance(body, dict) else None
			except Exception:
				q_item_group = None

		if q_item_group is None:
			raise HTTPException(status_code=400, detail="item_group is required")

		try:
			item_group_id = int(q_item_group)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid item_group")

		# Get items purchasable in this group
		items_query = get_item_by_group_id_purchaseable(item_group_id=item_group_id)
		items_result = db.execute(items_query, {"item_group_id": item_group_id}).fetchall()
		items = [dict(r._mapping) for r in items_result]

		# Get item makes for this group
		makes_query = get_item_make_by_group_id(item_group_id=item_group_id)
		makes_result = db.execute(makes_query, {"item_group_id": item_group_id}).fetchall()
		makes = [dict(r._mapping) for r in makes_result]

		# Get item uom mappings for this group
		uoms_query = get_item_uom_by_group_id(item_group_id=item_group_id)
		uoms_result = db.execute(uoms_query, {"item_group_id": item_group_id}).fetchall()
		uoms = [dict(r._mapping) for r in uoms_result]

		return {
			"items": items,
			"makes": makes,
			"uoms": uoms,
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching PO setup 2")
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_indent_line_items")
async def get_indent_line_items(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Get line items for an indent to be used in PO creation popup."""
	try:
		q_indent_id = request.query_params.get("indent_id")
		if q_indent_id is None:
			raise HTTPException(status_code=400, detail="indent_id is required")

		try:
			indent_id = int(q_indent_id)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid indent_id")

		indent_line_items_query = get_indent_line_items_for_po(indent_id=indent_id)
		line_items_result = db.execute(indent_line_items_query, {"indent_id": indent_id}).fetchall()
		line_items = [dict(r._mapping) for r in line_items_result]

		return {
			"indent_id": indent_id,
			"line_items": line_items,
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching indent line items")
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_supplier_branches")
async def get_supplier_branches_api(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Get branch addresses for a selected supplier."""
	try:
		q_party_id = request.query_params.get("party_id")
		if q_party_id is None:
			raise HTTPException(status_code=400, detail="party_id is required")

		try:
			party_id = int(q_party_id)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid party_id")

		supplier_branches_query = get_supplier_branches(party_id=party_id)
		branches_result = db.execute(supplier_branches_query, {"party_id": party_id}).fetchall()
		branches = [dict(r._mapping) for r in branches_result]

		return {
			"party_id": party_id,
			"branches": branches,
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching supplier branches")
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_po_table")
async def get_po_table(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
	page: int = 1,
	limit: int = 10,
	search: str | None = None,
	co_id: int | None = None,
):
	"""Return paginated procurement purchase order list."""

	try:
		page = max(page, 1)
		limit = max(min(limit, 100), 1)
		offset = (page - 1) * limit
		search_like = None
		if search:
			search_like = f"%{search.strip()}%"

		params = {
			"co_id": co_id,
			"search_like": search_like,
			"limit": limit,
			"offset": offset,
		}

		list_query = get_po_table_query()
		rows = db.execute(list_query, params).fetchall()
		data = []
		for row in rows:
			mapped = dict(row._mapping)
			po_date_obj = mapped.get("po_date")
			po_date = po_date_obj
			if hasattr(po_date_obj, "isoformat"):
				po_date = po_date_obj.isoformat()
			
			po_value = mapped.get("po_value")
			if po_value is not None:
				try:
					po_value = float(po_value)
				except (TypeError, ValueError):
					po_value = None
			
			data.append(
				{
					"po_id": mapped.get("po_id"),
					"po_no": mapped.get("po_no") or "",
					"po_date": po_date,
					"supplier_name": mapped.get("supp_name") or "",
					"po_value": po_value,
					"branch_name": mapped.get("branch_name") or "",
					"project_name": mapped.get("project_name") or None,
					"status": mapped.get("status_name") or "Pending",
				}
			)

		count_query = get_po_table_count_query()
		count_result = db.execute(count_query, params).scalar()
		total = int(count_result) if count_result is not None else 0

		return {"data": data, "total": total}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching PO table")
		raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ==================== HELPER FUNCTIONS ====================

def format_po_no(
	po_no: Optional[int],
	co_prefix: Optional[str],
	branch_prefix: Optional[str],
	po_date,
) -> str:
	"""Format PO number as "co_prefix/branch_prefix/PO/financial_year/po_no"."""
	if po_no is None or po_no == 0:
		return ""
	
	fy = calculate_financial_year(po_date)
	co_pref = co_prefix or ""
	branch_pref = branch_prefix or ""
	
	parts = []
	if co_pref:
		parts.append(co_pref)
	if branch_pref:
		parts.append(branch_pref)
	parts.extend(["PO", fy, str(po_no)])
	
	return "/".join(parts)


def calculate_gst_amounts(
	amount: float,
	tax_percentage: float,
	billing_state_id: int,
	shipping_state_id: int,
) -> dict:
	"""Calculate GST amounts based on billing and shipping states.
	
	Returns dict with:
	- i_tax_percentage: IGST percentage
	- s_tax_percentage: SGST percentage (if same state)
	- c_tax_percentage: CGST percentage (if same state)
	- i_tax_amount: IGST amount
	- s_tax_amount: SGST amount
	- c_tax_amount: CGST amount
	- tax_amount: Total tax amount
	"""
	if billing_state_id == shipping_state_id:
		# Same state: Split tax into SGST and CGST (each half)
		sgst_pct = tax_percentage / 2.0
		cgst_pct = tax_percentage / 2.0
		igst_pct = 0.0
		sgst_amt = (amount * sgst_pct) / 100.0
		cgst_amt = (amount * cgst_pct) / 100.0
		igst_amt = 0.0
	else:
		# Different state: Full tax as IGST
		igst_pct = tax_percentage
		sgst_pct = 0.0
		cgst_pct = 0.0
		igst_amt = (amount * igst_pct) / 100.0
		sgst_amt = 0.0
		cgst_amt = 0.0
	
	total_tax = igst_amt + sgst_amt + cgst_amt
	
	return {
		"i_tax_percentage": igst_pct,
		"s_tax_percentage": sgst_pct,
		"c_tax_percentage": cgst_pct,
		"i_tax_amount": igst_amt,
		"s_tax_amount": sgst_amt,
		"c_tax_amount": cgst_amt,
		"tax_amount": total_tax,
		"tax_pct": tax_percentage,
		"stax_percentage": sgst_pct + cgst_pct,  # Combined state tax
	}


# ==================== CRUD APIs ====================

@router.post("/create_po")
async def create_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Create a purchase order with line items, additional charges, and GST."""
	
	def to_int(value, field_name: str, required: bool = False) -> int | None:
		if value is None or value == "":
			if required:
				raise HTTPException(status_code=400, detail=f"{field_name} is required")
			return None
		try:
			return int(value)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

	def to_float(value, field_name: str, default: float = 0.0) -> float:
		if value is None or value == "":
			return default
		try:
			return float(value)
		except (TypeError, ValueError):
			return default

	try:
		# Header fields
		branch_id = to_int(payload.get("branch"), "branch", required=True)
		supplier_id = to_int(payload.get("supplier"), "supplier", required=True)
		supplier_branch_id = to_int(payload.get("supplier_branch"), "supplier_branch", required=True)
		billing_branch_id = to_int(payload.get("billing_address"), "billing_address", required=True)
		shipping_branch_id = to_int(payload.get("shipping_address"), "shipping_address", required=True)
		project_id = to_int(payload.get("project"), "project", required=True)
		
		date_str = payload.get("date")
		if not date_str:
			raise HTTPException(status_code=400, detail="date is required")
		try:
			po_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
		except ValueError:
			raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

		credit_days = to_int(payload.get("credit_term"), "credit_term")
		expected_delivery_days = to_int(payload.get("delivery_timeline"), "delivery_timeline", required=True)
		contact_person = payload.get("contact_person", "").strip() or None
		contact_no = payload.get("contact_no", "").strip() or None
		footer_notes = payload.get("footer_note", "").strip() or None
		remarks = payload.get("internal_note", "").strip() or None
		terms_conditions = payload.get("terms_conditions", "").strip() or None
		
		advance_value = to_float(payload.get("advance_percentage"), "advance_percentage")
		
		# Get billing and shipping state IDs for GST calculation
		billing_branch_query = text("SELECT state_id FROM branch_mst WHERE branch_id = :branch_id")
		billing_result = db.execute(billing_branch_query, {"branch_id": billing_branch_id}).fetchone()
		billing_state_id = billing_result[0] if billing_result else None
		
		shipping_branch_query = text("SELECT state_id FROM branch_mst WHERE branch_id = :branch_id")
		shipping_result = db.execute(shipping_branch_query, {"branch_id": shipping_branch_id}).fetchone()
		shipping_state_id = shipping_result[0] if shipping_result else None
		
		# Get co_config to check india_gst
		branch_query = text("SELECT co_id FROM branch_mst WHERE branch_id = :branch_id")
		branch_result = db.execute(branch_query, {"branch_id": branch_id}).fetchone()
		co_id = branch_result[0] if branch_result else None
		
		india_gst = False
		if co_id:
			co_config_query = get_co_config_by_id_query(co_id)
			co_config_result = db.execute(co_config_query, {"co_id": co_id}).fetchone()
			if co_config_result:
				co_config = dict(co_config_result._mapping)
				india_gst = bool(co_config.get("india_gst", False))
		
		# Line items
		raw_items = payload.get("items", [])
		if not isinstance(raw_items, list) or len(raw_items) == 0:
			raise HTTPException(status_code=400, detail="At least one item row is required")
		
		# Additional charges
		raw_additional = payload.get("additional_charges", [])
		
		updated_by = to_int(token_data.get("user_id"), "updated_by")
		created_at = datetime.utcnow()
		
		# Calculate totals
		net_amount = 0.0
		total_igst = 0.0
		total_sgst = 0.0
		total_cgst = 0.0
		
		# Process line items
		normalized_items = []
		for idx, item in enumerate(raw_items, start=1):
			item_id = to_int(item.get("item"), f"items[{idx}].item", required=True)
			qty = to_float(item.get("quantity"), f"items[{idx}].quantity")
			if qty <= 0:
				raise HTTPException(status_code=400, detail=f"items[{idx}].quantity must be greater than zero")
			rate = to_float(item.get("rate"), f"items[{idx}].rate")
			uom_id = to_int(item.get("uom"), f"items[{idx}].uom", required=True)
			item_make_id = to_int(item.get("make"), f"items[{idx}].make")
			indent_dtl_id = to_int(item.get("indent_dtl_id"), f"items[{idx}].indent_dtl_id")
			
			# Get tax percentage from item_mst
			item_query = text("SELECT tax_percentage, hsn_code FROM item_mst WHERE item_id = :item_id")
			item_result = db.execute(item_query, {"item_id": item_id}).fetchone()
			tax_percentage = 0.0
			hsn_code = None
			if item_result:
				tax_percentage = float(item_result[0] or 0.0)
				hsn_code = item_result[1]
			
			# Discount calculation
			discount_mode = to_int(item.get("discount_mode"), f"items[{idx}].discount_mode")
			discount_value = to_float(item.get("discount_value"), f"items[{idx}].discount_value")
			discount_amount = 0.0
			
			base_amount = qty * rate
			if discount_mode == 1:  # Percentage
				if discount_value > 100:
					raise HTTPException(status_code=400, detail=f"items[{idx}].discount_value cannot be greater than 100")
				discount_amount = (base_amount * discount_value) / 100.0
			elif discount_mode == 2:  # Amount
				if discount_value > base_amount:
					raise HTTPException(status_code=400, detail=f"items[{idx}].discount_amount cannot be greater than total amount")
				discount_amount = discount_value
			
			amount = base_amount - discount_amount
			net_amount += amount
			
			# Calculate GST if india_gst is enabled
			if india_gst and billing_state_id and shipping_state_id and tax_percentage > 0:
				gst_amounts = calculate_gst_amounts(amount, tax_percentage, billing_state_id, shipping_state_id)
				total_igst += gst_amounts["i_tax_amount"]
				total_sgst += gst_amounts["s_tax_amount"]
				total_cgst += gst_amounts["c_tax_amount"]
			else:
				gst_amounts = None
			
			remarks_raw = item.get("remarks", "").strip() or None
			
			normalized_items.append({
				"item_id": item_id,
				"qty": qty,
				"rate": rate,
				"uom_id": uom_id,
				"item_make_id": item_make_id,
				"indent_dtl_id": indent_dtl_id,
				"hsn_code": hsn_code,
				"discount_mode": discount_mode,
				"discount_value": discount_value,
				"discount_amount": discount_amount,
				"amount": amount,
				"remarks": remarks_raw,
				"tax_percentage": tax_percentage,
				"gst_amounts": gst_amounts,
			})
		
		# Process additional charges
		normalized_additional = []
		for idx, addl in enumerate(raw_additional, start=1):
			additional_charges_id = to_int(addl.get("additional_charges_id"), f"additional_charges[{idx}].additional_charges_id", required=True)
			qty = to_int(addl.get("qty"), f"additional_charges[{idx}].qty", required=True)
			rate = to_float(addl.get("rate"), f"additional_charges[{idx}].rate")
			net_amt = qty * rate
			net_amount += net_amt
			
			remarks_raw = addl.get("remarks", "").strip() or None
			
			# GST for additional charges (if applicable)
			gst_amounts = None
			if india_gst and billing_state_id and shipping_state_id:
				# Get tax percentage from additional_charges_master or use default
				addl_query = text("SELECT default_value FROM additional_charges_master WHERE additional_charges_id = :id")
				addl_result = db.execute(addl_query, {"id": additional_charges_id}).fetchone()
				tax_pct = float(addl_result[0] or 0.0) if addl_result else 0.0
				if tax_pct > 0:
					gst_amounts = calculate_gst_amounts(net_amt, tax_pct, billing_state_id, shipping_state_id)
					total_igst += gst_amounts["i_tax_amount"]
					total_sgst += gst_amounts["s_tax_amount"]
					total_cgst += gst_amounts["c_tax_amount"]
			
			normalized_additional.append({
				"additional_charges_id": additional_charges_id,
				"qty": qty,
				"rate": rate,
				"net_amount": net_amt,
				"remarks": remarks_raw,
				"gst_amounts": gst_amounts,
			})
		
		total_amount = net_amount + total_igst + total_sgst + total_cgst
		advance_amount = (net_amount * advance_value) / 100.0 if advance_value > 0 else 0.0
		
		# Insert PO header
		insert_header_query = insert_proc_po()
		header_params = {
			"credit_days": credit_days,
			"delivery_instructions": None,
			"expected_delivery_days": expected_delivery_days,
			"footer_notes": footer_notes,
			"po_date": po_date,
			"po_approve_date": None,
			"po_no": None,  # Will be generated on open
			"remarks": remarks,
			"delivery_mode": None,
			"terms_conditions": terms_conditions,
			"branch_id": branch_id,
			"price_enquiry_id": None,
			"project_id": project_id,
			"supplier_id": supplier_id,
			"status_id": 21,  # Drafted
			"supplier_branch_id": supplier_branch_id,
			"billing_branch_id": billing_branch_id,
			"shipping_branch_id": shipping_branch_id,
			"total_amount": total_amount,
			"net_amount": net_amount,
			"advance_type": 1 if advance_value > 0 else None,
			"advance_value": advance_value,
			"advance_amount": advance_amount,
			"contact_no": contact_no,
			"contact_person": contact_person,
			"updated_by": updated_by,
			"update_date_time": created_at,
			"approval_level": None,
		}
		
		result = db.execute(insert_header_query, header_params)
		po_id = result.lastrowid
		if not po_id:
			raise HTTPException(status_code=500, detail="Failed to create PO header")
		
		# Insert line items
		detail_query = insert_proc_po_dtl()
		for item in normalized_items:
			detail_params = {
				"po_id": po_id,
				"item_id": item["item_id"],
				"hsn_code": item["hsn_code"],
				"item_make_id": item["item_make_id"],
				"qty": item["qty"],
				"rate": item["rate"],
				"uom_id": item["uom_id"],
				"remarks": item["remarks"],
				"discount_mode": item["discount_mode"],
				"discount_value": item["discount_value"],
				"discount_amount": item["discount_amount"],
				"active": 1,
				"indent_dtl_id": item["indent_dtl_id"],
				"updated_by": updated_by,
				"update_date_time": created_at,
				"state": 1,
			}
			result = db.execute(detail_query, detail_params)
			po_dtl_id = result.lastrowid
			
			# Insert GST if applicable
			if india_gst and item["gst_amounts"]:
				gst_query = insert_po_gst()
				gst_params = {
					"po_dtl_id": po_dtl_id,
					"po_additional_id": None,
					"tax_pct": item["gst_amounts"]["tax_pct"],
					"stax_percentage": item["gst_amounts"]["stax_percentage"],
					"s_tax_amount": item["gst_amounts"]["s_tax_amount"],
					"i_tax_amount": item["gst_amounts"]["i_tax_amount"],
					"i_tax_percentage": item["gst_amounts"]["i_tax_percentage"],
					"c_tax_amount": item["gst_amounts"]["c_tax_amount"],
					"c_tax_percentage": item["gst_amounts"]["c_tax_percentage"],
					"tax_amount": item["gst_amounts"]["tax_amount"],
				}
				db.execute(gst_query, gst_params)
		
		# Insert additional charges
		additional_query = insert_proc_po_additional()
		for addl in normalized_additional:
			addl_params = {
				"po_id": po_id,
				"additional_charges_id": addl["additional_charges_id"],
				"qty": addl["qty"],
				"rate": addl["rate"],
				"net_amount": addl["net_amount"],
				"remarks": addl["remarks"],
			}
			result = db.execute(additional_query, addl_params)
			po_additional_id = result.lastrowid
			
			# Insert GST for additional charges if applicable
			if india_gst and addl["gst_amounts"]:
				gst_query = insert_po_gst()
				gst_params = {
					"po_dtl_id": None,
					"po_additional_id": po_additional_id,
					"tax_pct": addl["gst_amounts"]["tax_pct"],
					"stax_percentage": addl["gst_amounts"]["stax_percentage"],
					"s_tax_amount": addl["gst_amounts"]["s_tax_amount"],
					"i_tax_amount": addl["gst_amounts"]["i_tax_amount"],
					"i_tax_percentage": addl["gst_amounts"]["i_tax_percentage"],
					"c_tax_amount": addl["gst_amounts"]["c_tax_amount"],
					"c_tax_percentage": addl["gst_amounts"]["c_tax_percentage"],
					"tax_amount": addl["gst_amounts"]["tax_amount"],
				}
				db.execute(gst_query, gst_params)
		
		db.commit()
		return {
			"message": "PO created successfully",
			"po_id": po_id,
		}
	except HTTPException as exc:
		db.rollback()
		logger.warning("PO create failed with HTTP error: %s", getattr(exc, "detail", exc))
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Unexpected error while creating PO")
		raise HTTPException(
			status_code=500,
			detail={
				"message": "Failed to create PO",
				"error": str(e),
			},
		)


@router.get("/get_po_by_id")
async def get_po_by_id(
	request: Request,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Return PO details by ID with all line items, additional charges, and GST."""
	try:
		q_po_id = request.query_params.get("po_id")
		q_co_id = request.query_params.get("co_id")
		
		if q_po_id is None:
			raise HTTPException(status_code=400, detail="po_id is required")
		if q_co_id is None:
			raise HTTPException(status_code=400, detail="co_id is required")
		
		try:
			po_id = int(q_po_id)
			co_id = int(q_co_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id or co_id")
		
		# Fetch header data
		header_query = get_po_by_id_query()
		header_params = {"po_id": po_id, "co_id": co_id}
		header_result = db.execute(header_query, header_params).fetchone()
		
		if not header_result:
			raise HTTPException(status_code=404, detail="PO not found or access denied")
		
		header = dict(header_result._mapping)
		
		# Fetch line items
		detail_query = get_po_dtl_by_id_query()
		detail_params = {"po_id": po_id}
		detail_results = db.execute(detail_query, detail_params).fetchall()
		details = [dict(r._mapping) for r in detail_results]
		
		# Fetch additional charges
		additional_query = get_po_additional_by_id_query()
		additional_results = db.execute(additional_query, detail_params).fetchall()
		additional_charges = [dict(r._mapping) for r in additional_results]
		
		# Fetch GST records
		gst_query = get_po_gst_by_id_query()
		gst_results = db.execute(gst_query, detail_params).fetchall()
		gst_records = [dict(r._mapping) for r in gst_results]
		
		# Create GST lookup maps
		gst_by_dtl_id = {g["po_dtl_id"]: g for g in gst_records if g["po_dtl_id"]}
		gst_by_additional_id = {g["po_additional_id"]: g for g in gst_records if g["po_additional_id"]}
		
		# Format dates
		po_date = header.get("po_date")
		if po_date and hasattr(po_date, "date"):
			po_date_str = po_date.date().isoformat()
		elif po_date and hasattr(po_date, "isoformat"):
			po_date_str = po_date.isoformat()
		elif po_date:
			po_date_str = str(po_date)
		else:
			po_date_str = ""
		
		updated_at = header.get("update_date_time")
		updated_at_str = None
		if updated_at:
			if hasattr(updated_at, "isoformat"):
				updated_at_str = updated_at.isoformat()
			else:
				updated_at_str = str(updated_at)
		
		# Format PO number
		raw_po_no = header.get("po_no")
		formatted_po_no = ""
		if raw_po_no is not None and raw_po_no != 0:
			try:
				po_no_int = int(raw_po_no) if raw_po_no else None
				co_prefix = header.get("co_prefix")
				branch_prefix = header.get("branch_prefix")
				formatted_po_no = format_po_no(
					po_no=po_no_int,
					co_prefix=co_prefix,
					branch_prefix=branch_prefix,
					po_date=po_date,
				)
			except Exception as e:
				logger.exception("Error formatting PO number, using raw value")
				formatted_po_no = str(raw_po_no) if raw_po_no else ""
		
		# Get approval_level (only when status_id = 20)
		approval_level = header.get("approval_level")
		if approval_level is not None:
			try:
				approval_level = int(approval_level)
			except (TypeError, ValueError):
				approval_level = None
		else:
			approval_level = None
		
		# Get status_id
		status_id = header.get("status_id")
		branch_id = header.get("branch_id")
		
		# Get menu_id from query params (optional - needed for permission calculation)
		q_menu_id = request.query_params.get("menu_id")
		menu_id = None
		if q_menu_id is not None:
			try:
				menu_id = int(q_menu_id)
			except (TypeError, ValueError):
				menu_id = None
		
		# Calculate permissions if menu_id is provided
		permissions = None
		if menu_id is not None and branch_id is not None and status_id is not None:
			try:
				user_id = int(token_data.get("user_id"))
				permissions = calculate_approval_permissions(
					user_id=user_id,
					menu_id=menu_id,
					branch_id=branch_id,
					status_id=status_id,
					current_approval_level=approval_level,
					db=db,
				)
			except Exception as e:
				logger.exception("Error calculating permissions, continuing without them")
				permissions = None
		
		# Build response
		response = {
			"id": str(header.get("po_id", "")),
			"poNo": formatted_po_no,
			"poDate": po_date_str,
			"branch": str(header.get("branch_id", "")) if header.get("branch_id") else "",
			"supplier": str(header.get("supplier_id", "")) if header.get("supplier_id") else "",
			"supplierBranch": str(header.get("supplier_branch_id", "")) if header.get("supplier_branch_id") else "",
			"billingAddress": str(header.get("billing_branch_id", "")) if header.get("billing_branch_id") else "",
			"billingState": header.get("billing_state_name") if header.get("billing_state_name") else None,
			"shippingAddress": str(header.get("shipping_branch_id", "")) if header.get("shipping_branch_id") else "",
			"shippingState": header.get("shipping_state_name") if header.get("shipping_state_name") else None,
		"project": str(header.get("project_id", "")) if header.get("project_id") else "",
		"creditTerm": header.get("credit_days"),
			"deliveryTimeline": header.get("expected_delivery_days"),
			"contactPerson": header.get("contact_person"),
			"contactNo": header.get("contact_no"),
			"footerNote": header.get("footer_notes"),
			"internalNote": header.get("remarks"),
			"termsConditions": header.get("terms_conditions"),
			"netAmount": float(header.get("net_amount", 0)) if header.get("net_amount") else 0,
			"totalAmount": float(header.get("total_amount", 0)) if header.get("total_amount") else 0,
			"advancePercentage": float(header.get("advance_value", 0)) if header.get("advance_value") else 0,
			"advanceAmount": float(header.get("advance_amount", 0)) if header.get("advance_amount") else 0,
			"status": header.get("status_name") if header.get("status_name") else None,
			"statusId": header.get("status_id"),
			"approvalLevel": approval_level,
			"updatedBy": str(header.get("updated_by", "")) if header.get("updated_by") else None,
			"updatedAt": updated_at_str,
			"lines": [],
			"additionalCharges": [],
		}
		
		# Add permissions if calculated
		if permissions is not None:
			response["permissions"] = permissions
		
		# Map line items
		for detail in details:
			gst = gst_by_dtl_id.get(detail.get("po_dtl_id"))
			line = {
				"id": str(detail.get("po_dtl_id", "")) if detail.get("po_dtl_id") else "",
				"indentNo": detail.get("indent_no") if detail.get("indent_no") else None,
				"department": str(detail.get("dept_id", "")) if detail.get("dept_id") else None,
				"itemGroup": str(detail.get("item_grp_id", "")) if detail.get("item_grp_id") else "",
				"item": str(detail.get("item_id", "")) if detail.get("item_id") else "",
				"itemCode": detail.get("item_code") if detail.get("item_code") else "",
				"itemMake": str(detail.get("item_make_id", "")) if detail.get("item_make_id") else None,
				"quantity": float(detail.get("qty", 0)) if detail.get("qty") is not None else 0,
				"rate": float(detail.get("rate", 0)) if detail.get("rate") is not None else 0,
				"uom": str(detail.get("uom_id", "")) if detail.get("uom_id") else "",
				"discountMode": detail.get("discount_mode"),
				"discountValue": float(detail.get("discount_value", 0)) if detail.get("discount_value") is not None else 0,
				"discountAmount": float(detail.get("discount_amount", 0)) if detail.get("discount_amount") is not None else 0,
				"amount": float(detail.get("qty", 0) * detail.get("rate", 0) - detail.get("discount_amount", 0)) if detail.get("qty") and detail.get("rate") else 0,
				"remarks": detail.get("remarks") if detail.get("remarks") else None,
				"taxPercentage": None,  # Will be calculated from GST if available
			}
			if gst:
				line["taxPercentage"] = float(gst.get("tax_pct", 0)) if gst.get("tax_pct") else None
				line["igst"] = float(gst.get("i_tax_amount", 0)) if gst.get("i_tax_amount") else 0
				line["sgst"] = float(gst.get("s_tax_amount", 0)) if gst.get("s_tax_amount") else 0
				line["cgst"] = float(gst.get("c_tax_amount", 0)) if gst.get("c_tax_amount") else 0
			response["lines"].append(line)
		
		# Map additional charges
		for addl in additional_charges:
			gst = gst_by_additional_id.get(addl.get("po_additional_id"))
			addl_line = {
				"id": str(addl.get("po_additional_id", "")) if addl.get("po_additional_id") else "",
				"additionalChargesId": str(addl.get("additional_charges_id", "")) if addl.get("additional_charges_id") else "",
				"additionalChargesName": addl.get("additional_charges_name") if addl.get("additional_charges_name") else "",
				"qty": int(addl.get("qty", 0)) if addl.get("qty") is not None else 0,
				"rate": float(addl.get("rate", 0)) if addl.get("rate") is not None else 0,
				"netAmount": float(addl.get("net_amount", 0)) if addl.get("net_amount") is not None else 0,
				"remarks": addl.get("remarks") if addl.get("remarks") else None,
			}
			if gst:
				addl_line["igst"] = float(gst.get("i_tax_amount", 0)) if gst.get("i_tax_amount") else 0
				addl_line["sgst"] = float(gst.get("s_tax_amount", 0)) if gst.get("s_tax_amount") else 0
				addl_line["cgst"] = float(gst.get("c_tax_amount", 0)) if gst.get("c_tax_amount") else 0
			response["additionalCharges"].append(addl_line)
		
		return response
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error fetching PO by ID")
		raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_po")
async def update_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Update a purchase order with line items, additional charges, and GST."""
	
	def to_int(value, field_name: str, required: bool = False) -> int | None:
		if value is None or value == "":
			if required:
				raise HTTPException(status_code=400, detail=f"{field_name} is required")
			return None
		try:
			return int(value)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

	def to_float(value, field_name: str, default: float = 0.0) -> float:
		if value is None or value == "":
			return default
		try:
			return float(value)
		except (TypeError, ValueError):
			return default

	try:
		po_id = to_int(payload.get("id"), "id", required=True)
		
		# Verify PO exists
		check_query = text("SELECT po_id, status_id FROM proc_po WHERE po_id = :po_id")
		check_result = db.execute(check_query, {"po_id": po_id}).fetchone()
		if not check_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		existing_status_id = check_result[1] if check_result[1] is not None else None
		
		# Header fields (same as create)
		branch_id = to_int(payload.get("branch"), "branch", required=True)
		supplier_id = to_int(payload.get("supplier"), "supplier", required=True)
		supplier_branch_id = to_int(payload.get("supplier_branch"), "supplier_branch", required=True)
		billing_branch_id = to_int(payload.get("billing_address"), "billing_address", required=True)
		shipping_branch_id = to_int(payload.get("shipping_address"), "shipping_address", required=True)
		project_id = to_int(payload.get("project"), "project", required=True)
		
		date_str = payload.get("date")
		if not date_str:
			raise HTTPException(status_code=400, detail="date is required")
		try:
			po_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
		except ValueError:
			raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

		credit_days = to_int(payload.get("credit_term"), "credit_term")
		expected_delivery_days = to_int(payload.get("delivery_timeline"), "delivery_timeline", required=True)
		contact_person = payload.get("contact_person", "").strip() or None
		contact_no = payload.get("contact_no", "").strip() or None
		footer_notes = payload.get("footer_note", "").strip() or None
		remarks = payload.get("internal_note", "").strip() or None
		terms_conditions = payload.get("terms_conditions", "").strip() or None
		
		advance_value = to_float(payload.get("advance_percentage"), "advance_percentage")
		
		# Get billing and shipping state IDs for GST calculation
		billing_branch_query = text("SELECT state_id FROM branch_mst WHERE branch_id = :branch_id")
		billing_result = db.execute(billing_branch_query, {"branch_id": billing_branch_id}).fetchone()
		billing_state_id = billing_result[0] if billing_result else None
		
		shipping_branch_query = text("SELECT state_id FROM branch_mst WHERE branch_id = :branch_id")
		shipping_result = db.execute(shipping_branch_query, {"branch_id": shipping_branch_id}).fetchone()
		shipping_state_id = shipping_result[0] if shipping_result else None
		
		# Get co_config to check india_gst
		branch_query = text("SELECT co_id FROM branch_mst WHERE branch_id = :branch_id")
		branch_result = db.execute(branch_query, {"branch_id": branch_id}).fetchone()
		co_id = branch_result[0] if branch_result else None
		
		india_gst = False
		if co_id:
			co_config_query = get_co_config_by_id_query(co_id)
			co_config_result = db.execute(co_config_query, {"co_id": co_id}).fetchone()
			if co_config_result:
				co_config = dict(co_config_result._mapping)
				india_gst = bool(co_config.get("india_gst", False))
		
		# Line items
		raw_items = payload.get("items", [])
		if not isinstance(raw_items, list) or len(raw_items) == 0:
			raise HTTPException(status_code=400, detail="At least one item row is required")
		
		# Additional charges
		raw_additional = payload.get("additional_charges", [])
		
		updated_by = to_int(token_data.get("user_id"), "updated_by")
		updated_at = datetime.utcnow()
		
		# Calculate totals (same logic as create)
		net_amount = 0.0
		total_igst = 0.0
		total_sgst = 0.0
		total_cgst = 0.0
		
		# Process line items (same as create)
		normalized_items = []
		for idx, item in enumerate(raw_items, start=1):
			item_id = to_int(item.get("item"), f"items[{idx}].item", required=True)
			qty = to_float(item.get("quantity"), f"items[{idx}].quantity")
			if qty <= 0:
				raise HTTPException(status_code=400, detail=f"items[{idx}].quantity must be greater than zero")
			rate = to_float(item.get("rate"), f"items[{idx}].rate")
			uom_id = to_int(item.get("uom"), f"items[{idx}].uom", required=True)
			item_make_id = to_int(item.get("make"), f"items[{idx}].make")
			indent_dtl_id = to_int(item.get("indent_dtl_id"), f"items[{idx}].indent_dtl_id")
			
			# Get tax percentage from item_mst
			item_query = text("SELECT tax_percentage, hsn_code FROM item_mst WHERE item_id = :item_id")
			item_result = db.execute(item_query, {"item_id": item_id}).fetchone()
			tax_percentage = 0.0
			hsn_code = None
			if item_result:
				tax_percentage = float(item_result[0] or 0.0)
				hsn_code = item_result[1]
			
			# Discount calculation
			discount_mode = to_int(item.get("discount_mode"), f"items[{idx}].discount_mode")
			discount_value = to_float(item.get("discount_value"), f"items[{idx}].discount_value")
			discount_amount = 0.0
			
			base_amount = qty * rate
			if discount_mode == 1:  # Percentage
				if discount_value > 100:
					raise HTTPException(status_code=400, detail=f"items[{idx}].discount_value cannot be greater than 100")
				discount_amount = (base_amount * discount_value) / 100.0
			elif discount_mode == 2:  # Amount
				if discount_value > base_amount:
					raise HTTPException(status_code=400, detail=f"items[{idx}].discount_amount cannot be greater than total amount")
				discount_amount = discount_value
			
			amount = base_amount - discount_amount
			net_amount += amount
			
			# Calculate GST if india_gst is enabled
			if india_gst and billing_state_id and shipping_state_id and tax_percentage > 0:
				gst_amounts = calculate_gst_amounts(amount, tax_percentage, billing_state_id, shipping_state_id)
				total_igst += gst_amounts["i_tax_amount"]
				total_sgst += gst_amounts["s_tax_amount"]
				total_cgst += gst_amounts["c_tax_amount"]
			else:
				gst_amounts = None
			
			remarks_raw = item.get("remarks", "").strip() or None
			
			normalized_items.append({
				"item_id": item_id,
				"qty": qty,
				"rate": rate,
				"uom_id": uom_id,
				"item_make_id": item_make_id,
				"indent_dtl_id": indent_dtl_id,
				"hsn_code": hsn_code,
				"discount_mode": discount_mode,
				"discount_value": discount_value,
				"discount_amount": discount_amount,
				"amount": amount,
				"remarks": remarks_raw,
				"tax_percentage": tax_percentage,
				"gst_amounts": gst_amounts,
			})
		
		# Process additional charges (same as create)
		normalized_additional = []
		for idx, addl in enumerate(raw_additional, start=1):
			additional_charges_id = to_int(addl.get("additional_charges_id"), f"additional_charges[{idx}].additional_charges_id", required=True)
			qty = to_int(addl.get("qty"), f"additional_charges[{idx}].qty", required=True)
			rate = to_float(addl.get("rate"), f"additional_charges[{idx}].rate")
			net_amt = qty * rate
			net_amount += net_amt
			
			remarks_raw = addl.get("remarks", "").strip() or None
			
			# GST for additional charges (if applicable)
			gst_amounts = None
			if india_gst and billing_state_id and shipping_state_id:
				addl_query = text("SELECT default_value FROM additional_charges_master WHERE additional_charges_id = :id")
				addl_result = db.execute(addl_query, {"id": additional_charges_id}).fetchone()
				tax_pct = float(addl_result[0] or 0.0) if addl_result else 0.0
				if tax_pct > 0:
					gst_amounts = calculate_gst_amounts(net_amt, tax_pct, billing_state_id, shipping_state_id)
					total_igst += gst_amounts["i_tax_amount"]
					total_sgst += gst_amounts["s_tax_amount"]
					total_cgst += gst_amounts["c_tax_amount"]
			
			normalized_additional.append({
				"additional_charges_id": additional_charges_id,
				"qty": qty,
				"rate": rate,
				"net_amount": net_amt,
				"remarks": remarks_raw,
				"gst_amounts": gst_amounts,
			})
		
		total_amount = net_amount + total_igst + total_sgst + total_cgst
		advance_amount = (net_amount * advance_value) / 100.0 if advance_value > 0 else 0.0
		
		# Get existing po_no to preserve it
		existing_query = text("SELECT po_no FROM proc_po WHERE po_id = :po_id")
		existing_result = db.execute(existing_query, {"po_id": po_id}).fetchone()
		existing_po_no = existing_result[0] if existing_result and existing_result[0] else None
		
		# Update PO header
		update_header_query = update_proc_po()
		header_params = {
			"po_id": po_id,
			"credit_days": credit_days,
			"delivery_instructions": None,
			"expected_delivery_days": expected_delivery_days,
			"footer_notes": footer_notes,
			"po_date": po_date,
			"remarks": remarks,
			"delivery_mode": None,
			"terms_conditions": terms_conditions,
			"branch_id": branch_id,
			"project_id": project_id,
			"supplier_id": supplier_id,
			"supplier_branch_id": supplier_branch_id,
			"billing_branch_id": billing_branch_id,
			"shipping_branch_id": shipping_branch_id,
			"total_amount": total_amount,
			"net_amount": net_amount,
			"advance_type": 1 if advance_value > 0 else None,
			"advance_value": advance_value,
			"advance_amount": advance_amount,
			"contact_no": contact_no,
			"contact_person": contact_person,
			"updated_by": updated_by,
			"update_date_time": updated_at,
			"po_no": existing_po_no,
			"status_id": existing_status_id,
			"approval_level": None,
		}
		
		db.execute(update_header_query, header_params)
		
		# Soft delete existing line items
		delete_detail_query = delete_proc_po_dtl()
		db.execute(delete_detail_query, {
			"po_id": po_id,
			"updated_by": updated_by,
			"update_date_time": updated_at,
		})
		
		# Delete existing GST records
		delete_gst_query = delete_po_gst()
		db.execute(delete_gst_query, {"po_id": po_id})
		
		# Delete existing additional charges
		delete_additional_query = delete_proc_po_additional()
		db.execute(delete_additional_query, {"po_id": po_id})
		
		# Insert new line items (same as create)
		detail_query = insert_proc_po_dtl()
		for item in normalized_items:
			detail_params = {
				"po_id": po_id,
				"item_id": item["item_id"],
				"hsn_code": item["hsn_code"],
				"item_make_id": item["item_make_id"],
				"qty": item["qty"],
				"rate": item["rate"],
				"uom_id": item["uom_id"],
				"remarks": item["remarks"],
				"discount_mode": item["discount_mode"],
				"discount_value": item["discount_value"],
				"discount_amount": item["discount_amount"],
				"active": 1,
				"indent_dtl_id": item["indent_dtl_id"],
				"updated_by": updated_by,
				"update_date_time": updated_at,
				"state": 1,
			}
			result = db.execute(detail_query, detail_params)
			po_dtl_id = result.lastrowid
			
			# Insert GST if applicable
			if india_gst and item["gst_amounts"]:
				gst_query = insert_po_gst()
				gst_params = {
					"po_dtl_id": po_dtl_id,
					"po_additional_id": None,
					"tax_pct": item["gst_amounts"]["tax_pct"],
					"stax_percentage": item["gst_amounts"]["stax_percentage"],
					"s_tax_amount": item["gst_amounts"]["s_tax_amount"],
					"i_tax_amount": item["gst_amounts"]["i_tax_amount"],
					"i_tax_percentage": item["gst_amounts"]["i_tax_percentage"],
					"c_tax_amount": item["gst_amounts"]["c_tax_amount"],
					"c_tax_percentage": item["gst_amounts"]["c_tax_percentage"],
					"tax_amount": item["gst_amounts"]["tax_amount"],
				}
				db.execute(gst_query, gst_params)
		
		# Insert new additional charges (same as create)
		additional_query = insert_proc_po_additional()
		for addl in normalized_additional:
			addl_params = {
				"po_id": po_id,
				"additional_charges_id": addl["additional_charges_id"],
				"qty": addl["qty"],
				"rate": addl["rate"],
				"net_amount": addl["net_amount"],
				"remarks": addl["remarks"],
			}
			result = db.execute(additional_query, addl_params)
			po_additional_id = result.lastrowid
			
			# Insert GST for additional charges if applicable
			if india_gst and addl["gst_amounts"]:
				gst_query = insert_po_gst()
				gst_params = {
					"po_dtl_id": None,
					"po_additional_id": po_additional_id,
					"tax_pct": addl["gst_amounts"]["tax_pct"],
					"stax_percentage": addl["gst_amounts"]["stax_percentage"],
					"s_tax_amount": addl["gst_amounts"]["s_tax_amount"],
					"i_tax_amount": addl["gst_amounts"]["i_tax_amount"],
					"i_tax_percentage": addl["gst_amounts"]["i_tax_percentage"],
					"c_tax_amount": addl["gst_amounts"]["c_tax_amount"],
					"c_tax_percentage": addl["gst_amounts"]["c_tax_percentage"],
					"tax_amount": addl["gst_amounts"]["tax_amount"],
				}
				db.execute(gst_query, gst_params)
		
		db.commit()
		return {
			"message": "PO updated successfully",
			"po_id": po_id,
		}
	except HTTPException as exc:
		db.rollback()
		logger.warning("PO update failed with HTTP error: %s", getattr(exc, "detail", exc))
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Unexpected error while updating PO")
		raise HTTPException(
			status_code=500,
			detail=str(e),
		)


# ==================== APPROVAL FUNCTIONS ====================

def process_po_approval_with_value(
	po_id: int,
	user_id: int,
	menu_id: int,
	document_amount: float,
	db: Session,
) -> dict:
	"""Process approval for PO with monetary value."""
	try:
		# Get PO details
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		current_status_id = po.get("status_id")
		current_approval_level = po.get("approval_level") or 0
		branch_id = po.get("branch_id")
		
		# If status is Open (1), first transition to Pending Approval (20) with level 1
		if current_status_id == 1:
			updated_at = datetime.utcnow()
			update_query = update_po_status()
			db.execute(
				update_query,
				{
					"po_id": po_id,
					"status_id": 20,  # Pending Approval
					"approval_level": 1,  # Start at level 1
					"updated_by": user_id,
					"update_date_time": updated_at,
					"po_no": None,  # Don't update po_no
				}
			)
			db.commit()
			current_status_id = 20
			current_approval_level = 1
			po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
			if po_result:
				po = dict(po_result._mapping)
		
		# Verify current status is Pending Approval (20)
		if current_status_id != 20:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot approve PO with status_id {current_status_id}. Expected status 20 (Pending Approval) or 1 (Open)."
			)
		
		# Get user's approval level and limits
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
		max_amount_single = user_data.get("max_amount_single")
		
		# Check if user can approve at current level
		if user_approval_level != current_approval_level:
			raise HTTPException(
				status_code=403,
				detail=f"User approval level ({user_approval_level}) does not match current PO approval level ({current_approval_level})."
			)
		
		# Check amount limits
		if max_amount_single is not None and document_amount > max_amount_single:
			raise HTTPException(
				status_code=403,
				detail=f"Document amount ({document_amount}) exceeds maximum single approval amount ({max_amount_single})."
			)
		
		# Get max approval level
		max_level_query = get_max_approval_level()
		max_level_result = db.execute(
			max_level_query,
			{"menu_id": menu_id, "branch_id": branch_id}
		).fetchone()
		
		max_approval_level = dict(max_level_result._mapping).get("max_level") if max_level_result else user_approval_level
		
		# Determine next status
		if user_approval_level >= max_approval_level:
			# Final level - approve
			new_status_id = 3  # Approved
			new_approval_level = user_approval_level
			message = "PO approved (final level)."
		else:
			# Move to next level
			new_status_id = 20  # Still Pending Approval
			new_approval_level = current_approval_level + 1
			message = f"PO moved to approval level {new_approval_level}."
		
		# Update PO status
		updated_at = datetime.utcnow()
		update_query = update_po_status()
		db.execute(
			update_query,
			{
				"po_id": po_id,
				"status_id": new_status_id,
				"approval_level": new_approval_level,
				"updated_by": user_id,
				"update_date_time": updated_at,
				"po_no": None,  # Don't update po_no
			}
		)
		db.commit()
		
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
		logger.exception("Error processing PO approval with value")
		raise HTTPException(status_code=500, detail=str(e))


# ==================== APPROVAL API ENDPOINTS ====================

@router.post("/approve_po")
async def approve_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Approve a PO (with value check - PO has monetary amounts)."""
	try:
		po_id = payload.get("po_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not po_id:
			raise HTTPException(status_code=400, detail="po_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			po_id = int(po_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get PO amount
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		document_amount = float(po.get("total_amount", 0))
		
		# Process approval with value checks
		result = process_po_approval_with_value(
			po_id=po_id,
			user_id=user_id,
			menu_id=menu_id,
			document_amount=document_amount,
			db=db,
		)
		
		return result
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("Error approving PO")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/open_po")
async def open_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Open a PO (change status from 21 Drafted to 1 Open). Generates document number if not already generated."""
	try:
		po_id = payload.get("po_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not po_id:
			raise HTTPException(status_code=400, detail="po_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			po_id = int(po_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get PO details
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		current_status_id = po.get("status_id")
		current_po_no = po.get("po_no")
		po_date = po.get("po_date")
		
		# Verify current status is Drafted (21)
		if current_status_id != 21:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot open PO with status_id {current_status_id}. Expected status 21 (Drafted)."
			)
		
		# Generate po_no if not already set
		new_po_no = None
		if not po_date:
			raise HTTPException(
				status_code=400,
				detail="PO date is required to generate PO number."
			)
		
		# Only generate if po_no is NULL or 0
		if current_po_no is None or current_po_no == 0:
			# Calculate financial year boundaries (same as indent)
			if hasattr(po_date, "year") and hasattr(po_date, "month"):
				year = po_date.year
				month = po_date.month
			elif hasattr(po_date, "date"):
				date_obj = po_date.date()
				year = date_obj.year
				month = date_obj.month
			else:
				try:
					if isinstance(po_date, str):
						date_obj = datetime.strptime(po_date, "%Y-%m-%d").date()
					else:
						date_obj = datetime.fromisoformat(str(po_date)).date()
					year = date_obj.year
					month = date_obj.month
				except Exception:
					raise HTTPException(
						status_code=400,
						detail=f"Invalid po_date format: {po_date}"
					)
			
			# Calculate financial year boundaries
			if month >= 4:
				fy_start_year = year
				fy_end_year = year + 1
			else:
				fy_start_year = year - 1
				fy_end_year = year
			
			fy_start_date = datetime(fy_start_year, 4, 1).date()
			fy_end_date = datetime(fy_end_year, 3, 31).date()
			
			# Get max po_no for this branch and financial year
			max_query = get_max_po_no_for_branch_fy()
			max_result = db.execute(
				max_query,
				{
					"branch_id": branch_id,
					"fy_start_date": fy_start_date,
					"fy_end_date": fy_end_date,
				}
			).fetchone()
			
			if max_result:
				max_po_no = dict(max_result._mapping).get("max_po_no") or 0
				new_po_no = max_po_no + 1
			else:
				new_po_no = 1
		
		# Update status to Open (1) and set po_no if generated
		updated_at = datetime.utcnow()
		update_query = update_po_status()
		update_params = {
			"po_id": po_id,
			"status_id": 1,  # Open
			"approval_level": None,  # Reset approval level
			"updated_by": user_id,
			"update_date_time": updated_at,
			"po_no": new_po_no if new_po_no is not None else None,  # Pass None to keep existing, or new value
		}
		
		db.execute(update_query, update_params)
		db.commit()
		
		# Return the po_no that was set (either newly generated or existing)
		final_po_no = new_po_no if new_po_no is not None else current_po_no
		
		return {
			"status": "success",
			"new_status_id": 1,
			"message": "PO opened successfully.",
			"po_no": final_po_no,
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error opening PO")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel_draft_po")
async def cancel_draft_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Cancel a draft PO (change status from 21 Drafted to 6 Cancelled)."""
	try:
		po_id = payload.get("po_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not po_id:
			raise HTTPException(status_code=400, detail="po_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			po_id = int(po_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get PO details
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		current_status_id = po.get("status_id")
		
		# Verify current status is Drafted (21)
		if current_status_id != 21:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot cancel PO with status_id {current_status_id}. Expected status 21 (Drafted)."
			)
		
		# Update status to Cancelled (6)
		updated_at = datetime.utcnow()
		update_query = update_po_status()
		db.execute(
			update_query,
			{
				"po_id": po_id,
				"status_id": 6,  # Cancelled
				"approval_level": None,
				"updated_by": user_id,
				"update_date_time": updated_at,
				"po_no": None,  # Don't update po_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": 6,
			"message": "Draft cancelled successfully.",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error cancelling draft PO")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/reopen_po")
async def reopen_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Reopen a PO (change status from 6 Cancelled or 4 Rejected back to 1 Open or 21 Drafted)."""
	try:
		po_id = payload.get("po_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not po_id:
			raise HTTPException(status_code=400, detail="po_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			po_id = int(po_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get PO details
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		current_status_id = po.get("status_id")
		
		# Determine target status based on current status
		if current_status_id == 6:  # Cancelled
			new_status_id = 21  # Back to Drafted
		elif current_status_id == 4:  # Rejected
			new_status_id = 1  # Back to Open
		else:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot reopen PO with status_id {current_status_id}. Only Cancelled (6) or Rejected (4) can be reopened."
			)
		
		# Update status
		updated_at = datetime.utcnow()
		update_query = update_po_status()
		db.execute(
			update_query,
			{
				"po_id": po_id,
				"status_id": new_status_id,
				"approval_level": None,
				"updated_by": user_id,
				"update_date_time": updated_at,
				"po_no": None,  # Don't update po_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": new_status_id,
			"message": f"PO reopened successfully (status: {new_status_id}).",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error reopening PO")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/send_po_for_approval")
async def send_po_for_approval(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Send PO for approval (change status from 1 Open to 20 Pending Approval, set approval_level to 1)."""
	try:
		po_id = payload.get("po_id")
		branch_id = payload.get("branch_id")
		menu_id = payload.get("menu_id")
		
		if not po_id:
			raise HTTPException(status_code=400, detail="po_id is required")
		if not branch_id:
			raise HTTPException(status_code=400, detail="branch_id is required")
		if not menu_id:
			raise HTTPException(status_code=400, detail="menu_id is required")
		
		try:
			po_id = int(po_id)
			branch_id = int(branch_id)
			menu_id = int(menu_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id, branch_id, or menu_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get PO details
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		current_status_id = po.get("status_id")
		
		# Verify current status is Open (1)
		if current_status_id != 1:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot send for approval PO with status_id {current_status_id}. Expected status 1 (Open)."
			)
		
		# Update status to Pending Approval (20) with level 1
		updated_at = datetime.utcnow()
		update_query = update_po_status()
		db.execute(
			update_query,
			{
				"po_id": po_id,
				"status_id": 20,  # Pending Approval
				"approval_level": 1,  # Start at level 1
				"updated_by": user_id,
				"update_date_time": updated_at,
				"po_no": None,  # Don't update po_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": 20,
			"new_approval_level": 1,
			"message": "PO sent for approval successfully.",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error sending PO for approval")
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject_po")
async def reject_po(
	payload: dict,
	db: Session = Depends(get_tenant_db),
	token_data: dict = Depends(get_current_user_with_refresh),
):
	"""Reject a PO (change status from 20 Pending Approval to 4 Rejected)."""
	try:
		po_id = payload.get("po_id")
		co_id = payload.get("co_id")
		reason = payload.get("reason", "")
		
		if not po_id:
			raise HTTPException(status_code=400, detail="po_id is required")
		if not co_id:
			raise HTTPException(status_code=400, detail="co_id is required")
		
		try:
			po_id = int(po_id)
			co_id = int(co_id)
		except (TypeError, ValueError):
			raise HTTPException(status_code=400, detail="Invalid po_id or co_id")
		
		user_id = int(token_data.get("user_id"))
		
		# Get PO details
		po_query = get_po_with_approval_info()
		po_result = db.execute(po_query, {"po_id": po_id}).fetchone()
		if not po_result:
			raise HTTPException(status_code=404, detail="PO not found")
		
		po = dict(po_result._mapping)
		current_status_id = po.get("status_id")
		
		# Verify current status is Pending Approval (20)
		if current_status_id != 20:
			raise HTTPException(
				status_code=400,
				detail=f"Cannot reject PO with status_id {current_status_id}. Expected status 20 (Pending Approval)."
			)
		
		# Update status to Rejected (4)
		updated_at = datetime.utcnow()
		update_query = update_po_status()
		db.execute(
			update_query,
			{
				"po_id": po_id,
				"status_id": 4,  # Rejected
				"approval_level": None,
				"updated_by": user_id,
				"update_date_time": updated_at,
				"po_no": None,  # Don't update po_no
			}
		)
		db.commit()
		
		return {
			"status": "success",
			"new_status_id": 4,
			"message": "PO rejected successfully.",
		}
	except HTTPException:
		db.rollback()
		raise
	except Exception as e:
		db.rollback()
		logger.exception("Error rejecting PO")
		raise HTTPException(status_code=500, detail=str(e))

