from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

Base = declarative_base()

class ConMenuMaster(Base):
    __tablename__ = 'con_menu_master'

    con_menu_id = Column(Integer, primary_key=True, autoincrement=True)
    con_menu_name = Column(String(25), nullable=False)
    con_menu_parent_id = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    con_menu_path = Column(String(255), nullable=True)
    con_menu_icon = Column(String(255), nullable=True)
    order_by = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<ConMenuMaster(id={self.con_menu_id}, name='{self.con_menu_name}')>"

class ConRoleMenuMap(Base):
    __tablename__ = 'con_role_menu_map'

    con_role_menu_mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    con_role_id = Column(Integer, ForeignKey('con_role_master.con_role_id'), nullable=False)
    con_menu_id = Column(Integer, ForeignKey('con_menu_master.con_menu_id'), nullable=False)

    menu = relationship('ConMenuMaster', backref='role_mappings')
    role = relationship('conRoleMaster', backref='menu_mappings')

    def __repr__(self):
        return (f"<ConRoleMenuMap(id={self.con_role_menu_mapping_id}, "
                f"role_id={self.con_role_id}, menu_id={self.con_menu_id})>")

class ConUser(Base):
    __tablename__ = "con_user_master"

    con_user_id = Column(Integer, primary_key=True, autoincrement=True)
    con_org_id = Column(Integer, ForeignKey('con_org_master.con_org_id'), nullable=True, index=True)
    con_user_login_email_id = Column(String(50), nullable=False)
    con_user_login_password = Column(String(500), nullable=False)
    con_user_name = Column(String(30), nullable=False)
    con_user_type = Column(Integer, nullable=False)
    created_by = Column(Integer, nullable=True)
    created_date_time = Column(DateTime, nullable=True, server_default=func.current_timestamp())
    active = Column(Integer, nullable=False, default=1)
    refresh_token = Column(String(255), nullable=True)

class ConOrgMaster(Base):
    __tablename__ = "con_org_master"

    con_org_id = Column(Integer, primary_key=True, autoincrement=True)
    con_org_name = Column(String(50), nullable=True)
    con_org_shortname = Column(String(10), nullable=True)
    con_org_email_id = Column(String(100), nullable=True)
    con_org_mobile = Column(String(20), nullable=True)
    con_org_contact_person = Column(String(30), nullable=True)
    con_org_address = Column(String(250), nullable=True)
    con_org_pincode = Column(Integer, nullable=True)
    con_org_main_url = Column(String(100), nullable=True)
    con_org_state_id = Column(Integer, nullable=True)
    con_org_master_status = Column(Integer, nullable=True)
    con_org_remarks = Column(String(250), nullable=True)
    con_modules_selected = Column(JSON, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_date_time = Column(DateTime, nullable=True, server_default=func.current_timestamp())
    active = Column(Integer, nullable=True, default=1)

class conRoleMaster(Base):
    __tablename__ = "con_role_master"

    con_role_id = Column(Integer, primary_key=True, autoincrement=True)
    con_role_name = Column(String(50), nullable=False)
    con_org_id = Column(Integer, ForeignKey('con_org_master.con_org_id'), nullable=False)
    status = Column(Integer, nullable=False)
    created_by = Column(Integer, nullable=True)
    created_date_time = Column(DateTime, nullable=True, server_default=func.current_timestamp())
    con_company_id = Column(Integer, nullable=True)
    is_enable = Column(Integer, nullable=False, default=1)

class ConUserRoleMapping(Base):
    __tablename__ = "con_user_role_mapping"

    con_user_role_mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    con_role_id = Column(Integer, ForeignKey('con_role_master.con_role_id'), nullable=False, index=True)
    con_user_id = Column(Integer, ForeignKey('con_user_master.con_user_id'), nullable=False, index=True)
    created_by = Column(Integer, nullable=False, index=True)
    created_date_time = Column(DateTime, nullable=True, server_default=func.now())

