"""Model registry.

Import every model module here so that importing ``src.models`` populates
``Base.metadata`` with all tables. Alembic's ``--autogenerate`` and
``Base.metadata.create_all`` only see models that have been imported, so any
new model module must be added to ``__all__`` below.
"""

from src.models.users import User

__all__ = ["User"]
