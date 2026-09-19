from fastapi import APIRouter, FastAPI

app = FastAPI(title="arpw-local")
api = APIRouter(prefix="/api")


@api.get("/health")
async def health() -> dict[str, str]:
    """Liveness. async, no I/O — stays green while ingest occupies a worker."""
    return {"status": "ok"}


@api.get("/ready")
def ready() -> dict[str, str]:
    """Readiness. Slice 01 stub; PR 02 adds SELECT 1 against Postgres."""
    return {"status": "ok"}


app.include_router(api)
