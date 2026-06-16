from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.chef import router as chef_router

app = FastAPI(
    title="AI 私厨助手",
    description="基于 LangChain + Qwen 的智能私厨助手",
    version="1.0.0",
)

# ── CORS (allow Vue dev server) ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files for uploaded images ───────────────────────────────
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ── API routes ─────────────────────────────────────────────────────
app.include_router(chef_router)

# ── Serve built frontend (SPA fallback) ────────────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        # Let API and upload requests pass through
        if request.url.path.startswith(("/api/", "/uploads/")):
            return await call_next(request)

        # Try to serve a static frontend file
        relative = request.url.path.lstrip("/") or "index.html"
        file_path = FRONTEND_DIST / relative
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # Pass to router; if 404, serve SPA index.html
        response = await call_next(request)
        if response.status_code == 404:
            return FileResponse(str(FRONTEND_DIST / "index.html"))
        return response
