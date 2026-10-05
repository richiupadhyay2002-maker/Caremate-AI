"""Alembic migration environment for Caremate AI.

Migrations are generated from the SQLAlchemy ORM models in
``caremate.db.models``.  The ``Base.metadata`` is the single source of truth
for the schema — both ``init_db()`` (dev/test) and Alembic migrations
(production) derive from it.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# -- Import the target metadata and models ---------------------------------
from caremate.db.models import Base  # noqa: E402  (registers all tables)
from caremate.utils.config import get_settings  # noqa: E402

# -- Alembic config ---------------------------------------------------------
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database URL from app settings (env-var driven)."""
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to the DB directly)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        url=get_url(),
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

