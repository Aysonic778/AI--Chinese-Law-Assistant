from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.database import init_db
from backend.routers import chat, library


@asynccontextmanager
async def lifespan(_: FastAPI):
    for path in (
        Path(settings.chroma_persist_dir),
        Path(settings.upload_dir),
        Path("data"),
    ):
        path.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title="法律资料库可信问答 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(library.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
