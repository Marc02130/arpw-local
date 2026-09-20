from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app import db
from app.config import settings
from app.origin import OriginAllowlistMiddleware
from app.routers.auth import router as auth_router
from app.routers.settings import router as settings_router
from app.routers.documents import router as documents_router
from app.routers.papers import router as papers_router
from app.routers.citations import router as citations_router

app = FastAPI(title="arpw-local")
app.add_middleware(OriginAllowlistMiddleware)

if settings.cors_origin_list:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(settings_router)
api.include_router(documents_router)
api.include_router(papers_router)
api.include_router(citations_router)


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
