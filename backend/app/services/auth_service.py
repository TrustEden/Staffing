from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.app import models
from backend.app.schemas import Token, TokenPayload, UserCreate
from backend.app.utils.constants import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(self, payload: UserCreate) -> models.User:
        user = models.User(
            username=payload.username.lower(),
            email=payload.email.lower() if payload.email else None,
            hashed_password=self.hash_password(payload.password),
            phone=payload.phone,
            name=payload.name,
            license_number=payload.license_number,
            role=payload.role,
            company_id=payload.company_id,
            is_active=True,
        )
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError as exc:  # pragma: no cover - handled in API layer
            self.session.rollback()
            if "uq_users_username" in str(getattr(exc, "orig", exc)):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
            raise
        self.session.refresh(user)
        return user

    def authenticate(self, username: str, password: str) -> models.User:
        user = self.session.query(models.User).filter(
            models.User.username == username.lower(), models.User.is_active.is_(True)
        ).one_or_none()
        if not user or not self.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return user

    def create_access_token(self, subject: UUID, role: UserRole, company_id: Optional[UUID]) -> tuple[str, int]:
        expires_delta = timedelta(minutes=self.settings.access_token_expire_minutes)
        expire_at = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": str(subject),
            "role": role.value,
            "company_id": str(company_id) if company_id else None,
            "exp": int(expire_at.timestamp()),
        }
        token = jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)
        return token, int(expires_delta.total_seconds())

    def create_refresh_token(self, subject: UUID, role: UserRole) -> tuple[str, int]:
        expires_delta = timedelta(minutes=self.settings.refresh_token_expire_minutes)
        expire_at = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": str(subject),
            "role": role.value,
            "exp": int(expire_at.timestamp()),
            "type": "refresh",
        }
        token = jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)
        return token, int(expires_delta.total_seconds())

    def build_token_response(self, user: models.User) -> Token:
        access_token, access_exp = self.create_access_token(user.id, user.role, user.company_id)
        refresh_token, refresh_exp = self.create_refresh_token(user.id, user.role)
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_exp,
            refresh_expires_in=refresh_exp,
        )

    def decode_token(self, token: str, *, refresh: bool = False) -> TokenPayload:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        except JWTError as exc:  # pragma: no cover - JWT already validated in tests
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        if refresh and payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        return TokenPayload(
            sub=UUID(payload["sub"]),
            role=UserRole(payload["role"]),
            exp=int(payload["exp"]),
            company_id=UUID(payload["company_id"]) if payload.get("company_id") else None,
        )

    def refresh_tokens(self, refresh_token: str) -> Token:
        token_payload = self.decode_token(refresh_token, refresh=True)
        user = self.session.get(models.User, token_payload.sub)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
        return self.build_token_response(user)
