from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.services.auth_service import AuthService
from backend.app.utils.constants import CompanyType, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    auth_service = AuthService(db)
    payload = auth_service.decode_token(token)
    user = db.get(models.User, payload.sub)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_roles(*roles: UserRole) -> Callable[[models.User], models.User]:
    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def get_current_facility_admin(
    current_user: models.User = Depends(require_roles(UserRole.ADMIN))
) -> models.User:
    if not current_user.company or current_user.company.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not tied to a facility")
    return current_user


def get_current_agency_admin(
    current_user: models.User = Depends(require_roles(UserRole.AGENCY_ADMIN))
) -> models.User:
    if not current_user.company or current_user.company.type != CompanyType.AGENCY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not tied to an agency")
    return current_user
