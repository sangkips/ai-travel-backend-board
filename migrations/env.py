import asyncio
from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Import the model registry so every model registers on Base.metadata,
# which autogenerate compares against the live database.
import src.models  # noqa: F401
from src.database import Base
from src.settings import settings

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Load DATABASE_URL from settings based on current environment
# The settings will automatically pick up the correct .env file based on ENVIRONMENT
# variable
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def include_object(obj, name, type_, reflected, compare_to):
    """Filter objects considered by ``--autogenerate``.

    The PostGIS image ships hundreds of system tables (the ``tiger`` geocoder,
    ``spatial_ref_sys``, ``topology``, …). They exist in the database but are not
    part of our models, so without this filter autogenerate emits ``DROP TABLE``
    for every one of them. Skip any reflected table that we don't define, then
    defer to GeoAlchemy2 for spatial index/column handling.
    """
    if type_ == "table" and name not in target_metadata.tables:
        return False
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


# Shared configuration for autogenerate so geometry columns render with the
# correct type + ``import geoalchemy2`` and spatial indexes are handled by
# GeoAlchemy2 rather than duplicated.
_AUTOGEN_OPTS = {
    "include_object": include_object,
    "render_item": alembic_helpers.render_item,
    "process_revision_directives": alembic_helpers.writer,
}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_AUTOGEN_OPTS,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        **_AUTOGEN_OPTS,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
