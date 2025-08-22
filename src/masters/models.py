
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Float
try:
    from src.common.companyAdmin.models import CoMst
except Exception:
    # optional import: some test environments may not have src.common dependencies available
    CoMst = None

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
            updated_date_time = Column(DateTime)
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

class PartyMst(Base):
    __tablename__ = "party_mst"

    party_id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Integer)
    prefix = Column(String(25))
    updated_date_time = Column(DateTime, default=func.now())
    updated_by = Column(Integer)
    phone_no = Column(String(25))
    cin = Column(String(25))
    co_id = Column(Integer)
    supp_contact_person = Column(String(255))
    supp_contact_designation = Column(String(255))
    supp_email_id = Column(String(255))
    supp_code = Column(String(25))
    party_pan_no = Column(String(255))
    entity_type_id = Column(Integer)
    supp_name = Column(String(255))
    msme_certified = Column(Integer)  # 1 = certified, 0 = not certified
    country_id = Column(Integer)
    party_type_id = Column(String(255))

    # Relationships (optional, only if the related models exist)
    # company = relationship("CoMst", foreign_keys=[co_id])
    # entity_type = relationship("EntityTypeMst", foreign_keys=[entity_type_id])
    # country = relationship("CountryMst", foreign_keys=[country_id])
    branches = relationship(
    "PartyBranchMst",
    back_populates="party",
    cascade="all, delete-orphan",
    passive_deletes=True,
    )

class PartyBranchMst(Base):
    __tablename__ = "party_branch_mst"

    party_mst_branch_id = Column(Integer, primary_key=True, autoincrement=True)
    party_id = Column(Integer, ForeignKey("party_mst.party_id"))
    active = Column(Integer)
    updated_date_time = Column(DateTime, default=func.now())
    updated_by = Column(Integer)
    gst_no = Column(String(255))
    address = Column(String(255))
    address_additional = Column(String(255))
    zip_code = Column(Integer)
    city_id = Column(Integer)
    contact_no = Column(String(25))
    contact_person = Column(String(255))

    # party = relationship("PartyMst", back_populates="branches")
    party = relationship("PartyMst", back_populates="branches")
    # city = relationship("CityMst", foreign_keys=[city_id])

    class EntityTypeMst(Base):
        __tablename__ = "entity_type_mst"

        entity_type_id = Column(Integer, primary_key=True, autoincrement=True)
        entity_type_name = Column(String(30))