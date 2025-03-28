from sqlalchemy.sql import text


def get_admin_login_query():
    return text("""
        SELECT * FROM vowconsole3.con_user_master cum
        WHERE con_user_login_email_id = :username 
          AND cum.con_user_type = 0
    """)