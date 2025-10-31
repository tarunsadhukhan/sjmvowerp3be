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
        etm.expense_type_name,
        sm.status_name
FROM proc_indent AS pi
LEFT JOIN branch_mst AS bm ON bm.branch_id = pi.branch_id
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