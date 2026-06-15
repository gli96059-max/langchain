from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.chef import router as chef_router

app = FastAPI(
    title="AI 私厨助手",
    description="基于 LangChain + Qwen 的智能私厨助手",
    version="1.0.0",
)

# ── CORS (allow Vue dev server) ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
