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

class JuteGateEntryHdr(Base):
    """Jute gate entry header table - stores gate entry information for incoming jute."""
    __tablename__ = "jute_gate_entry_hdr"

    rec_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    fin_year: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entry_company_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Supplier/Broker information
    supp_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    broker_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    broker_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mukam: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Challan/Consignment details
    po_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    with_without_po: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    challan_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    challan_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    challan_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    consignment_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    consignment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Vehicle/Transport details
    vehicle_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vehicle_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
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
    status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qc_check: Mapped[str] = mapped_column(String(255), nullable=False, default="N")
    mr_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Audit fields
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    update_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    update_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    auto_datetime_insert: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    details: Mapped[List["JuteGateEntryDtl"]] = relationship(
        "JuteGateEntryDtl", back_populates="header", foreign_keys="JuteGateEntryDtl.hdr_id"
    )


class JuteGateEntryDtl(Base):
    """Jute gate entry detail table - stores line item details for gate entries."""
    __tablename__ = "jute_gate_entry_dtl"

    rec_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hdr_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("jute_gate_entry_hdr.rec_id"), nullable=True, index=True
    )
    po_line_item_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Advised (from PO/Challan)
    advised_jute_typ: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    advised_quality: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    advised_quantity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    advised_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Actual (received)
    actual_jute_typ: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actual_quality: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actual_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    actual_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # QC (Quality Control verified)
    qc_jute_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qc_jute_quality: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qc_jute_quantity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qc_jute_weight: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Other details
    allowable_moisture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kgs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    received_in: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status and audit
    is_active: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="1")
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auto_datetime_insert: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )

    # Relationships
    header: Mapped[Optional["JuteGateEntryHdr"]] = relationship(
        "JuteGateEntryHdr", back_populates="details", foreign_keys=[hdr_id]
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
