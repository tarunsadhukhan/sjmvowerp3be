from sqlalchemy.sql import text
from sqlalchemy.sql import bindparam
from sqlalchemy.sql.elements import TextClause


def get_item_group(co_id: int = None):
    sql = f"""WITH RECURSIVE item_hierarchy AS (-- Anchor member: level 1
  SELECT 
    igm.item_grp_id,
    igm.item_grp_code,
    igm.item_grp_name,
    igm.parent_grp_id,
    igm.active, 
    igm.item_type_id,
    CAST(igm.item_grp_code AS CHAR) AS item_grp_code_display,
    CAST(igm.item_grp_name AS CHAR) AS item_grp_name_display,
    1 AS level
  FROM item_grp_mst igm
  WHERE igm.parent_grp_id IS NULL AND co_id = 1
UNION ALL -- Recursive member
SELECT 
    child.item_grp_id,
    child.item_grp_code,
    child.item_grp_name,
    child.parent_grp_id,
    child.active,
    child.item_type_id,
    CONCAT(parent.item_grp_code_display, '-', child.item_grp_code),
    CONCAT(parent.item_grp_name_display, '-', child.item_grp_name),
    parent.level + 1
  FROM item_grp_mst child
  JOIN item_hierarchy parent ON child.parent_grp_id = parent.item_grp_id
)
SELECT 
  item_grp_id, 
  item_grp_code_display,-- item_grp_name_display based on level
  CASE 
    WHEN level = 1 THEN item_grp_name_display
    WHEN level = 2 THEN SUBSTRING_INDEX(item_grp_name_display, '-', 1)
    ELSE SUBSTRING_INDEX(item_grp_name_display, '-', level - 1)
  END AS item_grp_name_parent,
  -- item_grp_name based on level
  CASE 
    WHEN level = 1 THEN NULL
    ELSE SUBSTRING_INDEX(item_grp_name_display, '-', -1)
  END AS item_sub_grp_name,
  active,
  item_type_id
FROM item_hierarchy where (:search IS NULL OR 
                    item_grp_code_display LIKE :search OR 
                    item_grp_name_display LIKE :search) ;"""
    query = text(sql)
    return query
