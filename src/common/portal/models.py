from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Create Base class for SQLAlchemy ORM
Base = declarative_base()

class ConUser(Base):
    __tablename__ = "user_mst"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String(255), nullable=False, unique=True)
    name = Column(String(255))
    password = Column(String(255))
    refresh_token = Column(String(255))
    active = Column(Boolean, nullable=False)
    created_by_con_user = Column(Integer)
    created_date_time = Column(DateTime, default=func.now())

class conRoleMaster(Base):
    __tablename__ = "roles_mst"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(255), nullable=False, unique=True)
    active = Column(Boolean)
    created_by_con_user = Column(Integer)
    created_date_time = Column(DateTime, default=func.now())

class ConRoleMenuMap(Base):
    __tablename__ = "role_menu_map"

    role_menu_mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey('roles_mst.role_id'), nullable=False)
    menu_id = Column(Integer, nullable=False)
    access_type_id = Column(Integer, nullable=False)

    role = relationship('conRoleMaster', backref='menu_mappings')