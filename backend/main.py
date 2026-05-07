"""
FastAPI application entry-point.
Registers all routers — organised by user role — and initialises the DB on startup.

Architecture:
    backend/
    ├── employee/routes.py   → /api/employee/*   (Employee-facing)
    ├── hr/routes.py         → /api/hr/*         (HR-facing)
    ├── it_admin/routes.py   → /api/it/*         (IT Admin-facing)
    ├── routes_chat.py       → /api/chat/*       (Shared — agent)
    └── routes_ml.py         → /api/ml/*         (Shared — predictions)

Run with:
    cd "agentic chatbot"
    .venv\\Scripts\\uvicorn backend.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import APP_TITLE, APP_VERSION
from backend.database import init_db

# ── User-role routers ────────────────────────────────
from backend.employee.routes import router as employee_router
from backend.hr.routes import router as hr_router
from backend.it_admin.routes import router as it_admin_router

# ── Shared routers ───────────────────────────────────
from backend.routes_chat import router as chat_router
from backend.routes_ml import router as ml_router

# ── Legacy routers (kept for backward compat, can be removed later) ──
from backend.routes_employees import router as employees_router
from backend.routes_leaves import router as leaves_router
from backend.routes_meetings import router as meetings_router

# ── Create app ───────────────────────────────────────
app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# ── CORS (allow React frontend) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register role-based routers ──────────────────────
app.include_router(employee_router)
app.include_router(hr_router)
app.include_router(it_admin_router)

# ── Register shared routers ─────────────────────────
app.include_router(chat_router)
app.include_router(ml_router)

# ── Register legacy routers ─────────────────────────
app.include_router(employees_router)
app.include_router(leaves_router)
app.include_router(meetings_router)


# ── Startup event ───────────────────────────────────
@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION}
