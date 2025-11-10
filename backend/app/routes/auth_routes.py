from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.app import models
from backend.app.dependencies import get_auth_service, get_current_user
from backend.app.schemas import Token, UserCreate, UserOut
from backend.app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, auth_service: AuthService = Depends(get_auth_service)) -> UserOut:
    user = auth_service.create_user(payload)
    return UserOut.model_validate(user)


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_auth_service)
) -> Token:
    user = auth_service.authenticate(form_data.username, form_data.password)
    return auth_service.build_token_response(user)


@router.post("/refresh", response_model=Token)
def refresh_tokens(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)) -> Token:
    return auth_service.refresh_tokens(payload.refresh_token)


@router.get("/me", response_model=UserOut)
def me(current_user: models.User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
