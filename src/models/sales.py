"""
SQLAlchemy ORM models for sales tables.
Covers: quotation, order, delivery order, and invoice.
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
    BigInteger,
    String,
    DECIMAL,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all sales models."""
    pass


# =============================================================================
# INVOICE MODELS
# =============================================================================

class InvoiceHdr(Base):
    """Invoice header table."""
    __tablename__ = "sales_invoice"

    invoice_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    challan_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    challan_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.current_timestamp()
    )
    party_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    del_order_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    del_order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    footer_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    freight_charges: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    grand_total: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    intra_inter_state: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invoice_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_no_string: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_unique_no: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quote_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sale_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_state_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_state_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tax_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    terms_conditions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type_of_sale: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vehicle_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sale_order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payable_tax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tds_payable: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tds_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tds_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    broker_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pcso_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_removal_of_goods: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    administrative_office_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    fatory_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    destination_rail_head: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transporter_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    transporter_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transporter_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transporter_state_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transporter_state_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    container_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    net_weight: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    pack_sheet: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    total_weight: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    loading_point: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    contract_no: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    contract_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consignment_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    consignment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    packing_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pcso_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mr_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    claim_amount: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    tcs_percentage: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    tcs_amount: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    eway_bill_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    eway_bill_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    other_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    mr_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sale_order_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_conversion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    round_off: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    tally_sync: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="N")
    tax_payable: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="N")

    # Relationships
    line_items: Mapped[List["InvoiceLineItem"]] = relationship(
        "InvoiceLineItem", back_populates="invoice", lazy="selectin"
    )


class InvoiceLineItem(Base):
    """Sales invoice detail/line items table."""
    __tablename__ = "sales_invoice_dtl"

    invoice_line_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    amount_without_tax: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_amt: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_per: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    co_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    igst_amt: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    igst_per: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sales_invoice.invoice_id"), nullable=True, index=True
    )
    item_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    item_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    item_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_name: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    make: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_amt: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_per: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tax_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    tax_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    uom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uom_rate: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uom_2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qty_2: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    uom_3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qty_3: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    bales: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    packing_with_identification_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bales_srl_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cost_factor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    cost_factor_des: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    claim_amount_dtl: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    claim_desc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mr_line_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    quality_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    quality_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sales_bale: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    sales_drum: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    sales_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    destination_mr_line: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    claim_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sale_line_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    delivery_line_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    weight_of_bag: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)

    # Relationships
    invoice: Mapped[Optional["InvoiceHdr"]] = relationship(
        "InvoiceHdr", back_populates="line_items"
    )


# =============================================================================
# SALES QUOTATION MODELS
# =============================================================================

class SalesQuotation(Base):
    """Sales quotation header table."""
    __tablename__ = "sales_quotation"

    sales_quotation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    quotation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quotation_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    party_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    sales_broker_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billing_address_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shipping_address_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quotation_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    footer_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brokerage_percentage: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    round_off_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    terms_condition: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    internal_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    approval_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    details: Mapped[List["SalesQuotationDtl"]] = relationship(
        "SalesQuotationDtl", back_populates="quotation"
    )


class SalesQuotationDtl(Base):
    """Sales quotation detail/line items table."""
    __tablename__ = "sales_quotation_dtl"

    quotation_lineitem_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    sales_quotation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_quotation.sales_quotation_id"), nullable=True, index=True
    )
    hsn_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discounted_rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    quotation: Mapped[Optional["SalesQuotation"]] = relationship(
        "SalesQuotation", back_populates="details"
    )
    gst_details: Mapped[List["SalesQuotationDtlGst"]] = relationship(
        "SalesQuotationDtlGst", back_populates="quotation_dtl"
    )


class SalesQuotationDtlGst(Base):
    """GST details for sales quotation line items."""
    __tablename__ = "sales_quotation_dtl_gst"

    sales_quotation_dtl_gst_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quotation_lineitem_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_quotation_dtl.quotation_lineitem_id"), nullable=True, index=True
    )
    igst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    igst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    gst_total: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Relationships
    quotation_dtl: Mapped[Optional["SalesQuotationDtl"]] = relationship(
        "SalesQuotationDtl", back_populates="gst_details"
    )


# =============================================================================
# SALES ORDER MODELS
# =============================================================================

class SalesOrder(Base):
    """Sales order header table."""
    __tablename__ = "sales_order"

    sales_order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    sales_order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sales_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    quotation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_quotation.sales_quotation_id"), nullable=True, index=True
    )
    party_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    party_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    broker_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billing_to_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shipping_to_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transporter_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sales_order_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    broker_commission_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    footer_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    terms_conditions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    internal_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    freight_charges: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    approval_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    quotation: Mapped[Optional["SalesQuotation"]] = relationship("SalesQuotation")
    details: Mapped[List["SalesOrderDtl"]] = relationship(
        "SalesOrderDtl", back_populates="order"
    )


class SalesOrderDtl(Base):
    """Sales order detail/line items table."""
    __tablename__ = "sales_order_dtl"

    sales_order_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    sales_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_order.sales_order_id"), nullable=True, index=True
    )
    quotation_lineitem_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    hsn_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discounted_rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    order: Mapped[Optional["SalesOrder"]] = relationship(
        "SalesOrder", back_populates="details"
    )
    gst_details: Mapped[List["SalesOrderDtlGst"]] = relationship(
        "SalesOrderDtlGst", back_populates="order_dtl"
    )


class SalesOrderDtlGst(Base):
    """GST details for sales order line items."""
    __tablename__ = "sales_order_dtl_gst"

    sales_order_dtl_gst_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sales_order_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_order_dtl.sales_order_dtl_id"), nullable=True, index=True
    )
    igst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    igst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    gst_total: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Relationships
    order_dtl: Mapped[Optional["SalesOrderDtl"]] = relationship(
        "SalesOrderDtl", back_populates="gst_details"
    )


# =============================================================================
# SALES DELIVERY ORDER MODELS
# =============================================================================

class SalesDeliveryOrder(Base):
    """Sales delivery order header table. Represents physical dispatch against a sales order."""
    __tablename__ = "sales_delivery_order"

    sales_delivery_order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    delivery_order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delivery_order_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    sales_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_order.sales_order_id"), nullable=True, index=True
    )
    party_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    party_branch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billing_to_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shipping_to_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transporter_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vehicle_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    driver_contact: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    eway_bill_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    eway_bill_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    footer_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    internal_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    freight_charges: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    round_off_value: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    approval_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    sales_order: Mapped[Optional["SalesOrder"]] = relationship("SalesOrder")
    details: Mapped[List["SalesDeliveryOrderDtl"]] = relationship(
        "SalesDeliveryOrderDtl", back_populates="delivery_order"
    )


class SalesDeliveryOrderDtl(Base):
    """Sales delivery order detail/line items table."""
    __tablename__ = "sales_delivery_order_dtl"

    sales_delivery_order_dtl_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_date_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    sales_delivery_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_delivery_order.sales_delivery_order_id"), nullable=True, index=True
    )
    sales_order_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    hsn_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    item_make_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    uom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discounted_rate: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    net_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    delivery_order: Mapped[Optional["SalesDeliveryOrder"]] = relationship(
        "SalesDeliveryOrder", back_populates="details"
    )
    gst_details: Mapped[List["SalesDeliveryOrderDtlGst"]] = relationship(
        "SalesDeliveryOrderDtlGst", back_populates="delivery_order_dtl"
    )


class SalesDeliveryOrderDtlGst(Base):
    """GST details for sales delivery order line items."""
    __tablename__ = "sales_delivery_order_dtl_gst"

    sales_delivery_order_dtl_gst_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sales_delivery_order_dtl_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sales_delivery_order_dtl.sales_delivery_order_dtl_id"), nullable=True, index=True
    )
    igst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    igst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    cgst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_amount: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    sgst_percent: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    gst_total: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Relationships
    delivery_order_dtl: Mapped[Optional["SalesDeliveryOrderDtl"]] = relationship(
        "SalesDeliveryOrderDtl", back_populates="gst_details"
    )
