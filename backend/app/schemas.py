"""Pydantic schemas used by the FastAPI routes."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.utils.constants import (
    ClaimStatus,
    CompanyType,
    InvitationStatus,
    RelationshipStatus,
    ShiftStatus,
    ShiftVisibility,
    UserRole,
)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class TokenPayload(BaseModel):
    sub: UUID
    role: UserRole
    exp: int
    company_id: Optional[UUID] = None


class CompanyBase(BaseModel):
    name: str
    type: CompanyType
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    timezone: str = "America/New_York"


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None


class CompanyOut(CompanyBase):
    id: UUID
    display_id: str
    is_locked: bool = False

    model_config = ConfigDict(from_attributes=True)


class CompanyCreateWithAdmin(CompanyBase):
    """Schema for creating a company with its admin user."""
    admin_username: str
    admin_password: str = Field(min_length=8)
    admin_name: str
    admin_email: Optional[EmailStr] = None
    admin_phone: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: str
    license_number: Optional[str] = None
    role: UserRole = UserRole.STAFF
    company_id: Optional[UUID] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    license_number: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserOut(UserBase):
    id: UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ShiftBase(BaseModel):
    facility_id: UUID
    date: date
    start_time: time
    end_time: time
    role_required: str
    visibility: ShiftVisibility = ShiftVisibility.INTERNAL
    notes: Optional[str] = None
    is_premium: bool = False
    premium_notes: Optional[str] = None
    release_at: Optional[datetime] = None
    tier_1_release: Optional[datetime] = None
    tier_2_release: Optional[datetime] = None


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    role_required: Optional[str] = None
    visibility: Optional[ShiftVisibility] = None
    status: Optional[ShiftStatus] = None
    notes: Optional[str] = None
    is_premium: Optional[bool] = None
    premium_notes: Optional[str] = None
    release_at: Optional[datetime] = None


class ShiftOut(ShiftBase):
    id: UUID
    status: ShiftStatus
    posted_by_id: UUID
    posted_at: datetime
    facility_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClaimCreate(BaseModel):
    shift_id: UUID


class ClaimOut(BaseModel):
    id: UUID
    shift_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    status: ClaimStatus
    claimed_at: datetime
    approved_by_id: Optional[UUID] = None
    denial_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClaimWithShiftOut(ClaimOut):
    shift: ShiftOut

    model_config = ConfigDict(from_attributes=True)


class ClaimActionResponse(BaseModel):
    claim: ClaimOut
    warnings: list[str] = []


class ClaimDecisionRequest(BaseModel):
    reason: Optional[str] = None


class RelationshipCreate(BaseModel):
    facility_id: UUID
    agency_id: UUID


class RelationshipUpdate(BaseModel):
    status: RelationshipStatus


class RelationshipOut(BaseModel):
    id: UUID
    facility_id: UUID
    agency_id: UUID
    status: RelationshipStatus
    invited_by_id: Optional[UUID] = None
    invite_accepted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: UUID
    recipient_id: UUID
    type: str
    content: str
    read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    read: bool


class AuditLogOut(BaseModel):
    id: UUID
    actor_id: Optional[UUID]
    action: str
    entity: str
    entity_id: Optional[UUID]
    timestamp: datetime
    details: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class InvitationCreate(BaseModel):
    agency_email: EmailStr
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    id: UUID
    facility_id: UUID
    agency_email: str
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    facility_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Analytics response schemas
class FillRateResponse(BaseModel):
    facility_id: str
    start_date: date
    end_date: date
    total_shifts: int
    filled_shifts: int
    fill_rate_percentage: float

    model_config = ConfigDict(from_attributes=True)


class TimeToFillResponse(BaseModel):
    facility_id: str
    start_date: date
    end_date: date
    total_filled_shifts: int
    average_time_to_fill_hours: float
    min_time_to_fill_hours: float
    max_time_to_fill_hours: float

    model_config = ConfigDict(from_attributes=True)


class ShiftStatsResponse(BaseModel):
    facility_id: str
    start_date: date
    end_date: date
    total_shifts: int
    by_status: dict[str, int]
    by_visibility: dict[str, int]
    premium_shifts: int

    model_config = ConfigDict(from_attributes=True)


class AgencyPerformanceResponse(BaseModel):
    agency_id: str
    start_date: date
    end_date: date
    total_claims: int
    approved_claims: int
    denied_claims: int
    pending_claims: int
    approval_rate_percentage: float
    average_response_time_hours: float

    model_config = ConfigDict(from_attributes=True)

