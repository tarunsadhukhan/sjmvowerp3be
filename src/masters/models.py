
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Float
from sqlmodel import Date
from src.common.companyAdmin.models import CoMst

Base = declarative_base()

class ItemGrpMst(Base):
    __tablename__ = "item_grp_mst"

    item_grp_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_grp_id = Column(Integer)
    active = Column(String(255))
    co_id = Column(Integer)
    # co_id = Column(Integer, ForeignKey("co_mst.co_id"))
    updated_by = Column(String(255))
    updated_date_time = Column(DateTime, default=func.now())
    item_grp_name = Column(String(255))
    item_grp_code = Column(String(255))
    purchase_code = Column(Integer)
    item_type_id = Column(Integer)
    # item_type_id = Column(Integer, ForeignKey("item_type_master.item_type_id"))

    # co = relationship("CoMst", foreign_keys=[co_id])
    # item_type = relationship("ItemTypeMaster", foreign_keys=[item_type_id])

class ItemMake(Base):
    __tablename__ = "item_make"

    item_make_id = Column(Integer, primary_key=True, autoincrement=True)
    item_grp_id = Column(Integer, ForeignKey("item_grp_mst.item_grp_id"))
    item_make_name = Column(String(255))
    updated_by = Column(Integer)
    updated_date_time = Column(DateTime, default=func.now())

    # item_group = relationship("ItemGrpMst", foreign_keys=[item_grp_id])

class ItemMst(Base):
    __tablename__ = "item_mst"
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Integer)
    updated_date_time = Column(DateTime, default=func.now())
    updated_by = Column(Integer)
    item_grp_id = Column(Integer, ForeignKey("item_grp_mst.item_grp_id"))
    item_code = Column(String(255))
    tangible = Column(Boolean)
    item_name = Column(String(255))
    item_photo = Column(String(16777215))  # MEDIUMTEXT equivalent
    legacy_item_code = Column(String(255))
    hsn_code = Column(String(255))
    uom_id = Column(Integer, ForeignKey("uom_mst.uom_id"))
    tax_percentage = Column(Float)
    saleable = Column(Boolean)
    consumable = Column(Boolean)
    purchaseable = Column(Boolean)
    manufacturable = Column(Boolean)
    assembly = Column(Boolean)
    uom_rounding = Column(Integer)
    rate_rounding = Column(Integer)
    # item_group = relationship("ItemGrpMst", foreign_keys=[item_grp_id])
    # uom = relationship("UomMst", foreign_keys=[uom_id])

class ItemTypeMaster(Base):
    __tablename__ = "item_type_master"
    item_type_id = Column(Integer, primary_key=True, autoincrement=True)
    item_type_name = Column(String(25), unique=True)
            # optional reverse relation
    # item_groups = relationship("ItemGrpMst", back_populates="item_type")

    class UomMst(Base):
        __tablename__ = "uom_mst"

        uom_id = Column(Integer, primary_key=True, autoincrement=True)
        active = Column(Boolean)
        uom_name = Column(String(255))
        class ItemMinmaxMst(Base):
            __tablename__ = "item_minmax_mst"

            item_minmax_id = Column(Integer, primary_key=True, autoincrement=True)
            branch_id = Column(Integer, ForeignKey("branch_mst.branch_id"))
            item_id = Column(Integer, ForeignKey("item_mst.item_id"))
            minqty = Column(Float)
            maxqty = Column(Float)
            min_order_qty = Column(Float)
            lead_time = Column(Integer)
            updated_by = Column(Integer)
            updated_date_tiime = Column(DateTime)
            active = Column(Integer)

            # branch = relationship("BranchMst", foreign_keys=[branch_id])
            # item = relationship("ItemMst", foreign_keys=[item_id])
            class UomItemMapMst(Base):
                __tablename__ = "uom_item_map_mst"

                uom_item_map_id = Column(Integer, primary_key=True, autoincrement=True)
                item_id = Column(Integer, ForeignKey("item_mst.item_id"))
                map_from_id = Column(Integer, ForeignKey("uom_mst.uom_id"))
                map_to_id = Column(Integer, ForeignKey("uom_mst.uom_id"))
                is_fixed = Column(Integer)          # 1 = fixed, 0 = variable
                relation_value = Column(Float)
                rounding = Column(Integer)
                updated_by = Column(Integer)
                updated_date_time = Column(DateTime)

                # item = relationship("ItemMst", foreign_keys=[item_id])
                # map_from = relationship("UomMst", foreign_keys=[map_from_id])
                # map_to = relationship("UomMst", foreign_keys=[map_to_id])
                
                
class DeptMst(Base):
    __tablename__ = 'dept_mst'

    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(Integer, nullable=True)
    created_by = Column(Integer, nullable=True)
    dept_desc = Column(String(30), nullable=True)
    dept_code = Column(String(30), nullable=True)
    order_id = Column(Integer, nullable=True)
    created_date = Column(DateTime, nullable=False, default=func.now())

 #   def __repr__(self):
        # include branch_id and dept_code for easier debugging
 #       return (f"<DeptMst(dept_id={self.dept_id}, branch_id={self.branch_id}, "
 #               f"dept_code={self.dept_code!r}, dept_desc={self.dept_desc!r})>")

# ...existing code...


# ...existing code...
class SubDeptMst(Base):
    __tablename__ = "sub_dept_mst"

    sub_dept_id = Column(Integer, primary_key=True, autoincrement=True)
    updated_by = Column(Integer, nullable=False)
    sub_dept_code = Column(String(25), nullable=True)
    sub_dept_desc = Column(String(30), nullable=True)
    dept_id = Column(Integer, nullable=True)
    updated_date_time = Column(DateTime, nullable=False, default=func.now())
    order_no = Column(Integer, nullable=True)

    # optional relationship to DeptMst
#    dept = relationship("DeptMst", foreign_keys=[dept_id])

#    def __repr__(self):
#        return f"<SubDeptMst(sub_dept_id={self.sub_dept_id}, dept_id={self.dept_id}, code={self.sub_dept_code!r})>"

class MachineTypeMst(Base):
    __tablename__ = "machine_type_mst"

    machine_type_id = Column(Integer, primary_key=True, autoincrement=True)
    machine_type_name = Column(String(255), nullable=True)
    updated_by = Column(Integer, nullable=False)
    updated_date_time = Column(DateTime, nullable=False, default=func.now())
    active = Column(Integer, nullable=True)
 
    # relationship to DeptMst (optional, convenient for joins)
    #dept = relationship("DeptMst", foreign_keys=[dept_id])


class MachineMst(Base):
    __tablename__ = "machine_mst"

    machine_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(Integer, ForeignKey("dept_mst.dept_id"), nullable=False)
    machine_name = Column(String(255), nullable=False)
    machine_type_id = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    remarks = Column(String(255), nullable=True)
    updated_date_time = Column(DateTime, nullable=False, default=func.now())
    active = Column(Integer, nullable=False, default=1)
    mech_posting_code = Column(Integer, nullable=True)
    mech_code = Column(String(100), nullable=False)

    # relationships
  #  dept = relationship("DeptMst", foreign_keys=[dept_id])
  #  machine_type = relationship("MachineTypeMst", foreign_keys=[machine_type_id])

class ProjectMst(Base):
    __tablename__ = "project_mst"

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    prj_desc = Column(String(255), nullable=True)
    prj_end_dt = Column(Date, nullable=True)
    prj_name = Column(String(255), nullable=True)
    prj_start_dt = Column(Date, nullable=True)
    status_id = Column(Integer, nullable=True)
    active = Column(Integer, nullable=False, default=1)
    branch_id = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    updated_date_time = Column(DateTime, nullable=True)
    party_id = Column(Integer, nullable=True)
    dept_id = Column(Integer, nullable=True)

    # optional relationships for convenience
 #   status = relationship("StatusMst", foreign_keys=[status_id], lazy="joined")
 #   branch = relationship("BranchMst", foreign_keys=[branch_id], lazy="joined")
 #   party = relationship("PartyMst", foreign_keys=[party_id], lazy="joined")
 #   dept = relationship("DeptMst", foreign_keys=[dept_id], lazy="joined")

 #   def __repr__(self):
 #       return f"<ProjectMst(project_id={self.project_id}, prj_name={self.prj_name!r})>"
# ...existing code...