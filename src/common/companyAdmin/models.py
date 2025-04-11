from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func

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


class RolesMst(Base):
    __tablename__ = 'roles_mst'

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(255), nullable=False, unique=True)
    active = Column(Boolean, default=True)
    created_by_con_user = Column(Integer, nullable=True)
    created_date_time = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<RolesMst(id={self.role_id}, name='{self.role_name}')>"
    
class CountryMst(Base):
    __tablename__ = 'country_mst'

    country_id = Column(Integer, primary_key=True, autoincrement=True)
    country = Column(String(255), nullable=False, unique=True)

    def __repr__(self):
        return f"<CountryMst(id={self.country_id}, country='{self.country}')>"


class StateMst(Base):
    __tablename__ = 'state_mst'

    state_id = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(String(255), nullable=False, unique=True)
    country_id = Column(Integer, ForeignKey('country_mst.country_id'), nullable=False)

    def __repr__(self):
        return f"<StateMst(id={self.state_id}, state='{self.state}', country_id={self.country_id})>"


class CityMst(Base):
    __tablename__ = 'city_mst'

    city_id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String(255), nullable=True)
    state_id = Column(Integer, ForeignKey('state_mst.state_id'), nullable=True)

    def __repr__(self):
        return f"<CityMst(id={self.city_id}, city_name='{self.city_name}', state_id={self.state_id})>"
