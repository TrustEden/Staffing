from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    AGENCY_ADMIN = "agency_admin"
    AGENCY_STAFF = "agency_staff"


class CompanyType(str, Enum):
    FACILITY = "facility"
    AGENCY = "agency"


class ShiftStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


class ShiftVisibility(str, Enum):
    INTERNAL = "internal"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    AGENCY = "agency"
    ALL = "all"
    TIERED = "tiered"


class ClaimStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class RelationshipStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    REVOKED = "revoked"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class NotificationType(str, Enum):
    SHIFT_CLAIMED = "shift_claimed"
    SHIFT_APPROVED = "shift_approved"
    SHIFT_DENIED = "shift_denied"
    SHIFT_CANCELLED = "shift_cancelled"
    RELATIONSHIP_UPDATED = "relationship_updated"


BACK_TO_BACK_WARNING_MINUTES = 60
