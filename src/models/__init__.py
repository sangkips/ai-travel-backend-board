"""Model registry.

Import every model module here so that importing ``src.models`` populates
``Base.metadata`` with all tables. Alembic's ``--autogenerate`` and
``Base.metadata.create_all`` only see models that have been imported, so any
new model module must be added to ``__all__`` below.
"""

from src.models.notifications import Notification
from src.models.places import Place
from src.models.reviews import Review
from src.models.users import User
from src.models.votes import Vote

__all__ = ["User", "Place", "Review", "Vote", "Notification"]
