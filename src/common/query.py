from sqlalchemy.sql import text

def get_menu_for_user1_query():
    sql="""WITH RECURSIVE MenuHierarchy AS (
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id, mm.control_desk_menu_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        WHERE
          mm.parent_id = 0
        UNION ALL
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id,
          mm.parent_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        INNER JOIN
          MenuHierarchy mh ON mm.parent_id = mh.id
        )
        SELECT mh.id, title,
        CASE WHEN parent_id = 66 THEN concat('store/', path) ELSE path END path, icon, parent_id, mmenu_id,
        null company_id, :userid user_id FROM MenuHierarchy mh ORDER BY mmenu_id"""
    return text(sql)
    
    
def get_menu_for_othuser_query():
    return text("""select k.* from (
WITH RECURSIVE MenuHierarchy AS (
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id, mm.control_desk_menu_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        WHERE
          mm.parent_id = 0
        UNION ALL
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id,
          mm.parent_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        INNER JOIN
          MenuHierarchy mh ON mm.parent_id = mh.id
        )
        SELECT mh.id, title,
        CASE WHEN parent_id = 66 THEN concat('store/', path) ELSE path END path, icon, parent_id, mmenu_id,
        null company_id, :userid user_id FROM MenuHierarchy mh ORDER BY mmenu_id limit 3290 ) k
        join (
        select control_desk_menu_id from vowconsole3.con_user_role_mapping curm 
        left join vowconsole3.con_role_menu_mapping crmm on curm.con_role_id =crmm.con_role_id
        where curm.con_user_id =:userid
        ) g on  k.id=g.control_desk_menu_id """)


def get_attdata_othuser_query():
    return text("""select * from worker_masterk.* from (
WITH RECURSIVE MenuHierarchy AS (
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id, mm.control_desk_menu_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        WHERE
          mm.parent_id = 0
        UNION ALL
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id,
          mm.parent_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        INNER JOIN
          MenuHierarchy mh ON mm.parent_id = mh.id
        )
        SELECT mh.id, title,
        CASE WHEN parent_id = 66 THEN concat('store/', path) ELSE path END path, icon, parent_id, mmenu_id,
        null company_id, :userid user_id FROM MenuHierarchy mh ORDER BY mmenu_id limit 3290 ) k
        join (
        select control_desk_menu_id from vowconsole3.con_user_role_mapping curm 
        left join vowconsole3.con_role_menu_mapping crmm on curm.con_role_id =crmm.con_role_id
        where curm.con_user_id =:userid
        ) g on  k.id=g.control_desk_menu_id """)



""" CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    has_hrms_access BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_type (type),
    INDEX idx_hrms_access (has_hrms_access)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
 """


def get_role_for_user111_query():
    return text("""
        SELECT r.* 
        FROM roles r 
        WHERE r.has_hrms_access = true 
        AND :userid = 1
        ORDER BY r.created_at DESC 
        LIMIT :limit OFFSET :offset
    """)

def get_role_for_user1_query(search: str = None):
    return text("""
        select eb_id id,concat(worker_name,eb_no) name,cata_desc type, false has_hrms_access, '2025-03-05' created_at,'2025-03-06' updated_at
        from vowsls.worker_master wm 
        left join vowsls.category_master cm on wm.cata_id =cm.cata_id
        where wm.company_id=2 and wm.active ='Y'
                AND (:search IS NULL OR (
            wm.worker_name LIKE CONCAT('%', :search, '%') OR 
            cata_desc LIKE CONCAT('%', :search, '%')
        ))
        ORDER BY wm.eb_id DESC 
        LIMIT :limit OFFSET :offset
    """)





def get_menu_for_othuser_query():
    return text("""
        SELECT r.* 
        FROM roles r 
        WHERE r.has_hrms_access = false 
        OR :userid != 1
        ORDER BY r.created_at DESC 
        LIMIT :limit OFFSET :offset
    """)

def get_total_count_query(user_id: int,search: str = None):
    if user_id == 1:
        return text("""
            SELECT COUNT(*) as total 
            FROM (select eb_id id,concat(worker_name,eb_no) name,cata_desc type, false has_hrms_access, '2025-03-05' created_at,'2025-03-06' updated_at
        from vowsls.worker_master wm 
        left join vowsls.category_master cm on wm.cata_id =cm.cata_id
        where wm.company_id=2 and wm.active ='Y'
                    AND (:search IS NULL OR (
            wm.worker_name LIKE CONCAT('%', :search, '%') OR 
            cata_desc LIKE CONCAT('%', :search, '%')
        ))
            )  r 
        """)
    else:
        return text("""
            SELECT COUNT(*) as total 
            FROM roles r 
            WHERE r.has_hrms_access = false 
            OR :userid != 1
        """)
