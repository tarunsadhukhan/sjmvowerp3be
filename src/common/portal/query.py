from sqlalchemy.sql import text
from sqlalchemy.sql import bindparam
from sqlalchemy.sql.elements import TextClause


def get_roles_tenant(search: str = None):
    sql = f"SELECT role_id, role_name FROM roles_mst where active = 1 "
    query = text(sql)
    return query

def get_co_tenant(search: str = None):
    sql = f"SELECT co_id, co_name FROM co_mst "
    query = text(sql)
    return query

def get_branch_tenant(search: str = None):
    sql = f"SELECT co_id, branch_id, branch_name FROM branch_mst where active = 1 "
    query = text(sql)
    return query

def get_user_role_map_tenant(user_id: int = None):
    """
    Get user role mappings for a specific user.
    The user_id parameter is expected to be provided when executing the query, not when defining it.
    """
    sql = "SELECT user_role_map_id, user_id, role_id, co_id, branch_id FROM user_role_map WHERE user_id = :user_id"
    query = text(sql)
    return query


# {
#     "detail": "Error fetching user edit setup data: (sqlalchemy.exc.InvalidRequestError) "
#     "A value is required for bind parameter 'user_id'\n[SQL: SELECT user_role_map_id, user_id, "
#     "role_id, co_id, branch_id FROM user_role_map WHERE user_id = %(user_id)s]\n[parameters: "
#     "[{}]]\n(Background on this error at: https://sqlalche.me/e/20/cd3x)"
# }