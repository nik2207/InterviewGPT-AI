from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth as auth_routes
from app.api.routes import resumes as resume_routes
from core.config.settings import settings
from core.database import close_mongo_connection, connect_to_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="InterviewGPT AI API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_routes.router,
    prefix="/api/v1/auth",
    tags=["auth"],
)

app.include_router(
    resume_routes.router,
    prefix="/api/v1/resumes",
    tags=["resumes"],
)


@app.get("/")
async def root():
    return {"message": "InterviewGPT AI API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
