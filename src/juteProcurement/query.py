from sqlalchemy.sql import text


def get_jute_po_table_query(co_id: int, search: str = None):
    """
    Query to get jute PO list with pagination support.
    Joins with branch_mst for co_id filtering, jute_supplier_mst for supplier name,
    jute_supp_party_map + party_mst for party details, jute_mukam_mst for mukam name,
    and status_mst for status name.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                jp.po_num LIKE :search
                OR jsm.supplier_name LIKE :search
                OR pm.supp_name LIKE :search
                OR jmm.mukam_name LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jp.jute_po_id,
            jp.po_num,
            jp.po_date,
            jspm.supp_code,
            pm.supp_name AS party_name,
            jp.supplier_id,
            jsm.supplier_name,
            jp.jute_mukam_id AS mukam_id,
            jmm.mukam_name AS mukam,
            jp.vehicle_type_id,
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
                jp.po_num LIKE :search
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
    """
    sql = """
        SELECT 
            jp.jute_po_id,
            jp.po_num,
            jp.po_date,
            pm.supp_code,
            pm.supp_name AS supplier_name,
            jp.supplier_id,
            COALESCE(jbm.supplier_name, '') AS broker_name,
            jp.jute_mukam_id AS mukam_id,
            jmm.mukam_name AS mukam,
            jp.vehicle_type_id,
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
            jp.po_type,
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
        LEFT JOIN jute_supplier_mst jbm ON jbm.supplier_id = jp.supplier_id
        LEFT JOIN party_mst pm ON pm.party_id = jbm.party_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.jute_mukam_id
        LEFT JOIN status_mst sm ON sm.status_id = jp.status_id
        WHERE jp.jute_po_id = :jute_po_id AND bm.co_id = :co_id
    """
    return text(sql)


def get_jute_po_line_items_query():
    """
    Query to get line items for a jute PO.
    Note: jute_po_li.quality maps to jute_quality_mst.jute_qlty_id,
    and jute_quality_mst.item_id maps to item_mst.item_id.
    """
    sql = """
        SELECT 
            jpli.jute_po_li_id,
            jpli.jute_po_id,
            jqm.item_id AS item_id,
            im.item_name AS item_name,
            jpli.quality,
            jqm.jute_quality AS quality_name,
            jpli.crop_year,
            jpli.marka,
            jpli.quantity,
            jpli.uom,
            jpli.rate,
            jpli.allowable_moisture_percentage,
            jpli.actual_quantity AS weight,
            jpli.value_wo_tax AS amount,
            jpli.status
        FROM jute_po_li jpli
        LEFT JOIN jute_quality_mst jqm ON jqm.jute_qlty_id = jpli.quality
        LEFT JOIN item_mst im ON im.item_id = jqm.item_id
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
