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
  WHERE igm.parent_grp_id IS NULL AND co_id = :co_id 
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


def get_item_group_drodown(co_id: int = None):
    sql = f"""WITH RECURSIVE item_hierarchy AS (-- Anchor member: start with top-level nodes (no parent)
  SELECT 
    igm.item_grp_id,
    igm.item_grp_code,
    igm.item_grp_name,
    igm.parent_grp_id ,
    CAST(igm.item_grp_code AS CHAR) AS item_grp_code_display,
    CAST(igm.item_grp_name AS CHAR) AS item_grp_name_display
  FROM item_grp_mst igm
  WHERE igm.parent_grp_id IS NULL and igm.co_id =:co_id and igm.active = 1
  UNION ALL-- Recursive member: join with children
  SELECT 
    child.item_grp_id,
    child.item_grp_code,
    child.item_grp_name,
    child.parent_grp_id,
    CONCAT(parent.item_grp_code_display, '-', child.item_grp_code),
    CONCAT(parent.item_grp_name_display, '-', child.item_grp_name)
  FROM item_grp_mst child
  JOIN item_hierarchy parent ON child.parent_grp_id = parent.item_grp_id
) 
SELECT 
  item_grp_id,
  item_grp_code_display,
  item_grp_name_display
FROM item_hierarchy
ORDER BY item_grp_code_display;"""
    query = text(sql)
    return query


def india_gst_applicable():
    sql = """
select cc.india_gst  from co_config cc where cc.co_id =:co_id;
"""
    query = text(sql)
    return query

def check_item_group_code_and_name(co_id: int, item_grp_code: str, item_grp_name: str):
    """
    Check if the item group code and name are valid for the given company.
    Returns a boolean indicating if the code and name are valid.
    """
    sql = """
WITH RECURSIVE all_descendants AS (
    -- Start from the parent where the new item would be added
    SELECT 
        item_grp_id,
        item_grp_code,
        item_grp_name,
        parent_grp_id,
        co_id
    FROM item_grp_mst
    WHERE item_grp_id = null AND co_id = :co_id
    UNION ALL
    -- Recursively get all children under that parent
    SELECT 
        child.item_grp_id,
        child.item_grp_code,
        child.item_grp_name,
        child.parent_grp_id,
        child.co_id
    FROM item_grp_mst child
    JOIN all_descendants parent ON child.parent_grp_id = parent.item_grp_id
    WHERE child.co_id = :co_id
)
-- Final check
SELECT
    NOT EXISTS (
        SELECT 1 FROM all_descendants 
        WHERE item_grp_code = :item_grp_code
    ) AS is_code_valid,
    NOT EXISTS (
        SELECT 1 FROM all_descendants 
        WHERE item_grp_name = :item_grp_name
    ) AS is_name_valid;
"""
    return text(sql)


def get_item_group_details_by_id():
    sql = """
        SELECT * FROM item_grp_mst WHERE item_grp_id = :item_grp_id
    """
    return text(sql)

def get_item(co_id: int = None):
    sql = f"""item_id, active, item_grp_id , item_code, tangible, item_name , item_photo , legacy_item_code , hsn_code , uom_id , tax_percentage , 
saleable , consumable , purchaseable , manufacturable , assembly , uom_rounding , rate_rounding 
from item_mst
  WHERE co_id = :co_id 
  AND (:search IS NULL OR 
                    item_grp_code_display LIKE :search OR 
                    item_grp_name_display LIKE :search) ;"""
    query = text(sql)
    return query

def get_item_table(co_id: int = None):
    sql = f"""  WITH RECURSIVE item_hierarchy AS (
  -- Anchor: top-level item groups for company 1
  SELECT 
    igm.item_grp_id,
    igm.item_grp_code,
    igm.item_grp_name,
    igm.parent_grp_id,
    igm.active,
    igm.item_type_id,
    igm.co_id,
    CAST(igm.item_grp_code AS CHAR) AS item_group_code_display,
    CAST(igm.item_grp_name AS CHAR) AS item_group_display,
    1 AS level
  FROM item_grp_mst igm
  WHERE igm.parent_grp_id IS NULL AND igm.co_id = :co_id
  UNION ALL
  -- Recursive part: build full paths for name and code
  SELECT 
    child.item_grp_id,
    child.item_grp_code,
    child.item_grp_name,
    child.parent_grp_id,
    child.active,
    child.item_type_id,
    child.co_id,
    CONCAT(parent.item_group_code_display, '-', child.item_grp_code),
    CONCAT(parent.item_group_display, '-', child.item_grp_name),
    parent.level + 1
  FROM item_grp_mst child 
  JOIN item_hierarchy parent 
    ON child.parent_grp_id = parent.item_grp_id
   AND child.co_id = parent.co_id
)
SELECT  
  im.item_id, 
  im.item_grp_id,
  ih.item_group_display,
  ih.item_group_code_display,
  im.item_code, 
  im.item_name, 
  im.active
FROM item_mst im 
INNER JOIN item_hierarchy ih 
  ON im.item_grp_id = ih.item_grp_id
  where (:search IS NULL OR
  ih.item_group_code_display LIKE :search OR
  ih.item_group_display LIKE :search
  OR im.item_code LIKE :search OR
  im.item_name LIKE :search);
"""
    query = text(sql)
    return query


def get_item_by_id(item_id: int):
    sql = """
  select 
  im.item_id,
  im.active, 
  im.item_grp_id,
  im.item_code, 
  im.item_name,
  im.tangible, 
  im.item_photo,
  im.legacy_item_code ,
  im.hsn_code, 
  im.uom_id,
  um.uom_name ,
  im.tax_percentage,
  im.saleable,
  im.consumable,
  im.purchaseable,
  im.manufacturable,
  im.assembly,
  im.uom_rounding ,
  im.rate_rounding 
  from item_mst im
  left join uom_mst um on um.uom_id = im.uom_id
  where im.item_id = :item_id
  ;"""
    query = text(sql)
    return query


def get_item_group_path(item_grp_id: int):
    sql = """
WITH RECURSIVE item_group_path AS (
  -- Anchor: start from given item group
  SELECT 
    igm.item_grp_id,
    igm.item_grp_code,
    igm.item_grp_name,
    igm.parent_grp_id,
    CAST(igm.item_grp_code AS CHAR) AS item_group_code_display,
    CAST(igm.item_grp_name AS CHAR) AS item_group_display
  FROM item_grp_mst igm
  WHERE igm.item_grp_id = :item_grp_id  -- Replace this with your desired item_grp_id
  UNION ALL
  -- Walk upward to parent, prepend name and code
  SELECT 
    parent.item_grp_id,
    parent.item_grp_code,
    parent.item_grp_name,
    parent.parent_grp_id,
    CONCAT(parent.item_grp_code, '-', child.item_group_code_display),
    CONCAT(parent.item_grp_name, '-', child.item_group_display)
  FROM item_grp_mst parent
  JOIN item_group_path child ON child.parent_grp_id = parent.item_grp_id
)
-- Return only the final merged result
SELECT 
  :item_grp_id as item_grp_id,
  item_group_code_display,
  item_group_display
FROM item_group_path
ORDER BY LENGTH(item_group_display) DESC
LIMIT 1;"""
    sql = sql.replace(":item_grp_id", str(item_grp_id))
    query = text(sql)
    return query



def get_item_uom_mapping(item_id: int):
    sql = """
SELECT 
  uimm.map_from_id, um.uom_name as map_from_name,
  uimm.map_to_id , um2.uom_name as map_to_name,
uimm.is_fixed, 
uimm.relation_value , 
uimm.rounding  
from uom_item_map_mst uimm 
left join uom_mst um  on um.uom_id = uimm.map_from_id
left join uom_mst um2 on um2.uom_id = uimm.map_to_id
where uimm.item_id = :item_id;"""
    query = text(sql)
    return query




def get_item_minmax_mapping(item_id: int, co_id: int):
    sql = """
SELECT 
  bm.branch_id ,
  bm.branch_name,
  imm.minqty, 
  imm.maxqty, 
  imm.min_order_qty, 
  imm.lead_time
FROM branch_mst bm
LEFT JOIN item_minmax_mst imm 
  ON bm.branch_id = imm.branch_id 
  AND imm.item_id = :item_id
  AND imm.active = 1
WHERE bm.co_id = :co_id;"""
    query = text(sql)
    return query


def get_uom_list():
    sql = """
SELECT um.uom_id, um.uom_name
FROM uom_mst um
WHERE um.active = 1;
"""
    query = text(sql)
    return query
