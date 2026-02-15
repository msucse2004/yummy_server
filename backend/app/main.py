"""FastAPI 앱 진입점"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_config import configure_logging

configure_logging(os.getenv("LOG_LEVEL", "INFO"))
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, customers, items, plans, routes, stops, completions, users, uploads, reports, settings as settings_api
from app.config import get_settings

settings = get_settings()
os.makedirs(settings.upload_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Yummy Server",
    description="배송/물류 관리 시스템 - 24/7 로컬 공장용",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(items.router)
app.include_router(plans.router)
app.include_router(routes.router)
app.include_router(stops.router)
app.include_router(completions.router)
app.include_router(users.router)
app.include_router(uploads.router)
app.include_router(reports.router)
app.include_router(settings_api.router)

# 업로드 파일은 /api/uploads/photo/{id} 통해 인증 후 다운로드


@app.get("/health")
def health():
    return {"status": "ok"}
