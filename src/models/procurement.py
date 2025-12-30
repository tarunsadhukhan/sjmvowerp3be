"""
SQLAlchemy ORM models for procurement tables (proc_*).
Auto-generated from database schema: sls
"""

from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all procurement models."""
    pass


# =============================================================================
# ENQUIRY MODELS
# =============================================================================

class ProcEnquiry(Base):
    """Price enquiry header table."""
    __tablename__ = "proc_enquiry"

    enquiry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    price_enquiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    price_enquiry_squence_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    suppliers: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    terms_conditions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    details: Mapped[List["ProcEnquiryDtl"]] = relationship(
        "ProcEnquiryDtl", back_populates="enquiry"
    )
    responses: Mapped[List["ProcPriceEnquiryResponse"]] = relationship(
        "ProcPriceEnquiryResponse", back_populates="enquiry"
    )


class ProcEnquiryDtl(Base):
    """Price enquiry detail/line items table."""
    __tablename__ = "proc_enquiry_dtl"

    enquiry_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enquiry_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_enquiry.enquiry_id"), nullable=True, index=True
    )
    indent_dtl_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    enquiry: Mapped[Optional["ProcEnquiry"]] = relationship(
        "ProcEnquiry", back_populates="details"
    )


# =============================================================================
# GST MODEL
# =============================================================================

class ProcGst(Base):
    """GST details for procurement inward items."""
    __tablename__ = "proc_gst"

    gst_invoice_type: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proc_inward_dtl: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    tax_pct: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    stax_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    s_tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    i_tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    i_tax_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    c_tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    c_tax_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


# =============================================================================
# INDENT MODELS
# =============================================================================

class ProcIndent(Base):
    """Purchase indent header table."""
    __tablename__ = "proc_indent"

    indent_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indent_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    indent_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    indent_type_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    expense_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    indent_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approval_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    details: Mapped[List["ProcIndentDtl"]] = relationship(
        "ProcIndentDtl", back_populates="indent"
    )


class ProcIndentDtl(Base):
    """Purchase indent detail/line items table."""
    __tablename__ = "proc_indent_dtl"

    indent_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_indent.indent_id"), nullable=True, index=True
    )
    required_by_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(599), nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    dept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    state: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    indent: Mapped[Optional["ProcIndent"]] = relationship(
        "ProcIndent", back_populates="details"
    )
    cancellations: Mapped[List["ProcIndentDtlCancel"]] = relationship(
        "ProcIndentDtlCancel", back_populates="indent_dtl"
    )


class ProcIndentDtlCancel(Base):
    """Cancelled indent detail line items."""
    __tablename__ = "proc_indent_dtl_cancel"

    indent_dtl_cancel_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indent_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_indent_dtl.indent_dtl_id"), nullable=True, index=True
    )
    cancelled_by: Mapped[int] = mapped_column(Integer, nullable=False)
    cancelled_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    cancelled_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cancelled_reasons: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    indent_dtl: Mapped[Optional["ProcIndentDtl"]] = relationship(
        "ProcIndentDtl", back_populates="cancellations"
    )


# =============================================================================
# INWARD MODELS
# =============================================================================

class ProcInward(Base):
    """Goods inward/receipt header table."""
    __tablename__ = "proc_inward"

    inward_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inward_sequence_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    driver_contact_number: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    inward_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    despatch_remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    receipts_remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_recvd_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    challan_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    challan_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consignment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consignment_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ewaybillno: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ewaybill_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    bill_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    ship_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    inspection_check: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    inspection_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    inspection_approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sr_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    sr_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sr_approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sr_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sr_remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sr_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billpass_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    billpass_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    billpass_approve_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    billpass_approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billpass_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    round_off_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    internal_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Relationships
    details: Mapped[List["ProcInwardDtl"]] = relationship(
        "ProcInwardDtl", back_populates="inward"
    )
    tds_details: Mapped[List["ProcTds"]] = relationship(
        "ProcTds", back_populates="inward"
    )
    drcr_notes: Mapped[List["DrcrNote"]] = relationship(
        "DrcrNote", back_populates="inward"
    )


class ProcInwardDtl(Base):
    """Goods inward/receipt detail/line items table."""
    __tablename__ = "proc_inward_dtl"

    inward_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inward_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("proc_inward.inward_id"), nullable=False, index=True
    )
    po_dtl_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bigint in DB
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    accepted_item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    challan_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    inward_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    approved_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rejected_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    reasons: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    accepted_rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_mode: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    updated_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    inward: Mapped["ProcInward"] = relationship(
        "ProcInward", back_populates="details"
    )
    drcr_note_details: Mapped[List["DrcrNoteDtl"]] = relationship(
        "DrcrNoteDtl", back_populates="inward_dtl"
    )


# =============================================================================
# PURCHASE ORDER (PO) MODELS
# =============================================================================

class ProcPo(Base):
    """Purchase order header table."""
    __tablename__ = "proc_po"

    po_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    credit_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_instructions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    footer_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    po_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    po_approve_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    po_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_mode: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    terms_conditions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    price_enquiry_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    supplier_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billing_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shipping_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    advance_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    advance_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    advance_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    contact_no: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    approval_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expense_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    details: Mapped[List["ProcPoDtl"]] = relationship(
        "ProcPoDtl", back_populates="po"
    )
    additional_charges: Mapped[List["ProcPoAdditional"]] = relationship(
        "ProcPoAdditional", back_populates="po"
    )


class ProcPoDtl(Base):
    """Purchase order detail/line items table."""
    __tablename__ = "proc_po_dtl"

    po_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_po.po_id"), nullable=True, index=True
    )
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    discount_mode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    indent_dtl_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    state: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    po: Mapped[Optional["ProcPo"]] = relationship(
        "ProcPo", back_populates="details"
    )
    cancellations: Mapped[List["ProcPoDtlCancel"]] = relationship(
        "ProcPoDtlCancel", back_populates="po_dtl"
    )
    gst_details: Mapped[List["PoGst"]] = relationship(
        "PoGst", back_populates="po_dtl"
    )


class ProcPoAdditional(Base):
    """Purchase order additional charges table."""
    __tablename__ = "proc_po_additional"

    po_additional_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_po.po_id"), nullable=True, index=True
    )
    additional_charges_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    po: Mapped[Optional["ProcPo"]] = relationship(
        "ProcPo", back_populates="additional_charges"
    )
    gst_details: Mapped[List["PoGst"]] = relationship(
        "PoGst", back_populates="po_additional"
    )


class ProcPoDtlCancel(Base):
    """Cancelled purchase order detail line items."""
    __tablename__ = "proc_po_dtl_cancel"

    po_dtl_cancel_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_po_dtl.po_dtl_id"), nullable=True, index=True
    )
    cancel_qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cancel_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cancel_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    po_dtl: Mapped[Optional["ProcPoDtl"]] = relationship(
        "ProcPoDtl", back_populates="cancellations"
    )


# =============================================================================
# PRICE ENQUIRY RESPONSE MODELS
# =============================================================================

class ProcPriceEnquiryResponse(Base):
    """Price enquiry response header table."""
    __tablename__ = "proc_price_enquiry_response"

    proc_price_enquiry_response_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    enquiry_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_enquiry.enquiry_id"), nullable=True, index=True
    )
    response_date: Mapped[Optional[date]] = mapped_column("date", Date, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    created_by_ip: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    terms_conditions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Relationships
    enquiry: Mapped[Optional["ProcEnquiry"]] = relationship(
        "ProcEnquiry", back_populates="responses"
    )
    details: Mapped[List["ProcPriceEnquiryResponseDtl"]] = relationship(
        "ProcPriceEnquiryResponseDtl", back_populates="response"
    )


class ProcPriceEnquiryResponseDtl(Base):
    """Price enquiry response detail/line items table."""
    __tablename__ = "proc_price_enquiry_response_dtl"

    proc_price_enquiry_response_dtl_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    enquiry_dtl_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_mode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    response: Mapped[Optional["ProcPriceEnquiryResponse"]] = relationship(
        "ProcPriceEnquiryResponse", back_populates="details", foreign_keys="ProcPriceEnquiryResponseDtl.enquiry_dtl_id"
    )


# =============================================================================
# TDS MODEL
# =============================================================================

class ProcTds(Base):
    """TDS (Tax Deducted at Source) details for procurement inward."""
    __tablename__ = "proc_tds"

    proc_tds_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inward_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_inward.inward_id"), nullable=True
    )
    itc_applicable: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tds_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    tds_pctg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tds_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tcs_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    inward: Mapped[Optional["ProcInward"]] = relationship(
        "ProcInward", back_populates="tds_details"
    )


# =============================================================================
# TRANSFER MODELS
# =============================================================================

class ProcTransfer(Base):
    """Stock/material transfer header table."""
    __tablename__ = "proc_transfer"

    transfer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transfer_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transfer_sequence_no: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    transfer_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    scrap: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Relationships
    details: Mapped[List["ProcTransferDtl"]] = relationship(
        "ProcTransferDtl", back_populates="transfer"
    )


class ProcTransferDtl(Base):
    """Stock/material transfer detail/line items table."""
    __tablename__ = "proc_transfer_dtl"

    transfer_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_transfer.transfer_id"), nullable=True, index=True
    )
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    qty: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    to_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    from_warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    transfer: Mapped[Optional["ProcTransfer"]] = relationship(
        "ProcTransfer", back_populates="details"
    )


# =============================================================================
# PO GST MODEL
# =============================================================================

class PoGst(Base):
    """GST details for purchase order items and additional charges."""
    __tablename__ = "po_gst"

    po_gst_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_po_dtl.po_dtl_id"), nullable=True, index=True
    )
    po_additional_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_po_additional.po_additional_id"), nullable=True, index=True
    )
    tax_pct: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    stax_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    s_tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    i_tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    i_tax_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    c_tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    c_tax_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    po_dtl: Mapped[Optional["ProcPoDtl"]] = relationship(
        "ProcPoDtl", back_populates="gst_details"
    )
    po_additional: Mapped[Optional["ProcPoAdditional"]] = relationship(
        "ProcPoAdditional", back_populates="gst_details"
    )


# =============================================================================
# DEBIT/CREDIT NOTE MODELS
# =============================================================================

class DrcrNote(Base):
    """Debit/Credit note header table."""
    __tablename__ = "drcr_note"

    debit_credit_note_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_date: Mapped[Optional[date]] = mapped_column("date", Date, nullable=True)
    adjustment_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inward_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_inward.inward_id"), nullable=True, index=True
    )
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    auto_create: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    round_off_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Relationships
    inward: Mapped[Optional["ProcInward"]] = relationship(
        "ProcInward", back_populates="drcr_notes"
    )
    details: Mapped[List["DrcrNoteDtl"]] = relationship(
        "DrcrNoteDtl", back_populates="drcr_note"
    )


class DrcrNoteDtl(Base):
    """Debit/Credit note detail/line items table."""
    __tablename__ = "drcr_note_dtl"

    drcr_note_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inward_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("proc_inward_dtl.inward_dtl_id"), nullable=True, index=True
    )
    debitnote_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_mode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    drcr_note: Mapped[Optional["DrcrNote"]] = relationship(
        "DrcrNote", back_populates="details", foreign_keys="DrcrNoteDtl.inward_dtl_id"
    )
    inward_dtl: Mapped[Optional["ProcInwardDtl"]] = relationship(
        "ProcInwardDtl", back_populates="drcr_note_details"
    )
    gst_details: Mapped[List["DrcrNoteDtlGst"]] = relationship(
        "DrcrNoteDtlGst", back_populates="drcr_note_dtl"
    )


class DrcrNoteDtlGst(Base):
    """GST details for debit/credit note line items."""
    __tablename__ = "drcr_note_dtl_gst"

    drcr_note_dtl_gst_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drcr_note_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("drcr_note_dtl.drcr_note_dtl_id"), nullable=True, index=True
    )
    cgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    igst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Relationships
    drcr_note_dtl: Mapped[Optional["DrcrNoteDtl"]] = relationship(
        "DrcrNoteDtl", back_populates="gst_details"
    )


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

__all__ = [
    "Base",
    # Enquiry
    "ProcEnquiry",
    "ProcEnquiryDtl",
    # GST
    "ProcGst",
    # Indent
    "ProcIndent",
    "ProcIndentDtl",
    "ProcIndentDtlCancel",
    # Inward
    "ProcInward",
    "ProcInwardDtl",
    # PO
    "ProcPo",
    "ProcPoDtl",
    "ProcPoAdditional",
    "ProcPoDtlCancel",
    # PO GST
    "PoGst",
    # Price Enquiry Response
    "ProcPriceEnquiryResponse",
    "ProcPriceEnquiryResponseDtl",
    # TDS
    "ProcTds",
    # Transfer
    "ProcTransfer",
    "ProcTransferDtl",
    # Debit/Credit Notes
    "DrcrNote",
    "DrcrNoteDtl",
    "DrcrNoteDtlGst",
]
