"""
SQLAlchemy ORM models for jute tables (jute_*).
Auto-generated from database schema: sls
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Double,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all jute models."""
    pass


# =============================================================================
# JUTE QUALITY MASTER
# =============================================================================

class JuteQualityMst(Base):
    """Jute quality master table - stores quality information for jute items."""
    __tablename__ = "jute_quality_mst"

    jute_qlty_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    jute_quality: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )


# =============================================================================
# JUTE GATE ENTRY MODELS
# =============================================================================

class JuteGateEntry(Base):
    """Jute gate entry table - stores gate entry information for incoming jute."""
    __tablename__ = "jute_gate_entry"

    jute_gate_entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_company_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Supplier/Party information
    jute_supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    party_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    mukam: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # PO reference
    po_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Challan/Consignment details
    challan_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    challan_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    challan_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    consignment_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    consignment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Vehicle/Transport details
    vehicle_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vehicle_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    transporter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Weight measurements
    gross_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True, default=0)
    tare_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True, default=0)
    actual_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True, default=0)
    unit_conversion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Date/Time tracking
    in_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    in_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    out_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    out_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status and QC
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qc_check: Mapped[str] = mapped_column(String(255), nullable=False, default="N")
    marketing_slip: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Audit fields
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    line_items: Mapped[List["JuteGateEntryLi"]] = relationship(
        "JuteGateEntryLi", back_populates="gate_entry", foreign_keys="JuteGateEntryLi.jute_gate_entry_id"
    )


class JuteGateEntryLi(Base):
    """Jute gate entry line item table - stores line item details for gate entries."""
    __tablename__ = "jute_gate_entry_li"

    jute_gate_entry_li_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jute_gate_entry_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("jute_gate_entry.jute_gate_entry_id"), nullable=True, index=True
    )
    po_line_item_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Challan details (from PO/Challan)
    challan_item_name_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    challan_jute_quality_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    challan_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    challan_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Actual (received) details
    actual_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actual_jute_quality_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actual_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    actual_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # QC (Quality Control verified) details
    qc_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qc_jute_quality_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qc_jute_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qc_jute_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Other details
    allowable_moisture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    jute_uom: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status and audit
    active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    updated_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )

    # Relationships
    gate_entry: Mapped[Optional["JuteGateEntry"]] = relationship(
        "JuteGateEntry", back_populates="line_items", foreign_keys=[jute_gate_entry_id]
    )


# =============================================================================
# JUTE ISSUE MODELS
# =============================================================================

class JuteIssue(Base):
    """Jute issue table - stores jute issue transactions to production/departments."""
    __tablename__ = "jute_issue"

    issue_no: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    fin_year: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Issue details
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    issue_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    issue_value: Mapped[Optional[Decimal]] = mapped_column(Double, nullable=True)
    
    # Jute details
    jute_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    jute_quality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Quantity and stock
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    no_bales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bale_loose: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_stock: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close_stock: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stock_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Location/Assignment
    dept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    godown_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    side: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # References
    mr_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    yarn_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wastage_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    uom_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status and audit
    is_active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    create_date_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    update_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class JuteIssuePrimary(Base):
    """Jute issue primary table - stores primary issue records for jute to production."""
    __tablename__ = "jute_issue_primary"

    jute_issue_primary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Issue details
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Jute details
    jute_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    jute_quality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Quantity and weight
    no_of_bales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    no_of_bales_issued: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    bale_or_loose: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gross_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tare_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Location/Assignment
    godown_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    side: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trolly_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    yarn_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # References
    mr_line_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status and audit
    is_active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auto_date_time_insert: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


# =============================================================================
# JUTE SUPPLIER MODELS
# =============================================================================

class JuteSupplierMst(Base):
    """Jute supplier master table - stores jute supplier information."""
    __tablename__ = "jute_supplier_mst"

    supplier_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )

    # Relationships
    party_mappings: Mapped[List["JuteSuppPartyMap"]] = relationship(
        "JuteSuppPartyMap", back_populates="jute_supplier"
    )


class JuteSuppPartyMap(Base):
    """Jute supplier to party mapping table - maps jute suppliers to party master."""
    __tablename__ = "jute_supp_party_map"

    map_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    jute_supplier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("jute_supplier_mst.supplier_id"), nullable=True, index=True
    )
    supp_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_mapped: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    jute_supplier: Mapped[Optional["JuteSupplierMst"]] = relationship(
        "JuteSupplierMst", back_populates="party_mappings"
    )


# =============================================================================
# JUTE MUKAM MASTER MODEL
# =============================================================================

class JuteMukamMst(Base):
    """Jute mukam master table - stores mukam (location) information for jute."""
    __tablename__ = "jute_mukam_mst"

    mukam_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mukam_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )


# =============================================================================
# JUTE LORRY MASTER MODEL
# =============================================================================

class JuteLorryMst(Base):
    """Jute lorry master table - stores lorry type and weight information for jute logistics."""
    __tablename__ = "jute_lorry_mst"

    jute_lorry_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lorry_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )


# =============================================================================
# JUTE PO MODELS
# =============================================================================

class JutePo(Base):
    """Jute purchase order header table - stores jute PO transactions."""
    __tablename__ = "jute_po"

    jute_po_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    party_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    jute_mukam_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    jute_indent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # PO identification
    po_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    po_num: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    po_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    po_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Contract details
    contract_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contract_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    channel_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Terms and charges
    credit_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_days: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    frieght_charge: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    brokrage_rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    brokrage_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    penalty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Vehicle details
    vehicle_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vehicle_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Value and weight
    jute_po_value: Mapped[Optional[Decimal]] = mapped_column(Double, nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    jute_uom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Notes and remarks
    remarks: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    internal_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    footer_note: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    
    # Audit fields
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )

    # Relationships
    line_items: Mapped[List["JutePoLi"]] = relationship(
        "JutePoLi", back_populates="jute_po"
    )


class JutePoLi(Base):
    """Jute purchase order line item table - stores individual items in a jute PO."""
    __tablename__ = "jute_po_li"

    jute_po_li_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jute_po_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("jute_po.jute_po_id"), nullable=True, index=True
    )
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # PO reference
    po_num: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    indent_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Jute details
    quality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    marka: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    crop_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Quantity details
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cancel_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    bale: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    loose: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    allowable_moisture_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Pricing
    rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_wo_tax: Mapped[Optional[Decimal]] = mapped_column(Double, nullable=True)
    value_wt_tax: Mapped[Optional[Decimal]] = mapped_column(Double, nullable=True)
    
    # Status
    status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="1")
    
    # Audit
    auto_datetime_insert: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    jute_po: Mapped[Optional["JutePo"]] = relationship(
        "JutePo", back_populates="line_items"
    )
