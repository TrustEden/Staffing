"""SQLAlchemy models for the healthcare staffing bridge application."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.utils.constants import (
    ClaimStatus,
    CompanyType,
    InvitationStatus,
    RelationshipStatus,
    ShiftStatus,
    ShiftVisibility,
    UserRole,
)


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


ENUM_KWARGS = {
    "native_enum": False,
    "create_constraint": False,
    "values_callable": _enum_values,
}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )


class Company(Base, TimestampMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("display_id", name="uq_company_display_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[CompanyType] = mapped_column(Enum(CompanyType, **ENUM_KWARGS), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str | None] = mapped_column(String(50), default="America/New_York")
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="company", cascade="all, delete")
    shifts: Mapped[list["Shift"]] = relationship(back_populates="facility", cascade="all, delete")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, **ENUM_KWARGS), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company: Mapped[Company | None] = relationship(back_populates="users")
    posted_shifts: Mapped[list["Shift"]] = relationship("Shift", back_populates="posted_by_user", foreign_keys="Shift.posted_by_id")
    claims: Mapped[list["Claim"]] = relationship(back_populates="user", foreign_keys="Claim.user_id", cascade="all, delete")
    approved_claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="approved_by_user", foreign_keys="Claim.approved_by_id"
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="recipient")


class Shift(Base, TimestampMixin):
    __tablename__ = "shifts"
    # Removed time range constraint to allow overnight shifts (e.g., 6P-6A)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    role_required: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ShiftStatus] = mapped_column(Enum(ShiftStatus, **ENUM_KWARGS), default=ShiftStatus.OPEN)
    visibility: Mapped[ShiftVisibility] = mapped_column(
        Enum(ShiftVisibility, **ENUM_KWARGS), default=ShiftVisibility.INTERNAL
    )
    posted_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_notes: Mapped[str | None] = mapped_column(Text)
    recurring_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tier_1_release: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tier_2_release: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    facility: Mapped[Company] = relationship(back_populates="shifts")
    posted_by_user: Mapped[User] = relationship(back_populates="posted_shifts", foreign_keys=[posted_by_id])
    claims: Mapped[list["Claim"]] = relationship(back_populates="shift", cascade="all, delete-orphan")


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("shift_id", "user_id", name="uq_claim_shift_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, **ENUM_KWARGS), default=ClaimStatus.PENDING)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    denial_reason: Mapped[str | None] = mapped_column(Text)

    shift: Mapped[Shift] = relationship(back_populates="claims")
    user: Mapped[User] = relationship(back_populates="claims", foreign_keys=[user_id])
    approved_by_user: Mapped[User | None] = relationship(
        back_populates="approved_claims", foreign_keys=[approved_by_id]
    )


class Relationship(Base, TimestampMixin):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint("facility_id", "agency_id", name="uq_relationship_facility_agency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    agency_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    status: Mapped[RelationshipStatus] = mapped_column(Enum(RelationshipStatus, **ENUM_KWARGS))
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    invite_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    facility: Mapped[Company] = relationship("Company", foreign_keys=[facility_id], backref="agency_relationships")
    agency: Mapped[Company] = relationship("Company", foreign_keys=[agency_id], backref="facility_relationships")
    invited_by: Mapped[User | None] = relationship("User")


class Invitation(Base, TimestampMixin):
    __tablename__ = "invitations"
    __table_args__ = (
        UniqueConstraint("token", name="uq_invitation_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    agency_email: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, **ENUM_KWARGS), default=InvitationStatus.PENDING
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    facility: Mapped[Company] = relationship("Company", foreign_keys=[facility_id])


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    recipient: Mapped[User] = relationship(back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)

    actor: Mapped[User | None] = relationship("User")
