"""Shared SQLAlchemy-compatible enums used across models.

Defining enums here prevents circular imports between model modules.
The same values are mirrored in the Strawberry GraphQL schema.
"""

import enum


class UserRole(str, enum.Enum):
    """Self-declared role chosen at sign-up."""

    TOURIST = "TOURIST"
    TOUR_GUIDE = "TOUR_GUIDE"
    DRIVER = "DRIVER"


class TourismType(str, enum.Enum):
    """Category of tourism experience associated with a review."""

    ADVENTURE = "ADVENTURE"
    CULTURAL = "CULTURAL"
    NIGHTLIFE = "NIGHTLIFE"
    FAMILY = "FAMILY"
    NATURE = "NATURE"
    RELAXATION = "RELAXATION"


class SafetyLabel(str, enum.Enum):
    """Derived safety label computed from average_safety_score."""

    SAFE = "SAFE"  # avg >= 4.0
    CAUTION = "CAUTION"  # avg >= 2.5
    AVOID = "AVOID"  # avg <  2.5
