from sqlalchemy.sql import text


def get_jute_po_table_query(co_id: int, search: str = None):
    """
    Query to get jute PO list with pagination support.
    Joins with party_mst for supplier name, jute_broker_master for broker name,
    jute_mukam_mst for mukam name, and status_mst for status name.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                jp.po_num LIKE :search
                OR pm.supp_name LIKE :search
                OR jbm.broker_name LIKE :search
                OR jmm.mukam_name LIKE :search
            )
        """

    sql = f"""
        SELECT 
            jp.jute_po_id,
            jp.po_num,
            jp.po_date,
            jp.supp_code,
            pm.supp_name AS supplier_name,
            jp.broker_id,
            COALESCE(jbm.broker_name, jp.broker_name) AS broker_name,
            jp.mukam AS mukam_id,
            jmm.mukam_name AS mukam,
            jp.vehicle_type_id,
            jp.vehicle_quantity AS vehicle_qty,
            jp.po_status AS status_id,
            COALESCE(sm.status_name, jp.po_status) AS status,
            jp.po_val_wt_tax,
            jp.po_val_wo_tax,
            jp.weight,
            jp.jute_unit,
            jp.branch_id,
            jp.updated_date_time,
            jp.created_by
        FROM jute_po jp
        LEFT JOIN party_mst pm ON pm.supp_code = jp.supp_code AND pm.co_id = jp.co_id
        LEFT JOIN jute_broker_master jbm ON jbm.broker_id = jp.broker_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.mukam
        LEFT JOIN status_mst sm ON sm.status_id = jp.po_status
        WHERE jp.co_id = :co_id
        {search_clause}
        ORDER BY jp.po_date DESC, jp.jute_po_id DESC
        LIMIT :limit OFFSET :offset
    """
    return text(sql)


def get_jute_po_table_count_query(co_id: int, search: str = None):
    """
    Query to get total count of jute POs for pagination.
    """
    search_clause = ""
    if search:
        search_clause = """
            AND (
                jp.po_num LIKE :search
                OR pm.supp_name LIKE :search
                OR jbm.broker_name LIKE :search
                OR jmm.mukam_name LIKE :search
            )
        """

    sql = f"""
        SELECT COUNT(*) AS total
        FROM jute_po jp
        LEFT JOIN party_mst pm ON pm.supp_code = jp.supp_code AND pm.co_id = jp.co_id
        LEFT JOIN jute_broker_master jbm ON jbm.broker_id = jp.broker_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.mukam
        WHERE jp.co_id = :co_id
        {search_clause}
    """
    return text(sql)


def get_jute_po_by_id_query():
    """
    Query to get a single jute PO by ID.
    """
    sql = """
        SELECT 
            jp.jute_po_id,
            jp.po_num,
            jp.po_date,
            jp.supp_code,
            pm.supp_name AS supplier_name,
            jp.broker_id,
            COALESCE(jbm.broker_name, jp.broker_name) AS broker_name,
            jp.mukam AS mukam_id,
            jmm.mukam_name AS mukam,
            jp.vehicle_type_id,
            jp.vehicle_quantity AS vehicle_qty,
            jp.po_status AS status_id,
            COALESCE(sm.status_name, jp.po_status) AS status,
            jp.po_val_wt_tax,
            jp.po_val_wo_tax,
            jp.weight,
            jp.jute_unit,
            jp.branch_id,
            jp.credit_term,
            jp.delivery_timeline,
            jp.footer_note,
            jp.frieght_charge,
            jp.indent_no,
            jp.indent_type_id,
            jp.remarks,
            jp.tax,
            jp.tax_type,
            jp.po_type,
            jp.with_or_without,
            jp.channel_code,
            jp.contract_no,
            jp.contract_date,
            jp.currency_code,
            jp.conversation_rate,
            jp.brokrage_rate,
            jp.brokrage_percentage,
            jp.penalty,
            jp.internal_note,
            jp.updated_date_time,
            jp.created_by,
            jp.mod_on,
            jp.mod_by
        FROM jute_po jp
        LEFT JOIN party_mst pm ON pm.supp_code = jp.supp_code AND pm.co_id = jp.co_id
        LEFT JOIN jute_broker_master jbm ON jbm.broker_id = jp.broker_id
        LEFT JOIN jute_mukam_mst jmm ON jmm.mukam_id = jp.mukam
        LEFT JOIN status_mst sm ON sm.status_id = jp.po_status
        WHERE jp.jute_po_id = :jute_po_id AND jp.co_id = :co_id
    """
    return text(sql)
