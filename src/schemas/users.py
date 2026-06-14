"""User-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from src.models.enums import UserRole


class UserOut(BaseModel):
    """Public-facing user representation returned in API responses."""

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    reputation_score: float
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
