from sqlalchemy.sql import text
from sqlalchemy.sql import bindparam
from sqlalchemy.sql.elements import TextClause


def get_item_group(co_id: int = None):
    sql = f"""WITH RECURSIVE item_hierarchy AS (-- Anchor member: start with top-level nodes (no parent)
  SELECT 
    igm.item_grp_id,
    igm.item_grp_code,
    igm.item_grp_name,
    igm.parent_grp_id,
    igm.active, 
    igm.item_type_id,
    CAST(igm.item_grp_code AS CHAR) AS item_grp_code_display,
    CAST(igm.item_grp_name AS CHAR) AS item_grp_name_display
  FROM item_grp_mst igm
  WHERE igm.parent_grp_id IS NULL and igm.co_id = :co_id
  UNION ALL-- Recursive member: join with children
  SELECT 
    child.item_grp_id,
    child.item_grp_code,
    child.item_grp_name,
    child.parent_grp_id,
    child.active,
    child.item_type_id,
    CONCAT(parent.item_grp_code_display, '-', child.item_grp_code),
    CONCAT(parent.item_grp_name_display, '-', child.item_grp_name)
  FROM item_grp_mst child
  JOIN item_hierarchy parent ON child.parent_grp_id = parent.item_grp_id
)
SELECT 
  item_grp_id,
  item_grp_code,
  item_grp_name,
  parent_grp_id,
  active,
  item_type_id,
  item_grp_code_display,
  item_grp_name_display
FROM item_hierarchy where (:search IS NULL OR 
                    item_grp_code_display LIKE :search OR 
                    item_grp_name_display LIKE :search) ;"""
    query = text(sql)
    return query
