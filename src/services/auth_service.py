"""Auth service – sign-up, login, and JWT token management."""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from src.models.enums import UserRole
from src.models.users import User
from src.repositories.user_repository import UserRepository
from src.schemas.auth import LoginInput, SignUpInput, TokenResponse
from src.schemas.users import UserOut
from src.settings import settings

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def _to_bcrypt_bytes(plain: str) -> bytes:
    """Encode a password for bcrypt, truncating to its 72-byte input limit.

    bcrypt only considers the first 72 bytes of a password and (since 4.1)
    raises on longer input, so we truncate explicitly to keep behaviour stable.
    """
    return plain.encode("utf-8")[:72]


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(_to_bcrypt_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))


def _create_access_token(user_id: str, role: UserRole) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jose.JWTError on invalid token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])


class AuthService:
    """Handles user registration and authentication."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._users = user_repo

    async def sign_up(self, data: SignUpInput) -> TokenResponse:
        """Register a new user and return a JWT.

        Raises ValueError if the email is already taken.
        """
        existing = await self._users.get_by_email(data.email)
        if existing:
            raise ValueError("An account with this email already exists")

        user = User(
            name=data.name,
            email=data.email,
            phone=data.phone,
            role=data.role,
            password_hash=_hash_password(data.password),
        )
        user = await self._users.create(user)
        token = _create_access_token(str(user.id), user.role)
        return TokenResponse(access_token=token)

    async def login(self, data: LoginInput) -> TokenResponse:
        """Authenticate a user and return a JWT.

        Raises ValueError on invalid credentials.
        """
        user = await self._users.get_by_email(data.email)
        if not user or not _verify_password(data.password, user.password_hash):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        token = _create_access_token(str(user.id), user.role)
        return TokenResponse(access_token=token)

    async def get_current_user(self, user_id: str) -> UserOut:
        """Return the currently authenticated user's public profile."""
        user = await self._users.get_by_id(user_id)  # type: ignore[arg-type]
        if not user:
            raise ValueError("User not found")
        return UserOut.model_validate(user)
