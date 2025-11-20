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
        pi.updated_date_time,
        CASE 
            WHEN pi.status_id = 20 THEN pi.approval_level 
            ELSE NULL 
        END AS approval_level
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