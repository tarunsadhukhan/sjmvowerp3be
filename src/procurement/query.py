from sqlalchemy.sql import text
from sqlalchemy.sql import bindparam
from sqlalchemy.sql.elements import TextClause

def get_expense_types():
    sql = f"""select expense_type_id, etm.expense_type_name  
    from expense_type_mst etm where etm.active =1 ;"""
    query = text(sql)
    return query

def get_project(branch_id: int = None):
    sql = f"""select pm.prj_name , pm.project_id 
    from project_mst pm where pm.branch_id = :branch_id and pm.active =1 ;"""
    query = text(sql)
    return query

def get_make(co_id: int = None):
    sql = f"""select igm.item_grp_id, im.item_make_id , im.item_make_name   from item_grp_mst igm
right join item_make im on im.item_grp_id = igm.item_grp_id 
where igm.co_id = :co_id;"""
    query = text(sql)
    return query

def get_item_by_group_id_purchaseable(item_group_id: int):
    sql = f"""Select im.item_id,
im.item_code , im.item_name , im.uom_id , um.uom_name
from item_mst im 
left join uom_mst um on um.uom_id= im.uom_id
where im.item_grp_id = :item_group_id and im.active =1 and im.purchaseable =1;"""
    query = text(sql)
    return query

def get_item_make_by_group_id(item_group_id: int):
    sql = f"""select im.item_make_id, im.item_make_name 
    from item_make im 
    where im.item_grp_id = :item_group_id;"""
    query = text(sql)
    return query

def get_item_uom_by_group_id(item_group_id: int):
    sql = f"""SELECT uimm.item_id, uimm.map_to_id, um.uom_name
FROM uom_item_map_mst AS uimm
JOIN item_mst AS im
  ON im.item_id = uimm.item_id
 AND im.item_grp_id = :item_group_id
 AND im.purchaseable = 1
 AND im.active = 1
LEFT JOIN uom_mst AS um
  ON um.uom_id = uimm.map_to_id;"""
    query = text(sql)
    return query


def insert_proc_indent():
    sql = """INSERT INTO proc_indent (
    indent_date,
    indent_no,
    active,
    indent_type_id,
    remarks,
    branch_id,
    expense_type_id,
    project_id,
    updated_by,
    updated_date_time,
    status_id,
    indent_title
) VALUES (
    :indent_date,
    :indent_no,
    :active,
    :indent_type_id,
    :remarks,
    :branch_id,
    :expense_type_id,
    :project_id,
    :updated_by,
    :updated_date_time,
    :status_id,
    :indent_title
);"""
    return text(sql)


def insert_proc_indent_detail():
    sql = """INSERT INTO proc_indent_dtl (
    indent_id,
    required_by_days,
    active,
    item_id,
    qty,
    uom_id,
    remarks,
    updated_by,
    updated_date_time,
    item_make_id,
    dept_id
) VALUES (
    :indent_id,
    :required_by_days,
    :active,
    :item_id,
    :qty,
    :uom_id,
    :remarks,
    :updated_by,
    :updated_date_time,
    :item_make_id,
    :dept_id
);"""
    return text(sql)


def get_indent_table_query():
        sql = """SELECT
        pi.indent_id,
        pi.indent_no,
        pi.indent_date,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        etm.expense_type_name,
        sm.status_name
FROM proc_indent AS pi
LEFT JOIN branch_mst AS bm ON bm.branch_id = pi.branch_id
LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
LEFT JOIN expense_type_mst AS etm ON etm.expense_type_id = pi.expense_type_id
LEFT JOIN status_mst AS sm ON sm.status_id = pi.status_id
WHERE (:co_id IS NULL OR bm.co_id = :co_id)
    AND (
                :search_like IS NULL
                OR pi.indent_no LIKE :search_like
                OR bm.branch_name LIKE :search_like
                OR etm.expense_type_name LIKE :search_like
            )
ORDER BY pi.indent_date DESC, pi.indent_id DESC
LIMIT :limit OFFSET :offset;"""
        return text(sql)


def get_all_approved_indents_query():
    """Get all approved indents (status_id = 3) for dropdown selection."""
    sql = """SELECT
        pi.indent_id,
        pi.indent_no,
        pi.indent_date,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        etm.expense_type_name
    FROM proc_indent AS pi
    LEFT JOIN branch_mst AS bm ON bm.branch_id = pi.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN expense_type_mst AS etm ON etm.expense_type_id = pi.expense_type_id
    WHERE pi.status_id = 3
        AND (:branch_id IS NULL OR pi.branch_id = :branch_id)
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND bm.active = 1
    ORDER BY pi.indent_date DESC, pi.indent_id DESC;"""
    return text(sql)


def get_indent_table_count_query():
        sql = """SELECT COUNT(1) AS total
FROM proc_indent AS pi
LEFT JOIN branch_mst AS bm ON bm.branch_id = pi.branch_id
LEFT JOIN expense_type_mst AS etm ON etm.expense_type_id = pi.expense_type_id
WHERE (:co_id IS NULL OR bm.co_id = :co_id)
    AND (
                :search_like IS NULL
                OR pi.indent_no LIKE :search_like
                OR bm.branch_name LIKE :search_like
                OR etm.expense_type_name LIKE :search_like
            );"""
        return text(sql)


def get_po_table_query():
    sql = """SELECT
        pp.po_id,
        pp.po_no,
        pp.po_date,
        pm.supp_name,
        pp.total_amount AS po_value,
        bm.branch_name,
        prjm.prj_name AS project_name,
        sm.status_name,
        bm.co_id
    FROM proc_po AS pp
    LEFT JOIN branch_mst AS bm ON bm.branch_id = pp.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = pp.supplier_id
    LEFT JOIN project_mst AS prjm ON prjm.project_id = pp.project_id
    LEFT JOIN status_mst AS sm ON sm.status_id = pp.status_id
    WHERE (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR pp.po_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
        )
    ORDER BY pp.po_date DESC, pp.po_id DESC
    LIMIT :limit OFFSET :offset;"""
    return text(sql)


def get_po_table_count_query():
    sql = """SELECT COUNT(1) AS total
    FROM proc_po AS pp
    LEFT JOIN branch_mst AS bm ON bm.branch_id = pp.branch_id
    LEFT JOIN party_mst AS pm ON pm.party_id = pp.supplier_id
    WHERE (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR pp.po_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
        );"""
    return text(sql)


def get_indent_by_id_query():
    sql = """SELECT
        pi.indent_id,
        pi.indent_no,
        pi.indent_date,
        pi.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        pi.indent_type_id,
        pi.expense_type_id,
        etm.expense_type_name,
        pi.project_id,
        pm.prj_name AS project_name,
        pi.indent_title,
        pi.remarks,
        pi.status_id,
        sm.status_name,
        pi.updated_by,
        pi.updated_date_time,
        CASE 
            WHEN pi.status_id = 20 THEN pi.approval_level 
            ELSE NULL 
        END AS approval_level
    FROM proc_indent AS pi
    LEFT JOIN branch_mst AS bm ON bm.branch_id = pi.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN expense_type_mst AS etm ON etm.expense_type_id = pi.expense_type_id
    LEFT JOIN project_mst AS pm ON pm.project_id = pi.project_id
    LEFT JOIN status_mst AS sm ON sm.status_id = pi.status_id
    WHERE pi.indent_id = :indent_id
        AND (:co_id IS NULL OR bm.co_id = :co_id);"""
    return text(sql)


def get_indent_detail_by_id_query():
    sql = """SELECT
        pid.indent_dtl_id,
        pid.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code,
        igm.item_grp_name,
        pid.qty,
        pid.uom_id,
        um.uom_name,
        pid.item_make_id,
        imk.item_make_name,
        pid.dept_id,
        dm.dept_desc AS dept_name,
        pid.remarks
    FROM proc_indent_dtl AS pid
    LEFT JOIN item_mst AS im ON im.item_id = pid.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN uom_mst AS um ON um.uom_id = pid.uom_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = pid.item_make_id
    LEFT JOIN dept_mst AS dm ON dm.dept_id = pid.dept_id
    WHERE pid.indent_id = :indent_id
        AND pid.active = 1
    ORDER BY pid.indent_dtl_id;"""
    return text(sql)


def update_proc_indent():
    sql = """UPDATE proc_indent SET
        indent_date = :indent_date,
        branch_id = :branch_id,
        indent_type_id = :indent_type_id,
        expense_type_id = :expense_type_id,
        project_id = :project_id,
        indent_title = :indent_title,
        remarks = :remarks,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        indent_no = COALESCE(:indent_no, indent_no),
        active = COALESCE(:active, active),
        status_id = COALESCE(:status_id, status_id)
    WHERE indent_id = :indent_id;"""
    return text(sql)


def delete_proc_indent_detail():
    sql = """UPDATE proc_indent_dtl SET
        active = 0,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time
    WHERE indent_id = :indent_id;"""
    return text(sql)


def get_approval_flow_by_menu_branch():
    """Get approval flow details for a specific menu and branch.
    Returns all approval levels configured for the menu/branch combination.
    """
    sql = """SELECT
        am.approval_mst_id,
        am.menu_id,
        am.user_id,
        am.branch_id,
        am.approval_level,
        am.max_amount_single,
        am.day_max_amount,
        am.month_max_amount,
        um.user_name,
        mm.menu_name
    FROM approval_mst am
    LEFT JOIN user_mst um ON um.user_id = am.user_id
    LEFT JOIN menu_mst mm ON mm.menu_id = am.menu_id
    WHERE am.menu_id = :menu_id
        AND am.branch_id = :branch_id
    ORDER BY am.approval_level ASC;"""
    return text(sql)


def get_user_approval_level():
    """Get the approval level of a specific user for a menu and branch."""
    sql = """SELECT
        am.approval_level,
        am.max_amount_single,
        am.day_max_amount,
        am.month_max_amount
    FROM approval_mst am
    WHERE am.menu_id = :menu_id
        AND am.branch_id = :branch_id
        AND am.user_id = :user_id
    LIMIT 1;"""
    return text(sql)


def get_max_approval_level():
    """Get the maximum approval level configured for a menu and branch."""
    sql = """SELECT MAX(am.approval_level) as max_level
    FROM approval_mst am
    WHERE am.menu_id = :menu_id
        AND am.branch_id = :branch_id;"""
    return text(sql)


def get_user_consumed_amounts():
    """Get amounts already consumed by user for the day and month.
    This aggregates amounts from documents approved by the user today/this month.
    Note: This needs to be customized based on which table stores the document amounts.
    """
    sql = """SELECT
        COALESCE(SUM(CASE WHEN DATE(pi.updated_date_time) = CURDATE() THEN 1 ELSE 0 END), 0) as day_count,
        COALESCE(SUM(CASE WHEN YEAR(pi.updated_date_time) = YEAR(CURDATE()) 
                          AND MONTH(pi.updated_date_time) = MONTH(CURDATE()) THEN 1 ELSE 0 END), 0) as month_count
    FROM proc_indent pi
    WHERE pi.approval_level = :approval_level
        AND pi.status_id = 3
        AND EXISTS (
            SELECT 1 FROM approval_mst am
            WHERE am.menu_id = :menu_id
                AND am.branch_id = :branch_id
                AND am.user_id = :user_id
                AND am.approval_level = :approval_level
        );"""
    return text(sql)


def check_approval_mst_exists():
    """Check if approval_mst has any entries for a menu and branch."""
    sql = """SELECT COUNT(*) as count
    FROM approval_mst am
    WHERE am.menu_id = :menu_id
        AND am.branch_id = :branch_id;"""
    return text(sql)


def get_user_edit_access():
    """Check if user has edit access (access_type_id >= 4) for a menu and branch."""
    sql = """SELECT 
        MAX(CASE WHEN ccm.access_type = 1 THEN 1 ELSE rmm.access_type_id END) as max_access_type_id
    FROM user_role_map urm
    LEFT JOIN role_menu_map rmm ON rmm.role_id = urm.role_id
    LEFT JOIN menu_mst mm ON mm.menu_id = rmm.menu_id AND mm.active = 1
    LEFT JOIN control_co_module ccm ON urm.co_id = ccm.co_id AND ccm.module_id = mm.module_mst_id
    WHERE urm.user_id = :user_id
        AND urm.branch_id = :branch_id
        AND rmm.menu_id = :menu_id
        AND IFNULL(ccm.access_type, 0) NOT IN (2);"""
    return text(sql)


def update_indent_status():
    """Update indent status and approval level. Optionally update indent_no."""
    sql = """UPDATE proc_indent SET
        status_id = :status_id,
        approval_level = :approval_level,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        indent_no = CASE 
            WHEN :indent_no IS NOT NULL THEN :indent_no 
            ELSE indent_no 
        END
    WHERE indent_id = :indent_id;"""
    return text(sql)


def get_max_indent_no_for_branch_fy():
    """Get the maximum indent_no for a branch within a financial year.
    
    Financial year: April 1 to March 31
    - If month >= 4 (April-December): FY = year-04-01 to (year+1)-03-31
    - If month < 4 (January-March): FY = (year-1)-04-01 to year-03-31
    """
    sql = """SELECT COALESCE(MAX(pi.indent_no), 0) as max_indent_no
    FROM proc_indent pi
    WHERE pi.branch_id = :branch_id
        AND pi.indent_date >= :fy_start_date
        AND pi.indent_date <= :fy_end_date
        AND pi.indent_no IS NOT NULL;"""
    return text(sql)


def get_indent_with_approval_info():
    """Get indent details including approval level and status."""
    sql = """SELECT
        pi.indent_id,
        pi.status_id,
        pi.approval_level,
        pi.branch_id,
        pi.indent_date,
        pi.indent_no,
        bm.co_id
    FROM proc_indent pi
    LEFT JOIN branch_mst bm ON bm.branch_id = pi.branch_id
    WHERE pi.indent_id = :indent_id;"""
    return text(sql)


# ==================== PO QUERY FUNCTIONS ====================

def get_suppliers_with_party_type_1(co_id: int = None):
    """Get suppliers where party_type_id contains 1 with full details."""
    sql = """SELECT 
        pm.party_id,
        pm.supp_name AS supplier_name,
        pm.supp_code AS supplier_code,
        pm.supp_contact_person,
        pm.supp_contact_designation,
        pm.supp_email_id,
        pm.phone_no,
        pm.party_pan_no,
        pm.country_id,
        cm.country,
        pm.msme_certified,
        pm.entity_type_id,
        etm.entity_type_name
    FROM party_mst pm
    LEFT JOIN country_mst cm ON cm.country_id = pm.country_id
    LEFT JOIN entity_type_mst etm ON etm.entity_type_id = pm.entity_type_id
    WHERE FIND_IN_SET("1", REPLACE(REPLACE(pm.party_type_id, "{", ""), "}", "")) > 0
        AND (:co_id IS NULL OR pm.co_id = :co_id)
        AND pm.active = 1
    ORDER BY pm.supp_name;"""
    return text(sql)


def get_supplier_branches(party_id: int):
    """Get branch addresses for a supplier with full address details."""
    sql = """SELECT 
        pbm.party_mst_branch_id,
        pbm.party_id,
        pbm.address AS branch_address1,
        pbm.address_additional AS branch_address2,
        pbm.city_id,
        cim.city_name,
        cim.state_id,
        sm.state AS state,
        pbm.zip_code,
        pbm.contact_person,
        pbm.contact_no,
        pbm.gst_no
    FROM party_branch_mst pbm
    LEFT JOIN city_mst cim ON cim.city_id = pbm.city_id
    LEFT JOIN state_mst sm ON sm.state_id = cim.state_id
    WHERE pbm.party_id = :party_id
        AND pbm.active = 1
    ORDER BY pbm.party_mst_branch_id;"""
    return text(sql)


def get_company_branch_addresses(co_id: int = None, branch_id: int = None):
    """Get branch addresses for company branches with state information. If branch_id is provided, filter by that branch."""
    sql = """SELECT 
        bm.branch_id,
        bm.branch_name,
        bm.branch_address1,
        bm.branch_address2,
        bm.state_id,
        sm.state AS state_name,
        bm.branch_zipcode,
        bm.co_id
    FROM branch_mst bm
    LEFT JOIN state_mst sm ON sm.state_id = bm.state_id
    WHERE (:co_id IS NULL OR bm.co_id = :co_id)
        AND (:branch_id IS NULL OR bm.branch_id = :branch_id)
        AND bm.active = 1
    ORDER BY bm.branch_name;"""
    return text(sql)


def get_indent_line_items_for_po(indent_id: int):
    """Get line items for an indent to be used in PO creation popup."""
    sql = """SELECT
        pid.indent_dtl_id,
        pi.indent_id,
        pi.indent_no,
        pid.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code,
        igm.item_grp_name,
        pid.qty,
        pid.uom_id,
        um.uom_name,
        pid.item_make_id,
        imk.item_make_name,
        pid.dept_id,
        dm.dept_desc AS dept_name,
        im.tax_percentage,
        pid.remarks
    FROM proc_indent_dtl AS pid
    LEFT JOIN proc_indent AS pi ON pi.indent_id = pid.indent_id
    LEFT JOIN item_mst AS im ON im.item_id = pid.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN uom_mst AS um ON um.uom_id = pid.uom_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = pid.item_make_id
    LEFT JOIN dept_mst AS dm ON dm.dept_id = pid.dept_id
    WHERE pid.indent_id = :indent_id
        AND pid.active = 1
    ORDER BY pid.indent_dtl_id;"""
    return text(sql)


def insert_proc_po():
    """Insert PO header."""
    sql = """INSERT INTO proc_po (
        credit_days,
        delivery_instructions,
        expected_delivery_days,
        footer_notes,
        po_date,
        po_approve_date,
        po_no,
        remarks,
        delivery_mode,
        terms_conditions,
        branch_id,
        price_enquiry_id,
        project_id,
        supplier_id,
        status_id,
        supplier_branch_id,
        billing_branch_id,
        shipping_branch_id,
        total_amount,
        net_amount,
        advance_type,
        advance_value,
        advance_amount,
        contact_no,
        contact_person,
        updated_by,
        updated_date_time,
        approval_level
    ) VALUES (
        :credit_days,
        :delivery_instructions,
        :expected_delivery_days,
        :footer_notes,
        :po_date,
        :po_approve_date,
        :po_no,
        :remarks,
        :delivery_mode,
        :terms_conditions,
        :branch_id,
        :price_enquiry_id,
        :project_id,
        :supplier_id,
        :status_id,
        :supplier_branch_id,
        :billing_branch_id,
        :shipping_branch_id,
        :total_amount,
        :net_amount,
        :advance_type,
        :advance_value,
        :advance_amount,
        :contact_no,
        :contact_person,
        :updated_by,
        :updated_date_time,
        :approval_level
    );"""
    return text(sql)


def insert_proc_po_dtl():
    """Insert PO line item."""
    sql = """INSERT INTO proc_po_dtl (
        po_id,
        item_id,
        hsn_code,
        item_make_id,
        qty,
        rate,
        uom_id,
        remarks,
        discount_mode,
        discount_value,
        discount_amount,
        active,
        indent_dtl_id,
        updated_by,
        updated_date_time,
        state
    ) VALUES (
        :po_id,
        :item_id,
        :hsn_code,
        :item_make_id,
        :qty,
        :rate,
        :uom_id,
        :remarks,
        :discount_mode,
        :discount_value,
        :discount_amount,
        :active,
        :indent_dtl_id,
        :updated_by,
        :updated_date_time,
        :state
    );"""
    return text(sql)


def insert_proc_po_additional():
    """Insert PO additional charges."""
    sql = """INSERT INTO proc_po_additional (
        po_id,
        additional_charges_id,
        qty,
        rate,
        net_amount,
        remarks
    ) VALUES (
        :po_id,
        :additional_charges_id,
        :qty,
        :rate,
        :net_amount,
        :remarks
    );"""
    return text(sql)


def insert_po_gst():
    """Insert PO GST record."""
    sql = """INSERT INTO po_gst (
        po_dtl_id,
        po_additional_id,
        tax_pct,
        stax_percentage,
        s_tax_amount,
        i_tax_amount,
        i_tax_percentage,
        c_tax_amount,
        c_tax_percentage,
        tax_amount
    ) VALUES (
        :po_dtl_id,
        :po_additional_id,
        :tax_pct,
        :stax_percentage,
        :s_tax_amount,
        :i_tax_amount,
        :i_tax_percentage,
        :c_tax_amount,
        :c_tax_percentage,
        :tax_amount
    );"""
    return text(sql)


def update_proc_po():
    """Update PO header."""
    sql = """UPDATE proc_po SET
        credit_days = :credit_days,
        delivery_instructions = :delivery_instructions,
        expected_delivery_days = :expected_delivery_days,
        footer_notes = :footer_notes,
        po_date = :po_date,
        remarks = :remarks,
        delivery_mode = :delivery_mode,
        terms_conditions = :terms_conditions,
        branch_id = :branch_id,
        project_id = :project_id,
        supplier_id = :supplier_id,
        supplier_branch_id = :supplier_branch_id,
        billing_branch_id = :billing_branch_id,
        shipping_branch_id = :shipping_branch_id,
        total_amount = :total_amount,
        net_amount = :net_amount,
        advance_type = :advance_type,
        advance_value = :advance_value,
        advance_amount = :advance_amount,
        contact_no = :contact_no,
        contact_person = :contact_person,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        po_no = COALESCE(:po_no, po_no),
        status_id = COALESCE(:status_id, status_id),
        approval_level = :approval_level
    WHERE po_id = :po_id;"""
    return text(sql)


def delete_proc_po_dtl():
    """Soft delete PO line items."""
    sql = """UPDATE proc_po_dtl SET
        active = 0,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time
    WHERE po_id = :po_id;"""
    return text(sql)


def delete_proc_po_additional():
    """Delete PO additional charges."""
    sql = """DELETE FROM proc_po_additional
    WHERE po_id = :po_id;"""
    return text(sql)


def delete_po_gst():
    """Delete PO GST records."""
    sql = """DELETE FROM po_gst
    WHERE po_dtl_id IN (
        SELECT po_dtl_id FROM proc_po_dtl WHERE po_id = :po_id
    ) OR po_additional_id IN (
        SELECT po_additional_id FROM proc_po_additional WHERE po_id = :po_id
    );"""
    return text(sql)


def get_po_by_id_query():
    """Get PO header by ID."""
    sql = """SELECT
        pp.po_id,
        pp.po_no,
        pp.po_date,
        pp.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        pp.supplier_id,
        pm.supp_name AS supplier_name,
        pp.supplier_branch_id,
        pbm.address AS supplier_branch_address,
        pp.billing_branch_id,
        bm_billing.branch_name AS billing_branch_name,
        bm_billing.state_id AS billing_state_id,
        sm_billing.state AS billing_state_name,
        pp.shipping_branch_id,
        bm_shipping.branch_name AS shipping_branch_name,
        bm_shipping.state_id AS shipping_state_id,
        sm_shipping.state AS shipping_state_name,
        pp.project_id,
        prjm.prj_name AS project_name,
        pp.credit_days,
        pp.expected_delivery_days,
        pp.contact_person,
        pp.contact_no,
        pp.footer_notes,
        pp.remarks,
        pp.terms_conditions,
        pp.total_amount,
        pp.net_amount,
        pp.advance_type,
        pp.advance_value,
        pp.advance_amount,
        pp.status_id,
        sm.status_name,
        pp.updated_by,
        pp.updated_date_time AS update_date_time,
        CASE 
            WHEN pp.status_id = 20 THEN pp.approval_level 
            ELSE NULL 
        END AS approval_level
    FROM proc_po AS pp
    LEFT JOIN branch_mst AS bm ON bm.branch_id = pp.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = pp.supplier_id
    LEFT JOIN party_branch_mst AS pbm ON pbm.party_mst_branch_id = pp.supplier_branch_id
    LEFT JOIN branch_mst AS bm_billing ON bm_billing.branch_id = pp.billing_branch_id
    LEFT JOIN state_mst AS sm_billing ON sm_billing.state_id = bm_billing.state_id
    LEFT JOIN branch_mst AS bm_shipping ON bm_shipping.branch_id = pp.shipping_branch_id
    LEFT JOIN state_mst AS sm_shipping ON sm_shipping.state_id = bm_shipping.state_id
    LEFT JOIN project_mst AS prjm ON prjm.project_id = pp.project_id
    LEFT JOIN status_mst AS sm ON sm.status_id = pp.status_id
    WHERE pp.po_id = :po_id
        AND (:co_id IS NULL OR bm.co_id = :co_id);"""
    return text(sql)


def get_po_dtl_by_id_query():
    """Get PO line items by PO ID."""
    sql = """SELECT
        pod.po_dtl_id,
        pod.po_id,
        pod.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code,
        igm.item_grp_name,
        pod.hsn_code,
        pod.item_make_id,
        imk.item_make_name,
        pod.qty,
        pod.rate,
        pod.uom_id,
        um.uom_name,
        pod.remarks,
        pod.discount_mode,
        pod.discount_value,
        pod.discount_amount,
        pod.indent_dtl_id,
        pid.indent_id,
        pi.indent_no,
        dm.dept_id,
        dm.dept_desc AS dept_name
    FROM proc_po_dtl AS pod
    LEFT JOIN item_mst AS im ON im.item_id = pod.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = pod.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = pod.uom_id
    LEFT JOIN proc_indent_dtl AS pid ON pid.indent_dtl_id = pod.indent_dtl_id
    LEFT JOIN proc_indent AS pi ON pi.indent_id = pid.indent_id
    LEFT JOIN dept_mst AS dm ON dm.dept_id = (
        SELECT dept_id FROM proc_indent_dtl WHERE indent_dtl_id = pod.indent_dtl_id
    )
    WHERE pod.po_id = :po_id
        AND pod.active = 1
    ORDER BY pod.po_dtl_id;"""
    return text(sql)


def get_po_additional_by_id_query():
    """Get PO additional charges by PO ID."""
    sql = """SELECT
        ppa.po_additional_id,
        ppa.po_id,
        ppa.additional_charges_id,
        acm.additional_charges_name,
        ppa.qty,
        ppa.rate,
        ppa.net_amount,
        ppa.remarks
    FROM proc_po_additional AS ppa
    LEFT JOIN additional_charges_master AS acm ON acm.additional_charges_id = ppa.additional_charges_id
    WHERE ppa.po_id = :po_id
    ORDER BY ppa.po_additional_id;"""
    return text(sql)


def get_po_gst_by_id_query():
    """Get PO GST records by PO ID."""
    sql = """SELECT
        pg.po_gst_id,
        pg.po_dtl_id,
        pg.po_additional_id,
        pg.tax_pct,
        pg.stax_percentage,
        pg.s_tax_amount,
        pg.i_tax_amount,
        pg.i_tax_percentage,
        pg.c_tax_amount,
        pg.c_tax_percentage,
        pg.tax_amount
    FROM po_gst AS pg
    WHERE pg.po_dtl_id IN (
        SELECT po_dtl_id FROM proc_po_dtl WHERE po_id = :po_id
    ) OR pg.po_additional_id IN (
        SELECT po_additional_id FROM proc_po_additional WHERE po_id = :po_id
    )
    ORDER BY pg.po_gst_id;"""
    return text(sql)


def get_max_po_no_for_branch_fy():
    """Get the maximum po_no for a branch within a financial year.
    
    Financial year: April 1 to March 31
    - If month >= 4 (April-December): FY = year-04-01 to (year+1)-03-31
    - If month < 4 (January-March): FY = (year-1)-04-01 to year-03-31
    """
    sql = """SELECT COALESCE(MAX(CAST(pp.po_no AS UNSIGNED)), 0) as max_po_no
    FROM proc_po pp
    WHERE pp.branch_id = :branch_id
        AND pp.po_date >= :fy_start_date
        AND pp.po_date <= :fy_end_date
        AND pp.po_no IS NOT NULL
        AND pp.po_no REGEXP '^[0-9]+$';"""
    return text(sql)


def get_po_with_approval_info():
    """Get PO details including approval level and status."""
    sql = """SELECT
        pp.po_id,
        pp.status_id,
        pp.approval_level,
        pp.branch_id,
        pp.po_date,
        pp.po_no,
        pp.total_amount,
        bm.co_id
    FROM proc_po pp
    LEFT JOIN branch_mst bm ON bm.branch_id = pp.branch_id
    WHERE pp.po_id = :po_id;"""
    return text(sql)


def update_po_status():
    """Update PO status and approval level. Optionally update po_no."""
    sql = """UPDATE proc_po SET
        status_id = :status_id,
        approval_level = :approval_level,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        po_no = CASE 
            WHEN :po_no IS NOT NULL THEN :po_no 
            ELSE po_no 
        END
    WHERE po_id = :po_id;"""
    return text(sql)