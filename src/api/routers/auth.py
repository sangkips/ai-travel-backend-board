"""Auth router – sign-up and login endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_auth_service
from src.schemas.auth import LoginInput, SignUpInput, TokenResponse
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and receive a JWT",
)
async def signup(
    body: SignUpInput,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Create a new account.

    The user's role (Tourist, Tour Guide, Driver) is self-declared at sign-up.
    """
    try:
        return await service.sign_up(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT",
)
async def login(
    body: LoginInput,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Exchange email + password for a 7-day JWT bearer token."""
    try:
        return await service.login(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
