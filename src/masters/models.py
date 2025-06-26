
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Float

Base = declarative_base()

class ItemGrpMst(Base):
    __tablename__ = "item_grp_mst"

    item_grp_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_grp_id = Column(Integer)
    active = Column(String(255))
    co_id = Column(Integer, ForeignKey("co_mst.co_id"))
    created_by = Column(String(255))
    created_date = Column(DateTime, default=func.now())
    item_grp_name = Column(String(255))
    item_grp_code = Column(String(255))
    purchase_code = Column(Integer)
    item_type_id = Column(Integer, ForeignKey("item_type_master.item_type_id"))

    co = relationship("CoMst", foreign_keys=[co_id])
    item_type = relationship("ItemTypeMaster", foreign_keys=[item_type_id])