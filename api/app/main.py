from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app import db

app = FastAPI(title="arpw-local")
api = APIRouter(prefix="/api")


@api.get("/health")
async def health() -> dict[str, str]:
    """Liveness. async, no I/O — stays green while ingest occupies a worker."""
    return {"status": "ok"}


@api.get("/ready")
def ready() -> dict[str, str]:
    """Readiness. Sync SELECT 1 against Postgres."""
    with db.SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(api)
