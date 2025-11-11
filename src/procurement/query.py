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


def get_indent_by_id_query():
    sql = """SELECT
        pi.indent_id,
        pi.indent_no,
        pi.indent_date,
        pi.branch_id,
        bm.branch_name,
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
        pi.updated_date_time
    FROM proc_indent AS pi
    LEFT JOIN branch_mst AS bm ON bm.branch_id = pi.branch_id
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