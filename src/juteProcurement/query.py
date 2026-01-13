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
            jspm.supp_code,
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
        LEFT JOIN jute_supp_party_map jspm ON jspm.jute_supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.supp_code = jspm.supp_code
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
        SELECT COUNT(*) AS total
        FROM jute_po jp
        INNER JOIN branch_mst bm ON bm.branch_id = jp.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
        LEFT JOIN jute_supp_party_map jspm ON jspm.jute_supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.supp_code = jspm.supp_code
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
            pm.supp_code,
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
        LEFT JOIN jute_supp_party_map jspm ON jspm.jute_supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jspm.party_id
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
        WHERE (jsm.co_id = :co_id OR jsm.co_id IS NULL)
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
        WHERE (jsm.co_id = :co_id OR jsm.co_id IS NULL)
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
# JUTE GATE ENTRY QUERIES
# =============================================================================

def get_jute_gate_entry_table_query(co_id: int, search: str = None):
    """
    Query to get jute gate entry list with pagination support.
    Joins with branch_mst for co_id filtering, co_mst for company prefix,
    jute_supplier_mst for supplier name, jute_supp_party_map + party_mst for party details,
    jute_po for PO number, and status_mst for status name.
    Includes formatted PO number and gate entry number with company and branch prefix.
    """
    # Get the formatted PO number SQL expression (using jp alias for jute_po)
    po_num_expr = get_jute_po_number_sql_expression(
        po_no_column="jp.po_no",
        po_date_column="jp.po_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jp.po_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jge.vehicle_no LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jge.jute_gate_entry_id,
            jge.branch_gate_entry_no,
            jge.branch_id,
            bm.branch_name,
            jge.po_id,
            jp.po_no,
            CASE WHEN jp.jute_po_id IS NOT NULL THEN {po_num_expr} ELSE NULL END AS po_num,
            jge.jute_gate_entry_date,
            jge.in_time,
            jge.out_date,
            jge.out_time,
            jge.jute_supplier_id,
            jsm.supplier_name,
            jge.party_id,
            pm.supp_name AS party_name,
            jge.vehicle_no,
            jge.vehicle_type_id,
            jge.challan_no,
            jge.challan_date,
            jge.gross_weight,
            jge.tare_weight,
            jge.net_weight,
            jge.status_id,
            COALESCE(sm.status_name, 'Pending') AS status,
            jge.updated_date_time
        FROM jute_gate_entry jge
        INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jge.po_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jge.jute_supplier_id
        LEFT JOIN jute_supp_party_map jspm ON jspm.map_id = jge.party_id
        LEFT JOIN party_mst pm ON pm.supp_code = jspm.supp_code
        LEFT JOIN status_mst sm ON sm.status_id = jge.status_id
        WHERE bm.co_id = :co_id
        {search_clause}
        ORDER BY jge.jute_gate_entry_date DESC, jge.jute_gate_entry_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_gate_entry_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of jute gate entries for pagination.
    Uses branch_mst to filter by co_id since jute_gate_entry doesn't have co_id column.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jp.po_no AS CHAR) LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jge.vehicle_no LIKE :search
            )
        """

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_gate_entry jge
        INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jge.po_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jge.jute_supplier_id
        LEFT JOIN jute_supp_party_map jspm ON jspm.map_id = jge.party_id
        LEFT JOIN party_mst pm ON pm.supp_code = jspm.supp_code
        WHERE bm.co_id = :co_id
        {search_clause}
    """
    return text(sql)


# =============================================================================
# JUTE GATE ENTRY DETAIL QUERIES
# =============================================================================

def get_jute_gate_entry_by_id_query():
    """
    Query to get a single jute gate entry by ID.
    Includes formatted PO number with company and branch prefix.
    """
    # Get the formatted PO number SQL expression (using jp alias for jute_po)
    po_num_expr = get_jute_po_number_sql_expression(
        po_no_column="jp.po_no",
        po_date_column="jp.po_date",
        co_prefix_column="cm.co_prefix",
        branch_prefix_column="bm.branch_prefix"
    )
    
    sql = f"""
        SELECT 
            jge.jute_gate_entry_id,
            jge.branch_gate_entry_no,
            jge.branch_id,
            bm.branch_name,
            jge.jute_gate_entry_date,
            jge.in_time,
            jge.out_date,
            jge.out_time,
            jge.challan_no,
            jge.challan_date,
            jge.challan_weight,
            jge.vehicle_no,
            jge.vehicle_type_id,
            jge.driver_name,
            jge.transporter,
            jge.po_id,
            jp.po_no,
            CASE WHEN jp.jute_po_id IS NOT NULL THEN {po_num_expr} ELSE NULL END AS po_num,
            jge.jute_supplier_id,
            jsm.supplier_name,
            jge.party_id,
            jspm.supp_code,
            pm.supp_name AS party_name,
            jge.mukam_id,
            jmm.mukam_name AS mukam,
            jge.unit_conversion AS jute_uom,
            jge.gross_weight,
            jge.tare_weight,
            jge.net_weight,
            jge.variable_shortage,
            jge.actual_weight,
            jge.remarks,
            jge.status_id,
            COALESCE(sm.status_name, 'Pending') AS status,
            jge.qc_check,
            jge.updated_by,
            jge.updated_date_time
        FROM jute_gate_entry jge
        INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
        INNER JOIN co_mst cm ON cm.co_id = bm.co_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jge.po_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jge.jute_supplier_id
        LEFT JOIN jute_supp_party_map jspm ON jspm.jute_supplier_id = jge.jute_supplier_id AND jspm.map_id = jge.party_id
        LEFT JOIN party_mst pm ON pm.supp_code = jspm.supp_code
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jge.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jge.status_id
        WHERE jge.jute_gate_entry_id = :jute_gate_entry_id AND bm.co_id = :co_id
    """
    return text(sql)


def get_jute_gate_entry_line_items_query():
    """
    Query to get line items for a jute gate entry.
    Updated: challan_item_name_id renamed to challan_item_id, QC fields removed (now in jute_mr_li).
    """
    sql = """
        SELECT 
            jgli.jute_gate_entry_li_id,
            jgli.jute_gate_entry_id,
            jgli.po_line_item_num,
            jgli.challan_item_id,
            im_ch.item_name AS challan_item_name,
            jgli.challan_jute_quality_id,
            jqm_ch.jute_quality AS challan_quality_name,
            jgli.challan_quantity,
            jgli.challan_weight,
            jgli.actual_item_id,
            im_act.item_name AS actual_item_name,
            jgli.actual_jute_quality_id,
            jqm_act.jute_quality AS actual_quality_name,
            jgli.actual_quantity,
            jgli.actual_weight,
            jgli.allowable_moisture,
            jgli.jute_uom,
            jgli.remarks,
            jgli.active
        FROM jute_gate_entry_li jgli
        LEFT JOIN item_mst im_ch ON im_ch.item_id = jgli.challan_item_id
        LEFT JOIN jute_quality_mst jqm_ch ON jqm_ch.jute_qlty_id = jgli.challan_jute_quality_id
        LEFT JOIN item_mst im_act ON im_act.item_id = jgli.actual_item_id
        LEFT JOIN jute_quality_mst jqm_act ON jqm_act.jute_qlty_id = jgli.actual_jute_quality_id
        WHERE jgli.jute_gate_entry_id = :jute_gate_entry_id
        AND (jgli.active = 1 OR jgli.active IS NULL)
        ORDER BY jgli.jute_gate_entry_li_id
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
            jp.jute_mukam_id AS mukam_id,
            jmm.mukam_name,
            jp.jute_uom,
            jp.branch_id
        FROM jute_po jp
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jp.supplier_id
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
# MATERIAL INSPECTION QUERIES
# =============================================================================

def get_material_inspection_table_query(co_id: int, search: str = None):
    """
    Query to get jute gate entries pending QC check (qc_check = 'N').
    Returns entries that need material inspection.
    Updated: entry_branch_seq renamed to branch_gate_entry_no, mukam renamed to mukam_id.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jge.jute_gate_entry_id AS CHAR) LIKE :search
                OR jmm.mukam_name LIKE :search
                OR jge.unit_conversion LIKE :search
                OR jge.vehicle_no LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jge.jute_gate_entry_id,
            jge.branch_gate_entry_no,
            jge.branch_id,
            bm.branch_name,
            jge.jute_gate_entry_date,
            jge.unit_conversion,
            jge.mukam_id,
            jmm.mukam_name AS mukam,
            jge.vehicle_no,
            jge.challan_no,
            jge.gross_weight,
            jge.tare_weight,
            jge.net_weight,
            jge.variable_shortage,
            jge.qc_check,
            jge.status_id,
            COALESCE(sm.status_name, 'Pending') AS status,
            jge.updated_date_time
        FROM jute_gate_entry jge
        INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jge.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jge.status_id
        WHERE bm.co_id = :co_id
        AND jge.qc_check = 'N'
        {search_clause}
        ORDER BY jge.jute_gate_entry_date DESC, jge.jute_gate_entry_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_material_inspection_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of gate entries pending QC check.
    Updated: mukam renamed to mukam_id.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                CAST(jge.jute_gate_entry_id AS CHAR) LIKE :search
                OR jmm.mukam_name LIKE :search
                OR jge.unit_conversion LIKE :search
                OR jge.vehicle_no LIKE :search
            )
        """

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_gate_entry jge
        INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jge.mukam_id
        WHERE bm.co_id = :co_id
        AND jge.qc_check = 'N'
        {search_clause}
    """
    return text(sql)


def get_material_inspection_by_id_query():
    """
    Query to get a single gate entry for material inspection.
    Updated: entry_branch_seq renamed to branch_gate_entry_no, mukam renamed to mukam_id.
    """
    sql = """
        SELECT 
            jge.jute_gate_entry_id,
            jge.branch_gate_entry_no,
            jge.branch_id,
            bm.branch_name,
            jge.jute_gate_entry_date,
            jge.unit_conversion,
            jge.mukam_id,
            jmm.mukam_name AS mukam,
            jge.vehicle_no,
            jge.challan_no,
            jge.challan_date,
            jge.challan_weight,
            jge.gross_weight,
            jge.tare_weight,
            jge.net_weight,
            jge.variable_shortage,
            jge.jute_supplier_id,
            jsm.supplier_name,
            jge.party_id,
            jge.po_id,
            jge.qc_check,
            jge.status_id,
            COALESCE(sm.status_name, 'Pending') AS status,
            jge.remarks,
            jge.updated_by,
            jge.updated_date_time
        FROM jute_gate_entry jge
        INNER JOIN branch_mst bm ON bm.branch_id = jge.branch_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jge.mukam_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jge.jute_supplier_id
        LEFT JOIN status_mst sm ON sm.status_id = jge.status_id
        WHERE jge.jute_gate_entry_id = :gate_entry_id
    """
    return text(sql)


def get_material_inspection_line_items_query():
    """
    Query to get line items for material inspection.
    Includes challan and actual fields only - QC fields are now in jute_mr_li.
    Updated: challan_item_name_id renamed to challan_item_id.
    """
    sql = """
        SELECT 
            jgli.jute_gate_entry_li_id,
            jgli.jute_gate_entry_id,
            jgli.po_line_item_num,
            
            -- Challan details
            jgli.challan_item_id,
            im_ch.item_name AS challan_item_name,
            jgli.challan_jute_quality_id,
            jqm_ch.jute_quality AS challan_quality_name,
            jgli.challan_quantity,
            jgli.challan_weight,
            
            -- Actual (received) details
            jgli.actual_item_id,
            im_act.item_name AS actual_item_name,
            jgli.actual_jute_quality_id,
            jqm_act.jute_quality AS actual_quality_name,
            jgli.actual_quantity,
            jgli.actual_weight,
            
            jgli.allowable_moisture,
            jgli.jute_uom,
            jgli.remarks,
            jgli.active
        FROM jute_gate_entry_li jgli
        LEFT JOIN item_mst im_ch ON im_ch.item_id = jgli.challan_item_id
        LEFT JOIN jute_quality_mst jqm_ch ON jqm_ch.jute_qlty_id = jgli.challan_jute_quality_id
        LEFT JOIN item_mst im_act ON im_act.item_id = jgli.actual_item_id
        LEFT JOIN jute_quality_mst jqm_act ON jqm_act.jute_qlty_id = jgli.actual_jute_quality_id
        WHERE jgli.jute_gate_entry_id = :gate_entry_id
        AND (jgli.active = 1 OR jgli.active IS NULL)
        ORDER BY jgli.jute_gate_entry_li_id
    """
    return text(sql)


def update_material_inspection_qc_complete():
    """
    Query to mark a gate entry as QC complete (qc_check = 'Y').
    """
    sql = """
        UPDATE jute_gate_entry
        SET qc_check = 'Y',
            updated_by = :updated_by,
            updated_date_time = :updated_date_time
        WHERE jute_gate_entry_id = :gate_entry_id
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
            jute_gate_entry_id, jute_gate_entry_date, 
            challan_no, challan_date,
            jute_supplier_id, party_id, mukam_id, unit_conversion,
            po_id, mr_weight, vehicle_no, status_id, remarks,
            updated_by, updated_date_time
        ) VALUES (
            :branch_id, :branch_mr_no, :jute_mr_date,
            :jute_gate_entry_id, :jute_gate_entry_date,
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
            jute_mr_id, jute_gate_entry_lineitem_id,
            challan_item_id, challan_quality_id, challan_quantity, challan_weight,
            actual_item_id, actual_quality, actual_qty, actual_weight,
            allowable_moisture, actual_moisture, accepted_weight,
            rate, warehouse_id, marka, crop_year,
            remarks, status, active, updated_date_time
        ) VALUES (
            :jute_mr_id, :jute_gate_entry_lineitem_id,
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
            jm.updated_date_time
        FROM jute_mr jm
        INNER JOIN branch_mst bm ON bm.branch_id = jm.branch_id
        LEFT JOIN jute_supplier_mst jsm ON jsm.supplier_id = jm.jute_supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = CAST(jm.party_id AS UNSIGNED)
        LEFT JOIN branch_mst pb ON pb.branch_id = jm.party_branch_id
        LEFT JOIN jute_po jp ON jp.jute_po_id = jm.po_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jm.mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jm.status_id
        WHERE bm.co_id = :co_id
        {search_clause}
        ORDER BY jm.jute_mr_date DESC, jm.jute_mr_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_mr_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of jute MRs for pagination.
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
    """
    sql = """
        SELECT 
            jmli.jute_mr_li_id,
            jmli.jute_mr_id,
            jmli.jute_gate_entry_lineitem_id,
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
            jmli.rate,
            jmli.claim_rate,
            jmli.claim_quality,
            jmli.water_damage_amount,
            jmli.premium_amount,
            jmli.remarks,
            jmli.status,
            jmli.active
        FROM jute_mr_li jmli
        LEFT JOIN item_mst im ON im.item_id = jmli.actual_item_id
        LEFT JOIN jute_quality_mst jqm ON jqm.jute_qlty_id = jmli.actual_quality
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

