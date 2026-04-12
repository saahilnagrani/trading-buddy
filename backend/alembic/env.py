import asyncio
import ssl as ssl_module
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
from app.models import Account, AccountToken  # noqa: F401 - needed for metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_engine_url_and_args():
    url = settings.async_database_url
    connect_args = {}
    if "sslmode=require" in settings.database_url or "neon.tech" in settings.database_url:
        connect_args["ssl"] = ssl_module.create_default_context()
        url = url.split("?")[0] if "?" in url else url
    return url, connect_args


def run_migrations_offline() -> None:
    url, _ = _get_engine_url_and_args()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url, connect_args = _get_engine_url_and_args()
    connectable = create_async_engine(url, poolclass=pool.NullPool, connect_args=connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
