from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import accounts, auth, orders, ws, baskets, strategies, portfolio, notifications
from app.tasks.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    from app.redis import redis_pool
    await redis_pool.aclose()


app = FastAPI(title="Trading Buddy", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(baskets.router, prefix="/api/baskets", tags=["baskets"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
