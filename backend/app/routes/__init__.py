from fastapi import FastAPI

from .admin_routes import router as admin_router
from .agency_routes import router as agency_router
from .analytics_routes import router as analytics_router
from .auth_routes import router as auth_router
from .claim_routes import router as claim_router
from .facility_routes import router as facility_router
from .invitation_routes import router as invitation_router
from .notification_routes import router as notification_router
from .shift_routes import router as shift_router
from .upload_routes import router as upload_router


def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(facility_router, prefix="/api/facilities")
    app.include_router(agency_router, prefix="/api/agencies")
    app.include_router(shift_router, prefix="/api/shifts")
    app.include_router(claim_router, prefix="/api/claims")
    app.include_router(upload_router, prefix="/api/uploads")
    app.include_router(notification_router, prefix="/api/notifications")
    app.include_router(invitation_router, prefix="/api/invitations")
    app.include_router(admin_router, prefix="/api/admin")
    app.include_router(analytics_router, prefix="/api/analytics")

