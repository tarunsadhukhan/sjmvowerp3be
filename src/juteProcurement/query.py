from sqlalchemy.sql import text

from src.juteProcurement.formatters import (
    get_jute_po_number_sql_expression,
    get_jute_gate_entry_number_sql_expression,
)


def get_jute_po_table_query(co_id: int, search: str = None):
    """
    Query to get jute PO list with pagination support.
    Joins with branch_mst for co_id filtering, co_mst for company prefix,
    jute_supplier_mst for supplier name, jute_supp_party_map + party_mst for party details,
    jute_mukam_mst for mukam name, and status_mst for status name.
    
    PO number format: {co_prefix}/{branch_prefix}/JPO/{year}/{sequence:05d}
    """
    # Get the formatted PO number SQL expression
    po_num_expr = get_jute_po_number_sql_expression()
    
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jp.po_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jmm.mukam_name LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jp.jute_po_id,
            jp.po_no,
            {po_num_expr} AS po_num,
            jp.po_date,
            jp.party_id,
            jspm_latest.party_id AS party_id_from_map,
            pm.supp_name AS party_name,
            jp.supplier_id,
            jsm.supplier_name,
            jp.jute_mukam_id AS mukam_id,
            jmm.mukam_name AS mukam,
            jp.vehicle_type_id,
            jlm.lorry_type AS vehicle_type,
            jp.vehicle_quantity AS vehicle_qty,
            jp.status_id,
            COALESCE(sm.status_name, jp.status_id) AS status,
            jp.jute_po_value AS po_val_wt_tax,
            jp.jute_po_value AS po_val_wo_tax,
            jp.weight,
            jp.jute_uom AS jute_unit,
            jp.branch_id,
            jp.updated_date_time,
            jp.updated_by AS created_by
        FROM jute_po jp
        INNER JOIN branch_mst bm ON bm.branch_id = jp.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_lorry_mst jlm ON jlm.jute_lorry_type_id = jp.vehicle_type_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
        LEFT JOIN (
            SELECT jspm1.jute_supplier_id, jspm1.party_id
            FROM jute_supp_party_map jspm1
            INNER JOIN (
                SELECT jute_supplier_id, MAX(updated_date_time) as max_date
                FROM jute_supp_party_map
                GROUP BY jute_supplier_id
            ) jspm2 ON jspm1.jute_supplier_id = jspm2.jute_supplier_id 
                   AND jspm1.updated_date_time = jspm2.max_date
        ) jspm_latest ON jspm_latest.jute_supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jspm_latest.party_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.jute_mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jp.status_id
        WHERE bm.co_id = :co_id
        {search_clause}
        ORDER BY jp.po_date DESC, jp.jute_po_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_po_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of jute POs for pagination.
    Uses branch_mst to filter by co_id since jute_po doesn't have co_id column.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jp.po_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jmm.mukam_name LIKE :search
            )
        """

    sql = f"""
        SELECT COUNT(DISTINCT jp.jute_po_id) AS total
        FROM jute_po jp
        INNER JOIN branch_mst bm ON bm.branch_id = jp.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
        LEFT JOIN (
            SELECT jspm1.jute_supplier_id, jspm1.party_id
            FROM jute_supp_party_map jspm1
            INNER JOIN (
                SELECT jute_supplier_id, MAX(updated_date_time) as max_date
                FROM jute_supp_party_map
                GROUP BY jute_supplier_id
            ) jspm2 ON jspm1.jute_supplier_id = jspm2.jute_supplier_id 
                   AND jspm1.updated_date_time = jspm2.max_date
        ) jspm_latest ON jspm_latest.jute_supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jspm_latest.party_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.jute_mukam_id
        WHERE bm.co_id = :co_id
        {search_clause}
    """
    return text(sql)


def get_jute_po_by_id_query():
    """
    Query to get a single jute PO by ID.
    Uses branch_mst to filter by co_id since jute_po doesn't have co_id column.
    Includes formatted PO number with company and branch prefix.
    """
    po_num_expr = get_jute_po_number_sql_expression()
    
    sql = f"""
        SELECT 
            jp.jute_po_id,
            jp.po_no,
            {po_num_expr} AS po_num,
            jp.po_date,
            jp.party_id,
            pm.party_id,
            pm.supp_name AS supplier_name,
            jp.supplier_id,
            jsm.supplier_name AS broker_name,
            jp.jute_mukam_id AS mukam_id,
            jmm.mukam_name AS mukam,
            jp.vehicle_type_id,
            jlm.weight AS vehicle_capacity,
            jp.vehicle_quantity AS vehicle_qty,
            jp.status_id,
            COALESCE(sm.status_name, jp.status_id) AS status,
            jp.jute_po_value AS po_val_wt_tax,
            jp.jute_po_value AS po_val_wo_tax,
            jp.weight,
            jp.jute_uom AS jute_unit,
            jp.branch_id,
            jp.credit_term,
            jp.delivery_days AS delivery_timeline,
            jp.footer_note,
            jp.frieght_charge,
            jp.jute_indent_id AS indent_no,
            jp.remarks,
            jp.channel_code,
            jp.contract_no,
            jp.contract_date,
            jp.brokrage_rate,
            jp.brokrage_percentage,
            jp.penalty,
            jp.internal_note,
            jp.updated_date_time
        FROM jute_po jp
        INNER JOIN branch_mst bm ON bm.branch_id = jp.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_lorry_mst jlm ON jlm.jute_lorry_type_id = jp.vehicle_type_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jp.party_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.jute_mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jp.status_id
        WHERE jp.jute_po_id = :jute_po_id AND bm.co_id = :co_id
    """
    return text(sql)


def get_jute_po_line_items_query():
    """
    Query to get line items for a jute PO.
    Uses item_id and jute_quality_id for lookups.
    """
    sql = """
        SELECT 
            jpli.jute_po_li_id,
            jpli.jute_po_id,
            jpli.item_id,
            im.item_name AS item_name,
            jpli.jute_quality_id,
            jqm.jute_quality AS quality_name,
            jpli.crop_year,
            jpli.marka,
            jpli.quantity,
            jpli.rate,
            jpli.allowable_moisture,
            jpli.value AS amount,
            jpli.active,
            jpli.status_id,
            sm.status_name AS status
        FROM jute_po_li jpli
        LEFT JOIN item_mst im ON im.item_id = jpli.item_id
        LEFT JOIN jute_quality_mst jqm ON jqm.jute_qlty_id = jpli.jute_quality_id
        LEFT JOIN status_mst sm ON sm.status_id = jpli.status_id
        WHERE jpli.jute_po_id = :jute_po_id
        ORDER BY jpli.jute_po_li_id
    """
    return text(sql)


def get_mukam_list_query():
    """
    Query to get list of mukams.
    """
    sql = """
        SELECT 
            mukam_id,
            mukam_name
        FROM jute_mukam_mst
        ORDER BY mukam_name
    """
    return text(sql)


def get_vehicle_types_query():
    """
    Query to get list of vehicle/lorry types with weight capacity.
    """
    sql = """
        SELECT 
            jute_lorry_type_id AS vehicle_type_id,
            lorry_type AS vehicle_type,
            weight AS capacity_weight
        FROM jute_lorry_mst
        WHERE co_id = :co_id OR co_id IS NULL
        ORDER BY lorry_type
    """
    return text(sql)


def get_jute_items_query():
    """
    Query to get jute items (items where item group has item_type_id = 2).
    Joins item_mst -> item_grp_mst to filter by item_type_id.
    """
    sql = """
        SELECT 
            im.item_id,
            im.item_code,
            im.item_name,
            im.item_grp_id,
            ig.item_grp_name,
            im.uom_id AS default_uom_id,
            um.uom_name AS default_uom
        FROM item_mst im
        INNER JOIN item_grp_mst ig ON ig.item_grp_id = im.item_grp_id
        LEFT JOIN uom_mst um ON um.uom_id = im.uom_id
        WHERE ig.item_type_id = 2
        AND ig.co_id = :co_id
        AND (im.active = 1 OR im.active IS NULL)
        ORDER BY im.item_name
    """
    return text(sql)


def get_jute_qualities_by_item_query():
    """
    Query to get jute qualities for a specific item.
    """
    sql = """
        SELECT 
            jute_qlty_id AS quality_id,
            jute_quality AS quality_name,
            item_id
        FROM jute_quality_mst
        WHERE item_id = :item_id
        AND (co_id = :co_id OR co_id IS NULL)
        ORDER BY jute_quality
    """
    return text(sql)


def get_suppliers_by_mukam_query():
    """
    Query to get jute suppliers filtered by mukam.
    """
    sql = """
        SELECT 
            jsm.supplier_id,
            jsm.supplier_name AS supplier_name
        FROM jute_supplier_mst jsm
        ORDER BY jsm.supplier_name
    """
    return text(sql)


def get_parties_by_supplier_query():
    """
    Query to get parties mapped to a jute supplier.
    Uses jute_supp_party_map to find parties linked to the selected supplier.
    """
    sql = """
        SELECT
            pm.party_id,
            pm.supp_name AS party_name
        FROM party_mst pm
        JOIN jute_supp_party_map jspm
            ON jspm.party_id = pm.party_id
        WHERE jspm.jute_supplier_id = :supplier_id
        ORDER BY pm.supp_name
    """
    return text(sql)


def get_all_suppliers_query():
    """
    Query to get all jute suppliers for the company.
    Suppliers are mandatory for Jute PO creation.
    """
    sql = """
        SELECT 
            jsm.supplier_id AS supplier_id,
            jsm.supplier_name AS supplier_name
        FROM jute_supplier_mst jsm
        ORDER BY jsm.supplier_name
    """
    return text(sql)


def get_branches_query():
    """
    Query to get list of branches for the company.
    """
    sql = """
        SELECT 
            branch_id,
            branch_name
        FROM branch_mst
        WHERE co_id = :co_id
        AND (active = 1 OR active IS NULL)
        ORDER BY branch_name
    """
    return text(sql)


# =============================================================================
# JUTE GATE ENTRY QUERIES (using jute_mr table)
# =============================================================================

def get_jute_gate_entry_table_query(co_id: int, branch_ids: list = None, search: str = None):
    """
    Query to get jute gate entry list with pagination support.
    
    Updated 2026-01-15: Now uses jute_mr table (merged gate entry + MR).
    The old jute_gate_entry table was deleted - all gate entry data is now in jute_mr.
    
    Args:
        co_id: Company ID for filtering
        branch_ids: List of branch IDs to filter by (optional)
        search: Search term for gate entry no, challan no, or vehicle no
    
    Columns: gate entry no, gate entry date, in time, out time, challan no, 
    vehicle no, challan weight, gross weight.
    """
    # Get the formatted gate entry number SQL expression (using jm alias for jute_mr)
    gate_entry_num_expr = get_jute_gate_entry_number_sql_expression(
        gate_entry_no_column="jm.jute_gate_entry_no",
        entry_date_column="jm.jute_gate_entry_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.jute_gate_entry_no AS CHAR) LIKE :search
                OR jm.challan_no LIKE :search
                OR jm.vehicle_no LIKE :search
            )
        """
    
    # Branch filter clause - uses IN clause with branch_ids list
    branch_clause = ""
    if branch_ids and len(branch_ids) > 0:
        # Create placeholders for branch IDs
        branch_placeholders = ", ".join([f":branch_id_{i}" for i in range(len(branch_ids))])
        branch_clause = f"AND jm.branch_id IN ({branch_placeholders})"

    sql = f"""
        SELECT 
            jm.jute_mr_id,
            jm.jute_gate_entry_no,
            CASE 
                WHEN jm.jute_gate_entry_no IS NOT NULL 
                THEN {gate_entry_num_expr} 
                ELSE NULL 
            END AS gate_entry_num,
            jm.jute_gate_entry_date,
            jm.in_time,
            jm.out_date,
            jm.out_time,
            jm.challan_no,
            jm.challan_date,
            jm.challan_weight,
            jm.vehicle_no,
            jm.gross_weight,
            jm.tare_weight,
            jm.net_weight,
            jm.branch_id,
            bm.branch_name,
            jm.status_id,
            COALESCE(sm.status_name, 'IN') AS status,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE bm.co_id = :co_id
        AND jm.jute_gate_entry_no IS NOT NULL
        {branch_clause}
        {search_clause}
        ORDER BY jm.jute_gate_entry_date DESC, jm.jute_mr_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_gate_entry_table_count_query(co_id: int, branch_ids: list = None, search: str = None):
    """
    Query to get total count of jute gate entries for pagination.
    
    Updated 2026-01-15: Now uses jute_mr table (merged gate entry + MR).
    
    Args:
        co_id: Company ID for filtering
        branch_ids: List of branch IDs to filter by (optional)
        search: Search term for gate entry no, challan no, or vehicle no
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.jute_gate_entry_no AS CHAR) LIKE :search
                OR jm.challan_no LIKE :search
                OR jm.vehicle_no LIKE :search
            )
        """
    
    # Branch filter clause - uses IN clause with branch_ids list
    branch_clause = ""
    if branch_ids and len(branch_ids) > 0:
        # Create placeholders for branch IDs
        branch_placeholders = ", ".join([f":branch_id_{i}" for i in range(len(branch_ids))])
        branch_clause = f"AND jm.branch_id IN ({branch_placeholders})"

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        WHERE bm.co_id = :co_id
        AND jm.jute_gate_entry_no IS NOT NULL
        {branch_clause}
        {search_clause}
    """
    return text(sql)


# =============================================================================
# JUTE GATE ENTRY DETAIL QUERIES (using jute_mr table)
# =============================================================================

def get_jute_gate_entry_by_id_query():
    """
    Query to get a single jute gate entry by ID.
    
    Updated 2026-01-15: Now uses jute_mr table (merged gate entry + MR).
    Includes formatted PO number and gate entry number with company and branch prefix.
    """
    # Get the formatted PO number SQL expression (using jp alias for jute_po)
    po_num_expr = get_jute_po_number_sql_expression(
        po_no_column="jp.po_no",
        po_date_column="jp.po_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    # Get the formatted gate entry number SQL expression
    gate_entry_num_expr = get_jute_gate_entry_number_sql_expression(
        gate_entry_no_column="jm.jute_gate_entry_no",
        entry_date_column="jm.jute_gate_entry_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    sql = f"""
        SELECT 
            jm.jute_mr_id,
            jm.jute_gate_entry_no,
            CASE 
                WHEN jm.jute_gate_entry_no IS NOT NULL 
                THEN {gate_entry_num_expr} 
                ELSE NULL 
            END AS gate_entry_num,
            jm.branch_id,
            bm.branch_name,
            jm.jute_gate_entry_date,
            jm.in_time,
            jm.out_date,
            jm.out_time,
            jm.challan_no,
            jm.challan_date,
            jm.challan_weight,
            jm.vehicle_no,
            jm.driver_name,
            jm.transporter,
            jm.po_id,
            jp.po_no,
            CASE WHEN jp.jute_po_id IS NOT NULL THEN {po_num_expr} ELSE NULL END AS po_num,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.mukam_id,
            jmm.mukam_name AS mukam,
            jm.unit_conversion AS jute_uom,
            jm.gross_weight,
            jm.tare_weight,
            jm.net_weight,
            jm.variable_shortage,
            jm.actual_weight,
            jm.remarks,
            jm.status_id,
            COALESCE(sm.status_name, 'IN') AS status,
            jm.qc_check,
            jm.marketing_slip,
            jm.updated_by,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jm.po_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jm.party_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE jm.jute_mr_id = :jute_mr_id AND bm.co_id = :co_id
    """
    return text(sql)


def get_jute_gate_entry_line_items_query():
    """
    Query to get line items for a jute gate entry.
    
    Updated 2026-01-16: Fixed column names to match actual jute_mr_li table schema.
    - challan_quality_id (not challan_jute_quality_id)
    - actual_quality (not actual_jute_quality_id)
    - actual_qty (not actual_quantity)
    - unit_conversion from jute_mr header (not jute_uom)
    """
    sql = """
        SELECT 
            jmli.jute_mr_li_id,
            jmli.jute_mr_id,
            jmli.jute_po_li_id,
            jmli.challan_item_id,
            im_ch.item_name AS challan_item_name,
            jmli.challan_quality_id,
            jqm_ch.jute_quality AS challan_quality_name,
            jmli.challan_quantity,
            jmli.challan_weight,
            jmli.actual_item_id,
            im_act.item_name AS actual_item_name,
            jmli.actual_quality AS actual_quality_id,
            jqm_act.jute_quality AS actual_quality_name,
            jmli.actual_qty,
            jmli.actual_weight,
            jmli.allowable_moisture,
            jm.unit_conversion,
            jmli.remarks,
            jmli.active
        FROM jute_mr_li jmli
        INNER JOIN jute_mr jm ON jm.jute_mr_id = jmli.jute_mr_id
        LEFT JOIN item_mst im_ch ON im_ch.item_id = jmli.challan_item_id
        LEFT JOIN jute_quality_mst jqm_ch ON jqm_ch.jute_qlty_id = jmli.challan_quality_id
        LEFT JOIN item_mst im_act ON im_act.item_id = jmli.actual_item_id
        LEFT JOIN jute_quality_mst jqm_act ON jqm_act.jute_qlty_id = jmli.actual_quality
        WHERE jmli.jute_mr_id = :jute_mr_id
        AND (jmli.active = 1 OR jmli.active IS NULL)
        ORDER BY jmli.jute_mr_li_id
    """
    return text(sql)


def get_jute_po_for_gate_entry_query():
    """
    Query to get PO details for gate entry auto-fill (when PO is selected).
    Returns PO header and line items.
    """
    sql = """
        SELECT 
            jp.jute_po_id,
            jp.po_no,
            jp.po_date,
            jp.supplier_id,
            jsm.supplier_name,
            jp.party_id,
            pm.supp_name AS party_name,
            jp.jute_mukam_id AS mukam_id,
            jmm.mukam_name,
            jp.jute_uom,
            jp.branch_id
        FROM jute_po jp
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jp.party_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.jute_mukam_id
        INNER JOIN branch_mst bm ON bm.branch_id = jp.branch_id
        WHERE jp.jute_po_id = :po_id AND bm.co_id = :co_id
    """
    return text(sql)


def get_jute_po_line_items_for_gate_entry_query():
    """
    Query to get PO line items for gate entry auto-fill.
    Uses new columns: item_id, jute_quality_id.
    """
    sql = """
        SELECT 
            jpli.jute_po_li_id,
            jpli.item_id,
            im.item_name AS item_name,
            jpli.jute_quality_id AS quality_id,
            jqm.jute_quality AS quality_name,
            jpli.quantity,
            jpli.value AS amount,
            jpli.allowable_moisture
        FROM jute_po_li jpli
        LEFT JOIN item_mst im ON im.item_id = jpli.item_id
        LEFT JOIN jute_quality_mst jqm ON jqm.jute_qlty_id = jpli.jute_quality_id
        WHERE jpli.jute_po_id = :po_id AND (jpli.active = 1 OR jpli.active IS NULL)
        ORDER BY jpli.jute_po_li_id
    """
    return text(sql)


def get_open_jute_pos_query():
    """
    Query to get list of approved Jute POs for selection in gate entry.
    Only shows POs with status_id = 3 (Approved).
    Formats PO number with company and branch prefix.
    """
    po_num_expr = get_jute_po_number_sql_expression()
    
    sql = f"""
        SELECT 
            jp.jute_po_id,
            {po_num_expr} AS po_num,
            jp.po_date,
            jp.branch_id,
            jsm.supplier_name,
            jp.supplier_id,
            jmm.mukam_name,
            jp.weight AS total_weight,
            jp.jute_uom
        FROM jute_po jp
        INNER JOIN branch_mst bm ON bm.branch_id = jp.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.jute_mukam_id
        WHERE bm.co_id = :co_id
        AND jp.status_id = 3
        ORDER BY jp.po_date DESC, jp.jute_po_id DESC
    """
    return text(sql)


# =============================================================================
# JUTE QUALITY CHECK QUERIES (using jute_mr table)
# =============================================================================

def get_material_inspection_table_query(co_id: int, branch_ids: list = None, search: str = None):
    """
    Query to get jute MR entries pending QC check (qc_check IS NULL or qc_check = 0).
    Returns entries that need quality inspection.
    
    Updated 2026-01-16: Now uses jute_mr table (merged gate entry + MR).
    The old jute_gate_entry table was deleted.
    
    Args:
        co_id: Company ID for filtering
        branch_ids: List of branch IDs to filter by (optional)
        search: Search term
    """
    # Get the formatted gate entry number SQL expression
    gate_entry_num_expr = get_jute_gate_entry_number_sql_expression(
        gate_entry_no_column="jm.jute_gate_entry_no",
        entry_date_column="jm.jute_gate_entry_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.jute_mr_id AS CHAR) LIKE :search
                OR CAST(jm.jute_gate_entry_no AS CHAR) LIKE :search
                OR jmm.mukam_name LIKE :search
                OR jm.vehicle_no LIKE :search
                OR jm.challan_no LIKE :search
            )
        """
    
    # Branch filter clause
    branch_clause = ""
    if branch_ids and len(branch_ids) > 0:
        branch_placeholders = ", ".join([f":branch_id_{i}" for i in range(len(branch_ids))])
        branch_clause = f"AND jm.branch_id IN ({branch_placeholders})"

    sql = f"""
        SELECT 
            jm.jute_mr_id,
            jm.jute_gate_entry_no,
            CASE 
                WHEN jm.jute_gate_entry_no IS NOT NULL 
                THEN {gate_entry_num_expr} 
                ELSE NULL 
            END AS gate_entry_num,
            jm.branch_id,
            bm.branch_name,
            jm.jute_gate_entry_date,
            jm.unit_conversion,
            jm.mukam_id,
            jmm.mukam_name AS mukam,
            jm.vehicle_no,
            jm.challan_no,
            jm.challan_weight,
            jm.gross_weight,
            jm.tare_weight,
            jm.net_weight,
            jm.variable_shortage,
            jm.qc_check,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.status_id,
            COALESCE(sm.status_name, 'Pending QC') AS status,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jm.party_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE bm.co_id = :co_id
        AND jm.jute_gate_entry_no IS NOT NULL
        AND (jm.qc_check IS NULL OR jm.qc_check = 0)
        {branch_clause}
        {search_clause}
        ORDER BY jm.jute_gate_entry_date DESC, jm.jute_mr_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_material_inspection_table_count_query(co_id: int, branch_ids: list = None, search: str = None):
    """
    Query to get total count of jute MR entries pending QC check.
    
    Updated 2026-01-16: Now uses jute_mr table (merged gate entry + MR).
    
    Args:
        co_id: Company ID for filtering
        branch_ids: List of branch IDs to filter by (optional)
        search: Search term
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.jute_mr_id AS CHAR) LIKE :search
                OR CAST(jm.jute_gate_entry_no AS CHAR) LIKE :search
                OR jmm.mukam_name LIKE :search
                OR jm.vehicle_no LIKE :search
                OR jm.challan_no LIKE :search
            )
        """
    
    # Branch filter clause
    branch_clause = ""
    if branch_ids and len(branch_ids) > 0:
        branch_placeholders = ", ".join([f":branch_id_{i}" for i in range(len(branch_ids))])
        branch_clause = f"AND jm.branch_id IN ({branch_placeholders})"

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        WHERE bm.co_id = :co_id
        AND jm.jute_gate_entry_no IS NOT NULL
        AND (jm.qc_check IS NULL OR jm.qc_check = 0)
        {branch_clause}
        {search_clause}
    """
    return text(sql)


def get_material_inspection_by_id_query():
    """
    Query to get a single jute MR entry for quality check/material inspection.
    
    Updated 2026-01-16: Now uses jute_mr table (merged gate entry + MR).
    """
    # Get the formatted gate entry number SQL expression
    gate_entry_num_expr = get_jute_gate_entry_number_sql_expression(
        gate_entry_no_column="jm.jute_gate_entry_no",
        entry_date_column="jm.jute_gate_entry_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    sql = f"""
        SELECT 
            jm.jute_mr_id,
            jm.jute_gate_entry_no,
            CASE 
                WHEN jm.jute_gate_entry_no IS NOT NULL 
                THEN {gate_entry_num_expr} 
                ELSE NULL 
            END AS gate_entry_num,
            jm.branch_id,
            bm.branch_name,
            jm.jute_gate_entry_date,
            jm.unit_conversion,
            jm.mukam_id,
            jmm.mukam_name AS mukam,
            jm.vehicle_no,
            jm.challan_no,
            jm.challan_date,
            jm.challan_weight,
            jm.gross_weight,
            jm.tare_weight,
            jm.net_weight,
            jm.variable_shortage,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.po_id,
            jm.qc_check,
            jm.status_id,
            COALESCE(sm.status_name, 'Pending QC') AS status,
            jm.remarks,
            jm.updated_by,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jm.party_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE jm.jute_mr_id = :jute_mr_id
    """
    return text(sql)


def get_material_inspection_line_items_query():
    """
    Query to get line items for quality check/material inspection.
    
    Updated 2026-01-16: Now uses jute_mr_li table.
    """
    sql = """
        SELECT 
            jmli.jute_mr_li_id,
            jmli.jute_mr_id,
            jmli.jute_po_li_id,
            
            -- Challan details
            jmli.challan_item_id,
            im_ch.item_name AS challan_item_name,
            jmli.challan_jute_quality_id,
            jqm_ch.jute_quality AS challan_quality_name,
            jmli.challan_quantity,
            jmli.challan_weight,
            
            -- Actual (received) details
            jmli.actual_item_id,
            im_act.item_name AS actual_item_name,
            jmli.actual_jute_quality_id,
            jqm_act.jute_quality AS actual_quality_name,
            jmli.actual_quantity,
            jmli.actual_weight,
            
            -- QC fields
            jmli.allowable_moisture,
            jmli.actual_moisture,
            jmli.accepted_weight,
            jmli.rate,
            jmli.warehouse_id,
            jmli.marka,
            jmli.crop_year,
            
            jmli.jute_uom,
            jmli.remarks,
            jmli.active
        FROM jute_mr_li jmli
        LEFT JOIN item_mst im_ch ON im_ch.item_id = jmli.challan_item_id
        LEFT JOIN jute_quality_mst jqm_ch ON jqm_ch.jute_qlty_id = jmli.challan_jute_quality_id
        LEFT JOIN item_mst im_act ON im_act.item_id = jmli.actual_item_id
        LEFT JOIN jute_quality_mst jqm_act ON jqm_act.jute_qlty_id = jmli.actual_jute_quality_id
        WHERE jmli.jute_mr_id = :jute_mr_id
        AND (jmli.active = 1 OR jmli.active IS NULL)
        ORDER BY jmli.jute_mr_li_id
    """
    return text(sql)


def update_material_inspection_qc_complete():
    """
    Query to mark a jute MR entry as QC complete (qc_check = 1).
    
    Updated 2026-01-16: Now uses jute_mr table (merged gate entry + MR).
    Changed qc_check from 'Y' to 1 (integer flag).
    """
    sql = """
        UPDATE jute_mr
        SET qc_check = 1,
            updated_by = :updated_by,
            updated_date_time = :updated_date_time
        WHERE jute_mr_id = :jute_mr_id
    """
    return text(sql)


def insert_jute_mr_query():
    """
    Query to insert a new jute MR (Material Receipt) record.
    This is created when material inspection is completed.
    """
    sql = """
        INSERT INTO jute_mr (
            branch_id, branch_mr_no, jute_mr_date,
            jute_gate_entry_no, jute_gate_entry_date, 
            challan_no, challan_date,
            jute_supplier_id, party_id, mukam_id, unit_conversion,
            po_id, mr_weight, vehicle_no, status_id, remarks,
            updated_by, updated_date_time
        ) VALUES (
            :branch_id, :branch_mr_no, :jute_mr_date,
            :jute_gate_entry_no, :jute_gate_entry_date,
            :challan_no, :challan_date,
            :jute_supplier_id, :party_id, :mukam_id, :unit_conversion,
            :po_id, :mr_weight, :vehicle_no, :status_id, :remarks,
            :updated_by, :updated_date_time
        )
    """
    return text(sql)


def insert_jute_mr_li_query():
    """
    Query to insert a jute MR line item with QC data.
    QC data is now stored here instead of jute_gate_entry_li.
    """
    sql = """
        INSERT INTO jute_mr_li (
            jute_mr_id, jute_po_li_id,
            challan_item_id, challan_quality_id, challan_quantity, challan_weight,
            actual_item_id, actual_quality, actual_qty, actual_weight,
            allowable_moisture, actual_moisture, accepted_weight,
            rate, warehouse_id, marka, crop_year,
            remarks, status, active, updated_date_time
        ) VALUES (
            :jute_mr_id, :jute_po_li_id,
            :challan_item_id, :challan_quality_id, :challan_quantity, :challan_weight,
            :actual_item_id, :actual_quality, :actual_qty, :actual_weight,
            :allowable_moisture, :actual_moisture, :accepted_weight,
            :rate, :warehouse_id, :marka, :crop_year,
            :remarks, :status, 1, :updated_date_time
        )
    """
    return text(sql)


def insert_jute_moisture_rdg_query():
    """
    Query to insert moisture readings for a jute MR line item.
    """
    sql = """
        INSERT INTO jute_moisture_rdg (
            jute_mr_li_id, moisture_percentage
        ) VALUES (
            :jute_mr_li_id, :moisture_percentage
        )
    """
    return text(sql)


def get_moisture_readings_by_mr_li_id_query():
    """
    Query to get moisture readings for a specific jute MR line item.
    """
    sql = """
        SELECT 
            jute_moisture_rdg_id,
            jute_mr_li_id,
            moisture_percentage
        FROM jute_moisture_rdg
        WHERE jute_mr_li_id = :jute_mr_li_id
        ORDER BY jute_moisture_rdg_id
    """
    return text(sql)


def delete_moisture_readings_query():
    """
    Query to delete all moisture readings for a specific jute MR line item.
    """
    sql = """
        DELETE FROM jute_moisture_rdg
        WHERE jute_mr_li_id = :jute_mr_li_id
    """
    return text(sql)


def update_mr_li_actual_moisture_query():
    """
    Query to update actual_moisture on jute_mr_li for a specific line item.
    """
    sql = """
        UPDATE jute_mr_li
        SET actual_moisture = :actual_moisture
        WHERE jute_mr_li_id = :jute_mr_li_id
    """
    return text(sql)


def update_mr_li_accepted_weight_query():
    """
    Query to update accepted_weight on jute_mr_li for a specific line item.
    """
    sql = """
        UPDATE jute_mr_li
        SET accepted_weight = :accepted_weight
        WHERE jute_mr_li_id = :jute_mr_li_id
    """
    return text(sql)


# =============================================================================
# JUTE MR (MATERIAL RECEIPT) QUERIES
# =============================================================================

def get_jute_mr_table_query(co_id: int, search: str = None):
    """
    Query to get jute MR list with pagination support.
    Joins with branch_mst for co_id filtering, jute_supplier_mst for supplier name,
    party_mst for party details, jute_po for PO number, and jute_mukam_mst for mukam.
    
    Only shows entries where out_time IS NOT NULL (vehicle has exited).
    Entries without out_time continue to show in the gate entry table.
    """
    # Get the formatted gate entry number SQL expression
    gate_entry_num_expr = get_jute_gate_entry_number_sql_expression(
        gate_entry_no_column="jm.jute_gate_entry_no",
        entry_date_column="jm.jute_gate_entry_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.branch_mr_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jm.challan_no LIKE :search
                OR jm.vehicle_no LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jm.jute_mr_id,
            jm.branch_mr_no,
            jm.jute_mr_date,
            jm.branch_id,
            bm.branch_name,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.party_branch_id,
            pb.branch_name AS party_branch_name,
            jm.po_id,
            jp.po_no,
            jp.po_date,
            jm.challan_no,
            jm.challan_date,
            jm.mukam_id,
            jmm.mukam_name AS mukam,
            jm.vehicle_no,
            jm.unit_conversion,
            jm.mr_weight,
            jm.remarks,
            jm.status_id,
            COALESCE(sm.status_name, 'Open') AS status,
            jm.src_com_id,
            jm.jute_gate_entry_no,
            jm.jute_gate_entry_date,
            CASE 
                WHEN jm.jute_gate_entry_no IS NOT NULL 
                THEN {gate_entry_num_expr}
                ELSE NULL 
            END AS gate_entry_no,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        LEFT JOIN branch_mst pb ON pb.branch_id = jm.party_branch_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jm.po_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE bm.co_id = :co_id
        AND jm.out_time IS NOT NULL
        {search_clause}
        ORDER BY jm.jute_mr_date DESC, jm.jute_mr_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_mr_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of jute MRs for pagination.
    Only counts entries where out_time IS NOT NULL (vehicle has exited).
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.branch_mr_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jm.challan_no LIKE :search
                OR jm.vehicle_no LIKE :search
            )
        """

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        WHERE bm.co_id = :co_id
        AND jm.out_time IS NOT NULL
        {search_clause}
    """
    return text(sql)


def get_jute_mr_by_id_query():
    """
    Query to get a single jute MR by ID with all header details.
    """
    sql = """
        SELECT 
            jm.jute_mr_id,
            jm.branch_mr_no,
            jm.jute_mr_date,
            jm.branch_id,
            bm.branch_name,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.party_branch_id,
            pb.branch_name AS party_branch_name,
            jm.po_id,
            jp.po_no,
            jp.po_date,
            jm.challan_no,
            jm.challan_date,
            jm.mukam_id,
            jmm.mukam_name AS mukam,
            jm.vehicle_no,
            jm.unit_conversion,
            jm.mr_weight,
            jm.remarks,
            jm.status_id,
            COALESCE(sm.status_name, 'Open') AS status,
            jm.src_com_id,
            jm.jute_gate_entry_date,
            jm.updated_by,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        LEFT JOIN branch_mst pb ON pb.branch_id = jm.party_branch_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jm.po_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE jm.jute_mr_id = :mr_id
    """
    return text(sql)


def get_jute_mr_line_items_query():
    """
    Query to get line items for a jute MR.
    Includes warehouse_path using recursive CTE similar to item_group_path.
    Joins with jute_po_li to get rate from PO if not set on MR line item.
    """
    sql = """
        WITH RECURSIVE warehouse_hierarchy AS (
            SELECT 
                wm.warehouse_id,
                wm.branch_id,
                wm.warehouse_name,
                wm.parent_warehouse_id,
                CAST(wm.warehouse_name AS CHAR(500)) AS warehouse_path
            FROM warehouse_mst wm
            WHERE wm.parent_warehouse_id IS NULL
            UNION ALL
            SELECT 
                child.warehouse_id,
                child.branch_id,
                child.warehouse_name,
                child.parent_warehouse_id,
                CONCAT(parent.warehouse_path, '-', child.warehouse_name)
            FROM warehouse_mst child
            JOIN warehouse_hierarchy parent 
                ON child.parent_warehouse_id = parent.warehouse_id
        )
        SELECT 
            jmli.jute_mr_li_id,
            jmli.jute_mr_id,
            jmli.jute_po_li_id,
            jmli.actual_item_id,
            im.item_name AS actual_item_name,
            jmli.actual_quality,
            jqm.jute_quality AS actual_quality_name,
            jmli.actual_qty,
            jmli.actual_weight,
            jmli.allowable_moisture,
            jmli.actual_moisture,
            jmli.claim_dust,
            jmli.shortage_kgs,
            jmli.accepted_weight,
            COALESCE(NULLIF(jmli.rate, 0), jpli.rate) AS rate,
            jpli.rate AS po_rate,
            jmli.claim_rate,
            jmli.claim_quality,
            jmli.water_damage_amount,
            jmli.premium_amount,
            jmli.warehouse_id,
            wh.warehouse_path,
            jmli.remarks,
            jmli.status,
            jmli.active
        FROM jute_mr_li jmli
        LEFT JOIN item_mst im ON im.item_id = jmli.actual_item_id
        LEFT JOIN jute_quality_mst jqm ON jqm.jute_qlty_id = jmli.actual_quality
        LEFT JOIN warehouse_hierarchy wh ON wh.warehouse_id = jmli.warehouse_id
        LEFT JOIN jute_po_li jpli ON jpli.jute_po_li_id = jmli.jute_po_li_id
        WHERE jmli.jute_mr_id = :mr_id
        AND (jmli.active = 1 OR jmli.active IS NULL)
        ORDER BY jmli.jute_mr_li_id
    """
    return text(sql)


def get_all_active_company_branches_query():
    """
    Query to get all active branches from all companies.
    Used for agent selection dropdown.
    Returns company name and branch name for display.
    """
    sql = """
        SELECT 
            bm.branch_id,
            cm.co_name AS company_name,
            bm.branch_name
        FROM branch_mst bm
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        WHERE (bm.active = 1 OR bm.active IS NULL)
        ORDER BY cm.co_name, bm.branch_name
    """
    return text(sql)


def get_agent_map_options_query():
    """
    Query to get agent options from jute_agent_map table.
    Returns agent branch info with party branch details.
    Used for agent selection dropdown in MR.
    """
    sql = """
        SELECT DISTINCT
            jam.agent_branch_id,
            cm.co_name AS company_name,
            bm.branch_name,
            CONCAT(cm.co_name, ' - ', bm.branch_name) AS display
        FROM jute_agent_map jam
        INNER JOIN branch_mst bm ON bm.branch_id = jam.agent_branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        WHERE jam.co_id = :co_id
            AND (bm.active = 1 OR bm.active IS NULL)
        ORDER BY cm.co_name, bm.branch_name
    """
    return text(sql)


def get_warehouse_options_query():
    """
    Query to get warehouse options with recursive path for dropdowns.
    Uses same recursive logic as warehouse master page.
    """
    sql = """
        WITH RECURSIVE warehouse_hierarchy AS (
            SELECT 
                wm.warehouse_id,
                wm.branch_id,
                wm.warehouse_name,
                wm.parent_warehouse_id,
                CAST(wm.warehouse_name AS CHAR(500)) AS warehouse_path
            FROM warehouse_mst wm
            WHERE wm.parent_warehouse_id IS NULL
                AND wm.branch_id = :branch_id
            UNION ALL
            SELECT 
                child.warehouse_id,
                child.branch_id,
                child.warehouse_name,
                child.parent_warehouse_id,
                CONCAT(parent.warehouse_path, '-', child.warehouse_name)
            FROM warehouse_mst child
            JOIN warehouse_hierarchy parent 
                ON child.parent_warehouse_id = parent.warehouse_id
            WHERE child.branch_id = :branch_id
        )
        SELECT 
            wh.warehouse_id,
            wh.warehouse_name,
            wh.warehouse_path
        FROM warehouse_hierarchy wh
        ORDER BY wh.warehouse_path
    """
    return text(sql)


# =============================================================================
# JUTE BILL PASS QUERIES
# =============================================================================

def get_jute_bill_pass_table_query(co_id: int, search: str = None):
    """
    Query to get jute bill pass list with pagination support.
    Bill passes are approved MRs (status_id = 3) from jute_mr table.
    
    Returns columns: bill_pass_no, bill_pass_date, mr_no, supplier, party, 
                     invoice_no, invoice_date, amount (net_total)
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.bill_pass_no AS CHAR) LIKE :search
                OR CAST(jm.branch_mr_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jm.invoice_no LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jm.jute_mr_id,
            jm.bill_pass_no,
            jm.bill_pass_date,
            jm.branch_mr_no AS mr_no,
            jm.jute_mr_date AS mr_date,
            jm.branch_id,
            bm.branch_name,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.invoice_no,
            jm.invoice_date,
            jm.invoice_amount,
            jm.total_amount,
            jm.claim_amount,
            jm.roundoff,
            jm.net_total AS amount,
            jm.tds_amount,
            jm.payment_due_date,
            jm.status_id,
            COALESCE(sm.status_name, 'Approved') AS status,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE bm.co_id = :co_id
        AND jm.status_id = 3
        {search_clause}
        ORDER BY jm.bill_pass_date DESC, jm.bill_pass_no DESC, jm.jute_mr_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_bill_pass_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of jute bill passes for pagination.
    Counts only approved MRs (status_id = 3).
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jm.bill_pass_no AS CHAR) LIKE :search
                OR CAST(jm.branch_mr_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jm.invoice_no LIKE :search
            )
        """

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        WHERE bm.co_id = :co_id
        AND jm.status_id = 3
        {search_clause}
    """
    return text(sql)


def get_jute_bill_pass_by_id_query():
    """
    Query to get a single jute bill pass (approved MR) by ID with all details.
    """
    sql = """
        SELECT 
            jm.jute_mr_id,
            jm.bill_pass_no,
            jm.bill_pass_date,
            jm.branch_mr_no AS mr_no,
            jm.jute_mr_date AS mr_date,
            jm.branch_id,
            bm.branch_name,
            jm.jute_supplier_id,
            jsm.supplier_name,
            jm.party_id,
            pm.supp_name AS party_name,
            jm.party_branch_id,
            pb.branch_name AS party_branch_name,
            jm.po_id,
            jp.po_no,
            jm.challan_no,
            jm.challan_date,
            jm.mukam_id,
            jmm.mukam_name AS mukam,
            jm.vehicle_no,
            jm.mr_weight,
            jm.invoice_no,
            jm.invoice_date,
            jm.invoice_amount,
            jm.invoice_received_date,
            jm.total_amount,
            jm.claim_amount,
            jm.roundoff,
            jm.net_total AS amount,
            jm.tds_amount,
            jm.payment_due_date,
            jm.invoice_upload,
            jm.challan_upload,
            jm.remarks,
            jm.status_id,
            COALESCE(sm.status_name, 'Approved') AS status,
            jm.updated_by,
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        LEFT JOIN branch_mst pb ON pb.branch_id = jm.party_branch_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jm.po_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE jm.jute_mr_id = :jute_mr_id 
        AND jm.status_id = 3
        AND bm.co_id = :co_id
    """
    return text(sql)
