from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_DEV = ROOT / "docker-compose.dev.yml"
ENV_EXAMPLE = ROOT / ".env.example"
NGINX = ROOT / "web" / "nginx.conf"
API_MAIN = ROOT / "api" / "app" / "main.py"
ALEMBIC_INITIAL = ROOT / "api" / "alembic" / "versions" / "0001_initial.py"
AUTH_ROUTER = ROOT / "api" / "app" / "routers" / "auth.py"
DOCUMENTS_ROUTER = ROOT / "api" / "app" / "routers" / "documents.py"
PAPERS_ROUTER = ROOT / "api" / "app" / "routers" / "papers.py"
GENERATE_SERVICE = ROOT / "api" / "app" / "services" / "generate.py"
SETTINGS_ROUTER = ROOT / "api" / "app" / "routers" / "settings.py"
WEBPACK = ROOT / "web" / "webpack.config.js"
WEB_PACKAGE = ROOT / "web" / "package.json"
WEB_APP = ROOT / "web" / "src" / "App.tsx"
SMOKE = ROOT / "scripts" / "smoke.sh"
VITE_CONFIG = ROOT / "vite.config.ts"
