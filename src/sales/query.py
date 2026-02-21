"""
SQL query functions for the sales module.
Covers: sales quotation, sales order, and sales delivery order.
"""

from sqlalchemy.sql import text


# =============================================================================
# SHARED / SETUP QUERIES
# =============================================================================

def get_customers_for_sales(co_id: int = None):
    """Get customers (party_type_id contains 2) with full details."""
    sql = """SELECT
        pm.party_id,
        pm.supp_name AS party_name,
        pm.supp_code AS party_code,
        pm.supp_contact_person AS contact_person,
        pm.supp_contact_designation AS contact_designation,
        pm.supp_email_id AS email,
        pm.phone_no,
        pm.party_pan_no AS pan_no,
        pm.country_id,
        cm.country,
        pm.msme_certified,
        pm.entity_type_id,
        etm.entity_type_name
    FROM party_mst pm
    LEFT JOIN country_mst cm ON cm.country_id = pm.country_id
    LEFT JOIN entity_type_mst etm ON etm.entity_type_id = pm.entity_type_id
    WHERE FIND_IN_SET("2", REPLACE(REPLACE(pm.party_type_id, "{", ""), "}", "")) > 0
        AND (:co_id IS NULL OR pm.co_id = :co_id)
        AND pm.active = 1
    ORDER BY pm.supp_name;"""
    return text(sql)


def get_customer_branches_bulk(co_id: int = None):
    """Get all customer branch addresses in bulk (avoids N+1 query problem)."""
    sql = """SELECT
        pbm.party_mst_branch_id,
        pbm.party_id,
        COALESCE(pbm.address, '') AS party_branch_name,
        pbm.address,
        cm.state_id,
        sm.state AS state_name,
        pbm.gst_no
    FROM party_branch_mst pbm
    LEFT JOIN party_mst pm ON pm.party_id = pbm.party_id
    LEFT JOIN city_mst cm ON cm.city_id = pbm.city_id
    LEFT JOIN state_mst sm ON sm.state_id = cm.state_id
    WHERE pbm.active = 1
        AND FIND_IN_SET("2", REPLACE(REPLACE(pm.party_type_id, "{", ""), "}", "")) > 0
        AND (:co_id IS NULL OR pm.co_id = :co_id)
    ORDER BY pbm.party_id, pbm.party_mst_branch_id;"""
    return text(sql)


def get_brokers_for_sales(co_id: int = None):
    """Get brokers (party_type_id contains 3) for sales."""
    sql = """SELECT
        pm.party_id AS broker_id,
        pm.supp_name AS broker_name,
        pm.supp_code AS broker_code
    FROM party_mst pm
    WHERE FIND_IN_SET("3", REPLACE(REPLACE(pm.party_type_id, "{", ""), "}", "")) > 0
        AND (:co_id IS NULL OR pm.co_id = :co_id)
        AND pm.active = 1
    ORDER BY pm.supp_name;"""
    return text(sql)


def get_transporters_for_sales(co_id: int = None):
    """Get transporters (party_type_id contains 4) for sales."""
    sql = """SELECT
        pm.party_id AS transporter_id,
        pm.supp_name AS transporter_name,
        pm.supp_code AS transporter_code
    FROM party_mst pm
    WHERE FIND_IN_SET("4", REPLACE(REPLACE(pm.party_type_id, "{", ""), "}", "")) > 0
        AND (:co_id IS NULL OR pm.co_id = :co_id)
        AND pm.active = 1
    ORDER BY pm.supp_name;"""
    return text(sql)


# =============================================================================
# SALES ITEM / GROUP QUERIES (for setup_2)
# =============================================================================

def get_item_by_group_id_saleable(item_group_id: int):
    """Get saleable items for a given item group, including tax_percentage and hsn_code."""
    sql = """SELECT im.item_id, im.item_code, im.item_name,
        im.uom_id, um.uom_name,
        im.tax_percentage, im.hsn_code
    FROM item_mst im
    LEFT JOIN uom_mst um ON um.uom_id = im.uom_id
    WHERE im.item_grp_id = :item_group_id
        AND im.active = 1
        AND im.saleable = 1;"""
    return text(sql)


def get_item_uom_by_group_id_saleable(item_group_id: int):
    """Get UOM mappings for saleable items in a given item group."""
    sql = """SELECT uimm.item_id, uimm.map_to_id, um.uom_name
    FROM uom_item_map_mst AS uimm
    JOIN item_mst AS im
      ON im.item_id = uimm.item_id
     AND im.item_grp_id = :item_group_id
     AND im.saleable = 1
     AND im.active = 1
    LEFT JOIN uom_mst AS um
      ON um.uom_id = uimm.map_to_id;"""
    return text(sql)


# =============================================================================
# SALES QUOTATION QUERIES
# =============================================================================

def insert_sales_quotation():
    sql = """INSERT INTO sales_quotation (
        updated_by, updated_date_time,
        quotation_date, quotation_no, branch_id, party_id,
        sales_broker_id, billing_address_id, shipping_address_id,
        quotation_expiry_date, footer_notes, brokerage_percentage,
        gross_amount, net_amount, round_off_value,
        payment_terms, delivery_terms, delivery_days,
        terms_condition, internal_note,
        status_id, approval_level, active
    ) VALUES (
        :updated_by, :updated_date_time,
        :quotation_date, :quotation_no, :branch_id, :party_id,
        :sales_broker_id, :billing_address_id, :shipping_address_id,
        :quotation_expiry_date, :footer_notes, :brokerage_percentage,
        :gross_amount, :net_amount, :round_off_value,
        :payment_terms, :delivery_terms, :delivery_days,
        :terms_condition, :internal_note,
        :status_id, :approval_level, :active
    );"""
    return text(sql)


def insert_sales_quotation_dtl():
    sql = """INSERT INTO sales_quotation_dtl (
        updated_by, updated_date_time,
        sales_quotation_id, hsn_code, item_id, item_make_id,
        quantity, uom_id, rate,
        discount_type, discounted_rate, discount_amount,
        net_amount, total_amount, remarks, active
    ) VALUES (
        :updated_by, :updated_date_time,
        :sales_quotation_id, :hsn_code, :item_id, :item_make_id,
        :quantity, :uom_id, :rate,
        :discount_type, :discounted_rate, :discount_amount,
        :net_amount, :total_amount, :remarks, :active
    );"""
    return text(sql)


def insert_sales_quotation_dtl_gst():
    sql = """INSERT INTO sales_quotation_dtl_gst (
        quotation_lineitem_id,
        igst_amount, igst_percent,
        cgst_amount, cgst_percent,
        sgst_amount, sgst_percent,
        gst_total
    ) VALUES (
        :quotation_lineitem_id,
        :igst_amount, :igst_percent,
        :cgst_amount, :cgst_percent,
        :sgst_amount, :sgst_percent,
        :gst_total
    );"""
    return text(sql)


def update_sales_quotation():
    sql = """UPDATE sales_quotation SET
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        quotation_date = :quotation_date,
        branch_id = :branch_id,
        party_id = :party_id,
        sales_broker_id = :sales_broker_id,
        billing_address_id = :billing_address_id,
        shipping_address_id = :shipping_address_id,
        quotation_expiry_date = :quotation_expiry_date,
        footer_notes = :footer_notes,
        brokerage_percentage = :brokerage_percentage,
        gross_amount = :gross_amount,
        net_amount = :net_amount,
        round_off_value = :round_off_value,
        payment_terms = :payment_terms,
        delivery_terms = :delivery_terms,
        delivery_days = :delivery_days,
        terms_condition = :terms_condition,
        internal_note = :internal_note,
        quotation_no = COALESCE(:quotation_no, quotation_no),
        active = COALESCE(:active, active),
        status_id = COALESCE(:status_id, status_id)
    WHERE sales_quotation_id = :sales_quotation_id;"""
    return text(sql)


def delete_sales_quotation_dtl():
    """Soft delete all detail rows for a quotation."""
    sql = """UPDATE sales_quotation_dtl SET
        active = 0,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time
    WHERE sales_quotation_id = :sales_quotation_id;"""
    return text(sql)


def delete_sales_quotation_dtl_gst():
    """Hard delete GST rows for a quotation's details (they are re-inserted on update)."""
    sql = """DELETE FROM sales_quotation_dtl_gst
    WHERE quotation_lineitem_id IN (
        SELECT quotation_lineitem_id FROM sales_quotation_dtl
        WHERE sales_quotation_id = :sales_quotation_id
    );"""
    return text(sql)


def get_quotation_table_query():
    sql = """SELECT
        sq.sales_quotation_id,
        sq.quotation_no,
        sq.quotation_date,
        sq.quotation_expiry_date,
        sq.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        sq.party_id,
        pm.supp_name AS party_name,
        sq.gross_amount,
        sq.net_amount,
        sq.status_id,
        sm.status_name
    FROM sales_quotation AS sq
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sq.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sq.party_id
    LEFT JOIN status_mst AS sm ON sm.status_id = sq.status_id
    WHERE sq.active = 1
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR sq.quotation_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
        )
    ORDER BY sq.quotation_date DESC, sq.sales_quotation_id DESC
    LIMIT :limit OFFSET :offset;"""
    return text(sql)


def get_quotation_table_count_query():
    sql = """SELECT COUNT(1) AS total
    FROM sales_quotation AS sq
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sq.branch_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sq.party_id
    WHERE sq.active = 1
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR sq.quotation_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
        );"""
    return text(sql)


def get_quotation_by_id_query():
    sql = """SELECT
        sq.sales_quotation_id,
        sq.quotation_no,
        sq.quotation_date,
        sq.quotation_expiry_date,
        sq.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        bm.state_id AS branch_state_id,
        bsm.state AS branch_state_name,
        sq.party_id,
        pm.supp_name AS party_name,
        sq.sales_broker_id,
        brkr.supp_name AS broker_name,
        sq.billing_address_id,
        sq.shipping_address_id,
        pbill.address AS billing_address_text,
        pbill.party_mst_branch_id AS billing_party_branch_id,
        pbill_city.state_id AS billing_state_id,
        sbill.state AS billing_state_name,
        pship.address AS shipping_address_text,
        pship.party_mst_branch_id AS shipping_party_branch_id,
        pship_city.state_id AS shipping_state_id,
        sship.state AS shipping_state_name,
        sq.footer_notes,
        sq.brokerage_percentage,
        sq.gross_amount,
        sq.net_amount,
        sq.round_off_value,
        sq.payment_terms,
        sq.delivery_terms,
        sq.delivery_days,
        sq.terms_condition,
        sq.internal_note,
        sq.status_id,
        sm.status_name,
        sq.updated_by,
        sq.updated_date_time,
        CASE
            WHEN sq.status_id = 20 THEN sq.approval_level
            ELSE NULL
        END AS approval_level
    FROM sales_quotation AS sq
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sq.branch_id
    LEFT JOIN state_mst AS bsm ON bsm.state_id = bm.state_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sq.party_id
    LEFT JOIN party_mst AS brkr ON brkr.party_id = sq.sales_broker_id
    LEFT JOIN status_mst AS sm ON sm.status_id = sq.status_id
    LEFT JOIN party_branch_mst AS pbill ON pbill.party_mst_branch_id = sq.billing_address_id
    LEFT JOIN city_mst AS pbill_city ON pbill_city.city_id = pbill.city_id
    LEFT JOIN state_mst AS sbill ON sbill.state_id = pbill_city.state_id
    LEFT JOIN party_branch_mst AS pship ON pship.party_mst_branch_id = sq.shipping_address_id
    LEFT JOIN city_mst AS pship_city ON pship_city.city_id = pship.city_id
    LEFT JOIN state_mst AS sship ON sship.state_id = pship_city.state_id
    WHERE sq.sales_quotation_id = :sales_quotation_id
        AND (:co_id IS NULL OR bm.co_id = :co_id);"""
    return text(sql)


def get_quotation_dtl_by_id_query():
    sql = """SELECT
        sqd.quotation_lineitem_id,
        sqd.sales_quotation_id,
        sqd.hsn_code,
        sqd.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code,
        igm.item_grp_name,
        sqd.item_make_id,
        imk.item_make_name,
        sqd.quantity,
        sqd.uom_id,
        um.uom_name,
        sqd.rate,
        sqd.discount_type,
        sqd.discounted_rate,
        sqd.discount_amount,
        sqd.net_amount,
        sqd.total_amount,
        sqd.remarks
    FROM sales_quotation_dtl AS sqd
    LEFT JOIN item_mst AS im ON im.item_id = sqd.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = sqd.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = sqd.uom_id
    WHERE sqd.sales_quotation_id = :sales_quotation_id
        AND sqd.active = 1
    ORDER BY sqd.quotation_lineitem_id;"""
    return text(sql)


def get_quotation_gst_by_dtl_id_query():
    sql = """SELECT
        sqg.sales_quotation_dtl_gst_id,
        sqg.quotation_lineitem_id,
        sqg.igst_amount, sqg.igst_percent,
        sqg.cgst_amount, sqg.cgst_percent,
        sqg.sgst_amount, sqg.sgst_percent,
        sqg.gst_total
    FROM sales_quotation_dtl_gst AS sqg
    WHERE sqg.quotation_lineitem_id IN (
        SELECT quotation_lineitem_id FROM sales_quotation_dtl
        WHERE sales_quotation_id = :sales_quotation_id AND active = 1
    )
    ORDER BY sqg.quotation_lineitem_id;"""
    return text(sql)


def update_quotation_status():
    """Update quotation status and approval level. Optionally update quotation_no."""
    sql = """UPDATE sales_quotation SET
        status_id = :status_id,
        approval_level = :approval_level,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        quotation_no = CASE
            WHEN :quotation_no IS NOT NULL THEN :quotation_no
            ELSE quotation_no
        END
    WHERE sales_quotation_id = :sales_quotation_id;"""
    return text(sql)


def get_quotation_with_approval_info():
    sql = """SELECT
        sq.sales_quotation_id,
        sq.status_id,
        sq.approval_level,
        sq.branch_id,
        sq.quotation_date,
        sq.quotation_no,
        sq.net_amount,
        bm.co_id
    FROM sales_quotation sq
    LEFT JOIN branch_mst bm ON bm.branch_id = sq.branch_id
    WHERE sq.sales_quotation_id = :sales_quotation_id;"""
    return text(sql)


def get_max_quotation_no_for_branch_fy():
    sql = """SELECT COALESCE(MAX(CAST(sq.quotation_no AS UNSIGNED)), 0) AS max_doc_no
    FROM sales_quotation sq
    WHERE sq.branch_id = :branch_id
        AND sq.quotation_date >= :fy_start_date
        AND sq.quotation_date <= :fy_end_date
        AND sq.quotation_no IS NOT NULL;"""
    return text(sql)


def get_approved_quotations_query():
    """Get all approved quotations (status_id = 3) for dropdown when creating sales order."""
    sql = """SELECT
        sq.sales_quotation_id,
        sq.quotation_no,
        sq.quotation_date,
        sq.party_id,
        pm.supp_name AS party_name,
        sq.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        sq.net_amount
    FROM sales_quotation AS sq
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sq.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sq.party_id
    WHERE sq.status_id = 3
        AND sq.active = 1
        AND (:branch_id IS NULL OR sq.branch_id = :branch_id)
        AND (:co_id IS NULL OR bm.co_id = :co_id)
    ORDER BY sq.quotation_date DESC, sq.sales_quotation_id DESC;"""
    return text(sql)


def get_quotation_lines_for_order():
    """Get quotation line items to pre-fill sales order lines."""
    sql = """SELECT
        sqd.quotation_lineitem_id,
        sqd.hsn_code,
        sqd.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        sqd.item_make_id,
        imk.item_make_name,
        sqd.quantity,
        sqd.uom_id,
        um.uom_name,
        sqd.rate,
        sqd.discount_type,
        sqd.discounted_rate,
        sqd.discount_amount,
        sqd.net_amount,
        sqd.total_amount,
        sqd.remarks
    FROM sales_quotation_dtl AS sqd
    LEFT JOIN item_mst AS im ON im.item_id = sqd.item_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = sqd.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = sqd.uom_id
    WHERE sqd.sales_quotation_id = :sales_quotation_id
        AND sqd.active = 1
    ORDER BY sqd.quotation_lineitem_id;"""
    return text(sql)


# =============================================================================
# SALES ORDER QUERIES
# =============================================================================

def insert_sales_order():
    sql = """INSERT INTO sales_order (
        updated_by, updated_date_time,
        sales_order_date, sales_no, invoice_type,
        branch_id, quotation_id, party_id, party_branch_id,
        broker_id, billing_to_id, shipping_to_id, transporter_id,
        sales_order_expiry_date, broker_commission_percent,
        footer_note, terms_conditions, internal_note,
        delivery_terms, payment_terms, delivery_days,
        freight_charges, gross_amount, net_amount,
        status_id, approval_level, active
    ) VALUES (
        :updated_by, :updated_date_time,
        :sales_order_date, :sales_no, :invoice_type,
        :branch_id, :quotation_id, :party_id, :party_branch_id,
        :broker_id, :billing_to_id, :shipping_to_id, :transporter_id,
        :sales_order_expiry_date, :broker_commission_percent,
        :footer_note, :terms_conditions, :internal_note,
        :delivery_terms, :payment_terms, :delivery_days,
        :freight_charges, :gross_amount, :net_amount,
        :status_id, :approval_level, :active
    );"""
    return text(sql)


def insert_sales_order_dtl():
    sql = """INSERT INTO sales_order_dtl (
        updated_by, updated_date_time,
        sales_order_id, quotation_lineitem_id,
        hsn_code, item_id, item_make_id,
        quantity, uom_id, rate,
        discount_type, discounted_rate, discount_amount,
        net_amount, total_amount, remarks, active
    ) VALUES (
        :updated_by, :updated_date_time,
        :sales_order_id, :quotation_lineitem_id,
        :hsn_code, :item_id, :item_make_id,
        :quantity, :uom_id, :rate,
        :discount_type, :discounted_rate, :discount_amount,
        :net_amount, :total_amount, :remarks, :active
    );"""
    return text(sql)


def insert_sales_order_dtl_gst():
    sql = """INSERT INTO sales_order_dtl_gst (
        sales_order_dtl_id,
        igst_amount, igst_percent,
        cgst_amount, cgst_percent,
        sgst_amount, sgst_percent,
        gst_total
    ) VALUES (
        :sales_order_dtl_id,
        :igst_amount, :igst_percent,
        :cgst_amount, :cgst_percent,
        :sgst_amount, :sgst_percent,
        :gst_total
    );"""
    return text(sql)


def update_sales_order():
    sql = """UPDATE sales_order SET
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        sales_order_date = :sales_order_date,
        invoice_type = :invoice_type,
        branch_id = :branch_id,
        quotation_id = :quotation_id,
        party_id = :party_id,
        party_branch_id = :party_branch_id,
        broker_id = :broker_id,
        billing_to_id = :billing_to_id,
        shipping_to_id = :shipping_to_id,
        transporter_id = :transporter_id,
        sales_order_expiry_date = :sales_order_expiry_date,
        broker_commission_percent = :broker_commission_percent,
        footer_note = :footer_note,
        terms_conditions = :terms_conditions,
        internal_note = :internal_note,
        delivery_terms = :delivery_terms,
        payment_terms = :payment_terms,
        delivery_days = :delivery_days,
        freight_charges = :freight_charges,
        gross_amount = :gross_amount,
        net_amount = :net_amount,
        sales_no = COALESCE(:sales_no, sales_no),
        active = COALESCE(:active, active),
        status_id = COALESCE(:status_id, status_id)
    WHERE sales_order_id = :sales_order_id;"""
    return text(sql)


def delete_sales_order_dtl():
    sql = """UPDATE sales_order_dtl SET
        active = 0,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time
    WHERE sales_order_id = :sales_order_id;"""
    return text(sql)


def delete_sales_order_dtl_gst():
    sql = """DELETE FROM sales_order_dtl_gst
    WHERE sales_order_dtl_id IN (
        SELECT sales_order_dtl_id FROM sales_order_dtl
        WHERE sales_order_id = :sales_order_id
    );"""
    return text(sql)


def get_sales_order_table_query():
    sql = """SELECT
        so.sales_order_id,
        so.sales_no,
        so.sales_order_date,
        so.sales_order_expiry_date,
        so.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        so.party_id,
        pm.supp_name AS party_name,
        so.quotation_id,
        sq.quotation_no,
        so.gross_amount,
        so.net_amount,
        so.status_id,
        sm.status_name
    FROM sales_order AS so
    LEFT JOIN branch_mst AS bm ON bm.branch_id = so.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = so.party_id
    LEFT JOIN sales_quotation AS sq ON sq.sales_quotation_id = so.quotation_id
    LEFT JOIN status_mst AS sm ON sm.status_id = so.status_id
    WHERE so.active = 1
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR so.sales_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
            OR sq.quotation_no LIKE :search_like
        )
    ORDER BY so.sales_order_date DESC, so.sales_order_id DESC
    LIMIT :limit OFFSET :offset;"""
    return text(sql)


def get_sales_order_table_count_query():
    sql = """SELECT COUNT(1) AS total
    FROM sales_order AS so
    LEFT JOIN branch_mst AS bm ON bm.branch_id = so.branch_id
    LEFT JOIN party_mst AS pm ON pm.party_id = so.party_id
    LEFT JOIN sales_quotation AS sq ON sq.sales_quotation_id = so.quotation_id
    WHERE so.active = 1
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR so.sales_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
            OR sq.quotation_no LIKE :search_like
        );"""
    return text(sql)


def get_sales_order_by_id_query():
    sql = """SELECT
        so.sales_order_id,
        so.sales_no,
        so.sales_order_date,
        so.sales_order_expiry_date,
        so.invoice_type,
        so.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        so.quotation_id,
        sq.quotation_no,
        so.party_id,
        pm.supp_name AS party_name,
        so.party_branch_id,
        so.broker_id,
        brkr.supp_name AS broker_name,
        so.billing_to_id,
        so.shipping_to_id,
        so.transporter_id,
        trns.supp_name AS transporter_name,
        so.broker_commission_percent,
        so.footer_note,
        so.terms_conditions,
        so.internal_note,
        so.delivery_terms,
        so.payment_terms,
        so.delivery_days,
        so.freight_charges,
        so.gross_amount,
        so.net_amount,
        so.status_id,
        sm.status_name,
        so.updated_by,
        so.updated_date_time,
        CASE
            WHEN so.status_id = 20 THEN so.approval_level
            ELSE NULL
        END AS approval_level
    FROM sales_order AS so
    LEFT JOIN branch_mst AS bm ON bm.branch_id = so.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN sales_quotation AS sq ON sq.sales_quotation_id = so.quotation_id
    LEFT JOIN party_mst AS pm ON pm.party_id = so.party_id
    LEFT JOIN party_mst AS brkr ON brkr.party_id = so.broker_id
    LEFT JOIN party_mst AS trns ON trns.party_id = so.transporter_id
    LEFT JOIN status_mst AS sm ON sm.status_id = so.status_id
    WHERE so.sales_order_id = :sales_order_id
        AND (:co_id IS NULL OR bm.co_id = :co_id);"""
    return text(sql)


def get_sales_order_dtl_by_id_query():
    sql = """SELECT
        sod.sales_order_dtl_id,
        sod.sales_order_id,
        sod.quotation_lineitem_id,
        sod.hsn_code,
        sod.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code,
        igm.item_grp_name,
        sod.item_make_id,
        imk.item_make_name,
        sod.quantity,
        sod.uom_id,
        um.uom_name,
        sod.rate,
        sod.discount_type,
        sod.discounted_rate,
        sod.discount_amount,
        sod.net_amount,
        sod.total_amount,
        sod.remarks
    FROM sales_order_dtl AS sod
    LEFT JOIN item_mst AS im ON im.item_id = sod.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = sod.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = sod.uom_id
    WHERE sod.sales_order_id = :sales_order_id
        AND sod.active = 1
    ORDER BY sod.sales_order_dtl_id;"""
    return text(sql)


def get_sales_order_gst_by_id_query():
    sql = """SELECT
        sog.sales_order_dtl_gst_id,
        sog.sales_order_dtl_id,
        sog.igst_amount, sog.igst_percent,
        sog.cgst_amount, sog.cgst_percent,
        sog.sgst_amount, sog.sgst_percent,
        sog.gst_total
    FROM sales_order_dtl_gst AS sog
    WHERE sog.sales_order_dtl_id IN (
        SELECT sales_order_dtl_id FROM sales_order_dtl
        WHERE sales_order_id = :sales_order_id AND active = 1
    )
    ORDER BY sog.sales_order_dtl_id;"""
    return text(sql)


def update_sales_order_status():
    sql = """UPDATE sales_order SET
        status_id = :status_id,
        approval_level = :approval_level,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        sales_no = CASE
            WHEN :sales_no IS NOT NULL THEN :sales_no
            ELSE sales_no
        END
    WHERE sales_order_id = :sales_order_id;"""
    return text(sql)


def get_sales_order_with_approval_info():
    sql = """SELECT
        so.sales_order_id,
        so.status_id,
        so.approval_level,
        so.branch_id,
        so.sales_order_date,
        so.sales_no,
        so.net_amount,
        bm.co_id
    FROM sales_order so
    LEFT JOIN branch_mst bm ON bm.branch_id = so.branch_id
    WHERE so.sales_order_id = :sales_order_id;"""
    return text(sql)


def get_max_sales_order_no_for_branch_fy():
    sql = """SELECT COALESCE(MAX(CAST(so.sales_no AS UNSIGNED)), 0) AS max_doc_no
    FROM sales_order so
    WHERE so.branch_id = :branch_id
        AND so.sales_order_date >= :fy_start_date
        AND so.sales_order_date <= :fy_end_date
        AND so.sales_no IS NOT NULL;"""
    return text(sql)


def get_approved_sales_orders_query():
    """Get all approved sales orders (status_id = 3) for dropdown when creating delivery order."""
    sql = """SELECT
        so.sales_order_id,
        so.sales_no,
        so.sales_order_date,
        so.party_id,
        pm.supp_name AS party_name,
        so.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        so.net_amount
    FROM sales_order AS so
    LEFT JOIN branch_mst AS bm ON bm.branch_id = so.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = so.party_id
    WHERE so.status_id = 3
        AND so.active = 1
        AND (:branch_id IS NULL OR so.branch_id = :branch_id)
        AND (:co_id IS NULL OR bm.co_id = :co_id)
    ORDER BY so.sales_order_date DESC, so.sales_order_id DESC;"""
    return text(sql)


def get_sales_order_lines_for_delivery():
    """Get sales order line items to pre-fill delivery order lines."""
    sql = """SELECT
        sod.sales_order_dtl_id,
        sod.quotation_lineitem_id,
        sod.hsn_code,
        sod.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        sod.item_make_id,
        imk.item_make_name,
        sod.quantity,
        sod.uom_id,
        um.uom_name,
        sod.rate,
        sod.discount_type,
        sod.discounted_rate,
        sod.discount_amount,
        sod.net_amount,
        sod.total_amount,
        sod.remarks
    FROM sales_order_dtl AS sod
    LEFT JOIN item_mst AS im ON im.item_id = sod.item_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = sod.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = sod.uom_id
    WHERE sod.sales_order_id = :sales_order_id
        AND sod.active = 1
    ORDER BY sod.sales_order_dtl_id;"""
    return text(sql)


# =============================================================================
# SALES DELIVERY ORDER QUERIES
# =============================================================================

def insert_sales_delivery_order():
    sql = """INSERT INTO sales_delivery_order (
        updated_by, updated_date_time,
        delivery_order_date, delivery_order_no,
        branch_id, sales_order_id, party_id, party_branch_id,
        billing_to_id, shipping_to_id, transporter_id,
        vehicle_no, driver_name, driver_contact,
        eway_bill_no, eway_bill_date, expected_delivery_date,
        footer_note, internal_note,
        gross_amount, net_amount, freight_charges, round_off_value,
        status_id, approval_level, active
    ) VALUES (
        :updated_by, :updated_date_time,
        :delivery_order_date, :delivery_order_no,
        :branch_id, :sales_order_id, :party_id, :party_branch_id,
        :billing_to_id, :shipping_to_id, :transporter_id,
        :vehicle_no, :driver_name, :driver_contact,
        :eway_bill_no, :eway_bill_date, :expected_delivery_date,
        :footer_note, :internal_note,
        :gross_amount, :net_amount, :freight_charges, :round_off_value,
        :status_id, :approval_level, :active
    );"""
    return text(sql)


def insert_sales_delivery_order_dtl():
    sql = """INSERT INTO sales_delivery_order_dtl (
        updated_by, updated_date_time,
        sales_delivery_order_id, sales_order_dtl_id,
        hsn_code, item_id, item_make_id,
        quantity, uom_id, rate,
        discount_type, discounted_rate, discount_amount,
        net_amount, total_amount, remarks, active
    ) VALUES (
        :updated_by, :updated_date_time,
        :sales_delivery_order_id, :sales_order_dtl_id,
        :hsn_code, :item_id, :item_make_id,
        :quantity, :uom_id, :rate,
        :discount_type, :discounted_rate, :discount_amount,
        :net_amount, :total_amount, :remarks, :active
    );"""
    return text(sql)


def insert_sales_delivery_order_dtl_gst():
    sql = """INSERT INTO sales_delivery_order_dtl_gst (
        sales_delivery_order_dtl_id,
        igst_amount, igst_percent,
        cgst_amount, cgst_percent,
        sgst_amount, sgst_percent,
        gst_total
    ) VALUES (
        :sales_delivery_order_dtl_id,
        :igst_amount, :igst_percent,
        :cgst_amount, :cgst_percent,
        :sgst_amount, :sgst_percent,
        :gst_total
    );"""
    return text(sql)


def update_sales_delivery_order():
    sql = """UPDATE sales_delivery_order SET
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        delivery_order_date = :delivery_order_date,
        branch_id = :branch_id,
        sales_order_id = :sales_order_id,
        party_id = :party_id,
        party_branch_id = :party_branch_id,
        billing_to_id = :billing_to_id,
        shipping_to_id = :shipping_to_id,
        transporter_id = :transporter_id,
        vehicle_no = :vehicle_no,
        driver_name = :driver_name,
        driver_contact = :driver_contact,
        eway_bill_no = :eway_bill_no,
        eway_bill_date = :eway_bill_date,
        expected_delivery_date = :expected_delivery_date,
        footer_note = :footer_note,
        internal_note = :internal_note,
        gross_amount = :gross_amount,
        net_amount = :net_amount,
        freight_charges = :freight_charges,
        round_off_value = :round_off_value,
        delivery_order_no = COALESCE(:delivery_order_no, delivery_order_no),
        active = COALESCE(:active, active),
        status_id = COALESCE(:status_id, status_id)
    WHERE sales_delivery_order_id = :sales_delivery_order_id;"""
    return text(sql)


def delete_sales_delivery_order_dtl():
    sql = """UPDATE sales_delivery_order_dtl SET
        active = 0,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time
    WHERE sales_delivery_order_id = :sales_delivery_order_id;"""
    return text(sql)


def delete_sales_delivery_order_dtl_gst():
    sql = """DELETE FROM sales_delivery_order_dtl_gst
    WHERE sales_delivery_order_dtl_id IN (
        SELECT sales_delivery_order_dtl_id FROM sales_delivery_order_dtl
        WHERE sales_delivery_order_id = :sales_delivery_order_id
    );"""
    return text(sql)


def get_delivery_order_table_query():
    sql = """SELECT
        sdo.sales_delivery_order_id,
        sdo.delivery_order_no,
        sdo.delivery_order_date,
        sdo.expected_delivery_date,
        sdo.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        sdo.party_id,
        pm.supp_name AS party_name,
        sdo.sales_order_id,
        so.sales_no,
        sdo.gross_amount,
        sdo.net_amount,
        sdo.status_id,
        sm.status_name
    FROM sales_delivery_order AS sdo
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sdo.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sdo.party_id
    LEFT JOIN sales_order AS so ON so.sales_order_id = sdo.sales_order_id
    LEFT JOIN status_mst AS sm ON sm.status_id = sdo.status_id
    WHERE sdo.active = 1
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR sdo.delivery_order_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
            OR so.sales_no LIKE :search_like
        )
    ORDER BY sdo.delivery_order_date DESC, sdo.sales_delivery_order_id DESC
    LIMIT :limit OFFSET :offset;"""
    return text(sql)


def get_delivery_order_table_count_query():
    sql = """SELECT COUNT(1) AS total
    FROM sales_delivery_order AS sdo
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sdo.branch_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sdo.party_id
    LEFT JOIN sales_order AS so ON so.sales_order_id = sdo.sales_order_id
    WHERE sdo.active = 1
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR sdo.delivery_order_no LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
            OR so.sales_no LIKE :search_like
        );"""
    return text(sql)


def get_delivery_order_by_id_query():
    sql = """SELECT
        sdo.sales_delivery_order_id,
        sdo.delivery_order_no,
        sdo.delivery_order_date,
        sdo.expected_delivery_date,
        sdo.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        sdo.sales_order_id,
        so.sales_no,
        sdo.party_id,
        pm.supp_name AS party_name,
        sdo.party_branch_id,
        sdo.billing_to_id,
        sdo.shipping_to_id,
        sdo.transporter_id,
        trns.supp_name AS transporter_name,
        sdo.vehicle_no,
        sdo.driver_name,
        sdo.driver_contact,
        sdo.eway_bill_no,
        sdo.eway_bill_date,
        sdo.footer_note,
        sdo.internal_note,
        sdo.gross_amount,
        sdo.net_amount,
        sdo.freight_charges,
        sdo.round_off_value,
        sdo.status_id,
        sm.status_name,
        sdo.updated_by,
        sdo.updated_date_time,
        CASE
            WHEN sdo.status_id = 20 THEN sdo.approval_level
            ELSE NULL
        END AS approval_level
    FROM sales_delivery_order AS sdo
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sdo.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN sales_order AS so ON so.sales_order_id = sdo.sales_order_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sdo.party_id
    LEFT JOIN party_mst AS trns ON trns.party_id = sdo.transporter_id
    LEFT JOIN status_mst AS sm ON sm.status_id = sdo.status_id
    WHERE sdo.sales_delivery_order_id = :sales_delivery_order_id
        AND (:co_id IS NULL OR bm.co_id = :co_id);"""
    return text(sql)


def get_delivery_order_dtl_by_id_query():
    sql = """SELECT
        sdod.sales_delivery_order_dtl_id,
        sdod.sales_delivery_order_id,
        sdod.sales_order_dtl_id,
        sdod.hsn_code,
        sdod.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code,
        igm.item_grp_name,
        sdod.item_make_id,
        imk.item_make_name,
        sdod.quantity,
        sdod.uom_id,
        um.uom_name,
        sdod.rate,
        sdod.discount_type,
        sdod.discounted_rate,
        sdod.discount_amount,
        sdod.net_amount,
        sdod.total_amount,
        sdod.remarks
    FROM sales_delivery_order_dtl AS sdod
    LEFT JOIN item_mst AS im ON im.item_id = sdod.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = sdod.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = sdod.uom_id
    WHERE sdod.sales_delivery_order_id = :sales_delivery_order_id
        AND sdod.active = 1
    ORDER BY sdod.sales_delivery_order_dtl_id;"""
    return text(sql)


def get_delivery_order_gst_by_id_query():
    sql = """SELECT
        sdog.sales_delivery_order_dtl_gst_id,
        sdog.sales_delivery_order_dtl_id,
        sdog.igst_amount, sdog.igst_percent,
        sdog.cgst_amount, sdog.cgst_percent,
        sdog.sgst_amount, sdog.sgst_percent,
        sdog.gst_total
    FROM sales_delivery_order_dtl_gst AS sdog
    WHERE sdog.sales_delivery_order_dtl_id IN (
        SELECT sales_delivery_order_dtl_id FROM sales_delivery_order_dtl
        WHERE sales_delivery_order_id = :sales_delivery_order_id AND active = 1
    )
    ORDER BY sdog.sales_delivery_order_dtl_id;"""
    return text(sql)


def update_delivery_order_status():
    sql = """UPDATE sales_delivery_order SET
        status_id = :status_id,
        approval_level = :approval_level,
        updated_by = :updated_by,
        updated_date_time = :updated_date_time,
        delivery_order_no = CASE
            WHEN :delivery_order_no IS NOT NULL THEN :delivery_order_no
            ELSE delivery_order_no
        END
    WHERE sales_delivery_order_id = :sales_delivery_order_id;"""
    return text(sql)


def get_delivery_order_with_approval_info():
    sql = """SELECT
        sdo.sales_delivery_order_id,
        sdo.status_id,
        sdo.approval_level,
        sdo.branch_id,
        sdo.delivery_order_date,
        sdo.delivery_order_no,
        sdo.net_amount,
        bm.co_id
    FROM sales_delivery_order sdo
    LEFT JOIN branch_mst bm ON bm.branch_id = sdo.branch_id
    WHERE sdo.sales_delivery_order_id = :sales_delivery_order_id;"""
    return text(sql)


def get_max_delivery_order_no_for_branch_fy():
    sql = """SELECT COALESCE(MAX(CAST(sdo.delivery_order_no AS UNSIGNED)), 0) AS max_doc_no
    FROM sales_delivery_order sdo
    WHERE sdo.branch_id = :branch_id
        AND sdo.delivery_order_date >= :fy_start_date
        AND sdo.delivery_order_date <= :fy_end_date
        AND sdo.delivery_order_no IS NOT NULL;"""
    return text(sql)


# =============================================================================
# SALES INVOICE QUERIES
# =============================================================================


def get_approved_delivery_orders_query():
    """Get all approved delivery orders (status_id = 3) for dropdown when creating invoice."""
    sql = """SELECT
        sdo.sales_delivery_order_id,
        sdo.delivery_order_no,
        sdo.delivery_order_date,
        sdo.party_id,
        pm.supp_name AS party_name,
        sdo.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        sdo.net_amount
    FROM sales_delivery_order AS sdo
    LEFT JOIN branch_mst AS bm ON bm.branch_id = sdo.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = sdo.party_id
    WHERE sdo.status_id = 3
        AND sdo.active = 1
        AND (:branch_id IS NULL OR sdo.branch_id = :branch_id)
        AND (:co_id IS NULL OR bm.co_id = :co_id)
    ORDER BY sdo.delivery_order_date DESC, sdo.sales_delivery_order_id DESC;"""
    return text(sql)


def get_delivery_order_lines_for_invoice():
    """Get delivery order line items to pre-fill invoice lines."""
    sql = """SELECT
        sdod.sales_delivery_order_dtl_id AS delivery_order_dtl_id,
        sdod.hsn_code,
        sdod.item_id,
        im.item_code,
        im.item_name,
        im.item_grp_id,
        igm.item_grp_code AS item_grp_code,
        igm.item_grp_name AS item_grp_name,
        sdod.item_make_id,
        imk.item_make_name,
        sdod.quantity,
        sdod.uom_id,
        um.uom_name,
        sdod.rate,
        sdod.discount_type,
        sdod.discounted_rate,
        sdod.discount_amount,
        sdod.net_amount,
        sdod.total_amount,
        sdod.remarks,
        COALESCE(im.tax_percentage, 0) AS tax_percentage
    FROM sales_delivery_order_dtl AS sdod
    LEFT JOIN item_mst AS im ON im.item_id = sdod.item_id
    LEFT JOIN item_grp_mst AS igm ON igm.item_grp_id = im.item_grp_id
    LEFT JOIN item_make AS imk ON imk.item_make_id = sdod.item_make_id
    LEFT JOIN uom_mst AS um ON um.uom_id = sdod.uom_id
    WHERE sdod.sales_delivery_order_id = :sales_delivery_order_id
        AND sdod.active = 1
    ORDER BY sdod.sales_delivery_order_dtl_id;"""
    return text(sql)


def get_invoice_table_query():
    sql = """SELECT
        si.invoice_id,
        si.invoice_unique_no,
        si.invoice_no_string,
        si.invoice_date,
        si.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        si.party_id,
        pm.supp_name AS party_name,
        si.del_order_no,
        si.invoice_amount,
        si.grand_total,
        si.status,
        sm.status_name
    FROM sales_invoice AS si
    LEFT JOIN branch_mst AS bm ON bm.branch_id = si.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = si.party_id
    LEFT JOIN status_mst AS sm ON sm.status_id = si.status
    WHERE (si.is_active = 1 OR si.is_active IS NULL)
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR si.invoice_no_string LIKE :search_like
            OR CAST(si.invoice_unique_no AS CHAR) LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
        )
    ORDER BY si.invoice_date DESC, si.invoice_id DESC
    LIMIT :limit OFFSET :offset;"""
    return text(sql)


def get_invoice_table_count_query():
    sql = """SELECT COUNT(1) AS total
    FROM sales_invoice AS si
    LEFT JOIN branch_mst AS bm ON bm.branch_id = si.branch_id
    LEFT JOIN party_mst AS pm ON pm.party_id = si.party_id
    WHERE (si.is_active = 1 OR si.is_active IS NULL)
        AND (:co_id IS NULL OR bm.co_id = :co_id)
        AND (
            :search_like IS NULL
            OR si.invoice_no_string LIKE :search_like
            OR CAST(si.invoice_unique_no AS CHAR) LIKE :search_like
            OR pm.supp_name LIKE :search_like
            OR bm.branch_name LIKE :search_like
        );"""
    return text(sql)


def get_invoice_by_id_query():
    sql = """SELECT
        si.invoice_id,
        si.invoice_unique_no,
        si.invoice_no_string,
        si.invoice_date,
        si.challan_no,
        si.challan_date,
        si.branch_id,
        bm.branch_name,
        bm.branch_prefix,
        bm.co_id,
        cm.co_prefix,
        si.party_id,
        pm.supp_name AS party_name,
        si.del_order_no,
        si.del_order_date,
        si.sale_no,
        si.shipping_address,
        si.shipping_state_code,
        si.shipping_state_name,
        si.transporter_id,
        trns.supp_name AS transporter_name,
        si.vehicle_no,
        si.eway_bill_no,
        si.eway_bill_date,
        si.invoice_type,
        si.footer_notes,
        si.terms,
        si.terms_conditions,
        si.invoice_amount,
        si.grand_total,
        si.tax_amount,
        si.freight_charges,
        si.round_off,
        si.tcs_percentage,
        si.tcs_amount,
        si.status,
        sm.status_name,
        si.updated_by,
        si.updated_date,
        si.intra_inter_state
    FROM sales_invoice AS si
    LEFT JOIN branch_mst AS bm ON bm.branch_id = si.branch_id
    LEFT JOIN co_mst AS cm ON cm.co_id = bm.co_id
    LEFT JOIN party_mst AS pm ON pm.party_id = si.party_id
    LEFT JOIN party_mst AS trns ON trns.party_id = si.transporter_id
    LEFT JOIN status_mst AS sm ON sm.status_id = si.status
    WHERE si.invoice_id = :invoice_id
        AND (:co_id IS NULL OR bm.co_id = :co_id);"""
    return text(sql)


def get_invoice_dtl_by_id_query():
    sql = """SELECT
        ili.invoice_line_item_id,
        ili.invoice_id,
        ili.delivery_line_id,
        ili.hsn_code,
        ili.item_id,
        ili.item_name,
        ili.item_group,
        im.item_grp_id,
        ili.make,
        ili.quantity,
        ili.uom,
        um.uom_id,
        ili.rate,
        ili.amount_without_tax,
        ili.tax_amount,
        ili.total_amount,
        ili.cgst_amt,
        ili.cgst_per,
        ili.sgst_amt,
        ili.sgst_per,
        ili.igst_amt,
        ili.igst_per,
        ili.item_description
    FROM sales_invoice_dtl AS ili
    LEFT JOIN item_mst AS im ON CAST(im.item_id AS CHAR) = ili.item_id
    LEFT JOIN uom_mst AS um ON um.uom_name = ili.uom
    WHERE ili.invoice_id = :invoice_id
        AND (ili.is_active = 1 OR ili.is_active IS NULL)
    ORDER BY ili.invoice_line_item_id;"""
    return text(sql)


def insert_sales_invoice():
    sql = """INSERT INTO sales_invoice (
        invoice_date, invoice_unique_no, invoice_no_string,
        branch_id, co_id, party_id,
        del_order_no, del_order_date,
        challan_no, challan_date,
        transporter_id, vehicle_no,
        eway_bill_no, eway_bill_date,
        invoice_type, footer_notes, terms, terms_conditions,
        invoice_amount, grand_total, tax_amount,
        freight_charges, round_off,
        tcs_percentage, tcs_amount,
        shipping_address, shipping_state_code, shipping_state_name,
        intra_inter_state,
        status, is_active,
        created_by, created_date, updated_by, updated_date
    ) VALUES (
        :invoice_date, :invoice_unique_no, :invoice_no_string,
        :branch_id, :co_id, :party_id,
        :del_order_no, :del_order_date,
        :challan_no, :challan_date,
        :transporter_id, :vehicle_no,
        :eway_bill_no, :eway_bill_date,
        :invoice_type, :footer_notes, :terms, :terms_conditions,
        :invoice_amount, :grand_total, :tax_amount,
        :freight_charges, :round_off,
        :tcs_percentage, :tcs_amount,
        :shipping_address, :shipping_state_code, :shipping_state_name,
        :intra_inter_state,
        :status, 1,
        :created_by, NOW(), :updated_by, CURDATE()
    );"""
    return text(sql)


def insert_invoice_line_item():
    sql = """INSERT INTO sales_invoice_dtl (
        invoice_id, co_id, delivery_line_id,
        hsn_code, item_id, item_name, item_group, item_description, make,
        quantity, uom, rate,
        amount_without_tax, tax_amount, total_amount,
        cgst_amt, cgst_per, sgst_amt, sgst_per,
        igst_amt, igst_per,
        claim_rate,
        is_active
    ) VALUES (
        :invoice_id, :co_id, :delivery_line_id,
        :hsn_code, :item_id, :item_name, :item_group, :item_description, :make,
        :quantity, :uom, :rate,
        :amount_without_tax, :tax_amount, :total_amount,
        :cgst_amt, :cgst_per, :sgst_amt, :sgst_per,
        :igst_amt, :igst_per,
        :claim_rate,
        1
    );"""
    return text(sql)


def update_sales_invoice():
    sql = """UPDATE sales_invoice SET
        invoice_date = :invoice_date,
        branch_id = :branch_id,
        party_id = :party_id,
        del_order_no = :del_order_no,
        del_order_date = :del_order_date,
        challan_no = :challan_no,
        challan_date = :challan_date,
        transporter_id = :transporter_id,
        vehicle_no = :vehicle_no,
        eway_bill_no = :eway_bill_no,
        eway_bill_date = :eway_bill_date,
        invoice_type = :invoice_type,
        footer_notes = :footer_notes,
        terms = :terms,
        terms_conditions = :terms_conditions,
        invoice_amount = :invoice_amount,
        grand_total = :grand_total,
        tax_amount = :tax_amount,
        freight_charges = :freight_charges,
        round_off = :round_off,
        tcs_percentage = :tcs_percentage,
        tcs_amount = :tcs_amount,
        updated_by = :updated_by,
        updated_date = CURDATE()
    WHERE invoice_id = :invoice_id;"""
    return text(sql)


def delete_invoice_line_items():
    sql = """UPDATE sales_invoice_dtl SET is_active = 0
    WHERE invoice_id = :invoice_id;"""
    return text(sql)


def update_invoice_status():
    sql = """UPDATE sales_invoice SET
        status = :status_id,
        invoice_unique_no = CASE
            WHEN :invoice_unique_no IS NOT NULL THEN :invoice_unique_no
            ELSE invoice_unique_no
        END,
        invoice_no_string = CASE
            WHEN :invoice_no_string IS NOT NULL THEN :invoice_no_string
            ELSE invoice_no_string
        END,
        updated_by = :updated_by,
        updated_date = CURDATE()
    WHERE invoice_id = :invoice_id;"""
    return text(sql)


def get_invoice_with_approval_info():
    sql = """SELECT
        si.invoice_id,
        si.status,
        si.invoice_unique_no,
        si.invoice_no_string,
        si.branch_id,
        si.invoice_date,
        si.invoice_amount,
        si.grand_total,
        bm.co_id
    FROM sales_invoice si
    LEFT JOIN branch_mst bm ON bm.branch_id = si.branch_id
    WHERE si.invoice_id = :invoice_id;"""
    return text(sql)


def get_max_invoice_no_for_branch_fy():
    sql = """SELECT COALESCE(MAX(si.invoice_unique_no), 0) AS max_doc_no
    FROM sales_invoice si
    WHERE si.branch_id = :branch_id
        AND si.invoice_date >= :fy_start_date
        AND si.invoice_date <= :fy_end_date
        AND si.invoice_unique_no IS NOT NULL;"""
    return text(sql)
