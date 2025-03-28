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
