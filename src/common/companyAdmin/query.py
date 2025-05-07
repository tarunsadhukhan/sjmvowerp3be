from sqlalchemy.sql import text
from sqlalchemy.sql import bindparam
from sqlalchemy.sql.elements import TextClause

def get_co_all_query(search: str = None, limit: int = None, offset: int = None):
    sql = f"""select cm.co_id, cm.co_name, cm.co_prefix,  cm.co_email_id 
from co_mst cm
    WHERE (:search IS NULL OR 
             cm.co_name LIKE :search OR
             cm.co_prefix LIKE :search OR
             cm.co_email_id LIKE :search) 
        ORDER BY cm.co_id
        LIMIT :limit OFFSET :offset;"""
    query = text(sql)
    return query

def get_co_all_count_query(search: str = None):
    sql = f"""select count(*) as total from co_mst cm 
    where 
    (:search IS NULL OR 
                    cm.co_name LIKE :search OR 
                    cm.co_prefix LIKE :search OR 
                    cm.co_email_id LIKE :search
                      ) 
                      ;"""
    query = text(sql)
    return query

def get_co_by_id_query(co_id: int):
    sql = f"""select cm.co_id, cm.co_name, cm.co_prefix, cm.co_address1 , cm.co_address2, cm.co_zipcode , 
cm.country_id, cm.state_id, cm.city_id, cm.co_cin_no, cm.co_email_id , cm.co_pan_no , cm.alert_email_id
from co_mst cm
    WHERE cm.co_id = :co_id;"""
    query = text(sql)
    return query

def get_country_query():
    sql = f"""select cm.country_id, cm.country from country_mst cm;"""
    query = text(sql)
    return query

def get_state_query():
    sql = f"""select sm.state_id, sm.state, sm.country_id from state_mst sm;"""
    query = text(sql)
    return query

def get_city_query():
    sql = f"""select cm.city_id, cm.city_name, cm.state_id from city_mst cm;"""
    query = text(sql)
    return query

