from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
_EXEMPT = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
}


def _normalized_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


class OriginAllowlistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in _MUTATING:
            path = _normalized_path(request.url.path)
            if (request.method, path) not in _EXEMPT:
                origin = request.headers.get("origin")
                if origin is not None and origin not in settings.public_origin_list:
                    return JSONResponse({"detail": "Invalid origin"}, status_code=403)
        return await call_next(request)
