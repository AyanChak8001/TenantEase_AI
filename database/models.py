from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.db import Base

class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.id"), nullable=True, index=True)
    property_name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(200))
    total_units: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(30))
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    unit_id: Mapped[str] = mapped_column(String(30))
    monthly_rent: Mapped[float] = mapped_column(Float)
    due_day: Mapped[int] = mapped_column(Integer, default=1)
    lease_start_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class RentRecord(Base):
    __tablename__ = "rent_records"
    __table_args__ = (UniqueConstraint("tenant_id", "rent_month", name="uq_tenant_cycle"), Index("ix_rent_status", "status"))
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    rent_month: Mapped[str] = mapped_column(String(7))
    rent_amount: Mapped[float] = mapped_column(Float)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="UPCOMING")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    rent_record_id: Mapped[int] = mapped_column(ForeignKey("rent_records.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str] = mapped_column(String(30))
    transaction_reference: Mapped[str] = mapped_column(String(80), unique=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (UniqueConstraint("tenant_id", "rent_record_id", "notification_type", "event_key", name="uq_notification_event"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    rent_record_id: Mapped[int] = mapped_column(ForeignKey("rent_records.id"), index=True)
    notification_type: Mapped[str] = mapped_column(String(30))
    event_key: Mapped[str] = mapped_column(String(100), default="legacy", nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    rent_record_id: Mapped[int] = mapped_column(ForeignKey("rent_records.id"), index=True)
    risk_probability: Mapped[float] = mapped_column(Float)
    risk_category: Mapped[str] = mapped_column(String(20))
    model_version: Mapped[str] = mapped_column(String(30))
    prediction_date: Mapped[date] = mapped_column(Date)
    explanation: Mapped[str] = mapped_column(Text)
