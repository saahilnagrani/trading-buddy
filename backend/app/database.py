import ssl as ssl_module

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Neon requires SSL; detect from sslmode in URL or non-localhost host
_url = settings.async_database_url
_connect_args = {}
if "sslmode=require" in settings.database_url or "neon.tech" in settings.database_url:
    _connect_args["ssl"] = ssl_module.create_default_context()
    # Strip sslmode param since asyncpg doesn't understand it
    _url = _url.split("?")[0] if "?" in _url else _url

engine = create_async_engine(_url, echo=False, connect_args=_connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
