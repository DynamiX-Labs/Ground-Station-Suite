import asyncio
import concurrent.futures
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from db.models import AwareDateTime, Base, JsonField

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import the database models and configuration
# We need to handle arguments differently for alembic

# Get the database path from environment or use default
db_path = os.environ.get("GS_DB", "data/db/gs.db")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def _build_database_url(path: str) -> str:
    if os.path.isabs(path):
        return f"sqlite+aiosqlite:///{os.path.abspath(path)}"
    return f"sqlite+aiosqlite:///./{path}"


# Set the SQLAlchemy URL from our application configuration
config.set_main_option("sqlalchemy.url", _build_database_url(db_path))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# We skip this when running from the application context (ALEMBIC_CONTEXT=1)
# to use the application's logging configuration instead
if config.config_file_name is not None and not os.environ.get("ALEMBIC_CONTEXT"):
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Custom rendering for types that alembic doesn't understand."""
    if type_ == "type" and isinstance(obj, type(AwareDateTime())):
        # Render AwareDateTime as DateTime
        autogen_context.imports.add("from sqlalchemy import DateTime")
        return "DateTime(timezone=False)"

    if type_ == "type" and isinstance(obj, type(JsonField())):
        # Render JsonField as JSON
        autogen_context.imports.add("from sqlalchemy import JSON")
        return "JSON()"

    return False


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # For SQLite ALTER TABLE support
        render_item=render_item,  # Custom type rendering
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # For SQLite ALTER TABLE support
        render_item=render_item,  # Custom type rendering
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode for async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Check if there's already a running event loop
    try:
        asyncio.get_running_loop()
        # We're in an async context, so we need to run this differently
        # Use a new thread to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, run_async_migrations())
            future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
