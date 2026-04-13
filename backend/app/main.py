from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import accounts, auth, orders, ws, baskets, strategies, portfolio, notifications, users
from app.routers.users import get_current_user
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

origins = [settings.frontend_url.rstrip("/")]
if settings.frontend_url != "http://localhost:3000":
    origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes (no auth required)
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Protected routes (require JWT auth)
_auth = [Depends(get_current_user)]
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"], dependencies=_auth)
app.include_router(orders.router, prefix="/api/orders", tags=["orders"], dependencies=_auth)
app.include_router(baskets.router, prefix="/api/baskets", tags=["baskets"], dependencies=_auth)
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"], dependencies=_auth)
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"], dependencies=_auth)
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"], dependencies=_auth)
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
