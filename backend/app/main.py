from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth as auth_routes
from app.api.routes import billing as billing_routes
from app.api.routes import credits as credits_routes
from app.api.routes import institutions as institution_routes
from app.api.routes import interviews as interview_routes
from app.api.routes import job_matches as job_match_routes
from app.api.routes import career_readiness as career_readiness_routes
from app.api.routes import company_prep as company_prep_routes
from app.api.routes import github_analysis as github_analysis_routes
from app.api.routes import job_applications as job_application_routes
from app.api.routes import preparation_plans as preparation_plan_routes
from app.api.routes import resume_builder as resume_builder_routes
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
    allow_origins=settings.cors_origins,
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

app.include_router(
    resume_builder_routes.router,
    prefix="/api/v1/resume-builder",
    tags=["resume-builder"],
)

app.include_router(
    interview_routes.router,
    prefix="/api/v1/interviews",
    tags=["interviews"],
)

app.include_router(
    job_match_routes.router,
    prefix="/api/v1/job-matches",
    tags=["job-matches"],
)

app.include_router(
    preparation_plan_routes.router,
    prefix="/api/v1/preparation-plans",
    tags=["preparation-plans"],
)

app.include_router(
    career_readiness_routes.router,
    prefix="/api/v1/career-readiness",
    tags=["career-readiness"],
)

app.include_router(
    company_prep_routes.router,
    prefix="/api/v1/company-prep",
    tags=["company-prep"],
)

app.include_router(
    github_analysis_routes.router,
    prefix="/api/v1/github",
    tags=["github"],
)

app.include_router(
    job_application_routes.router,
    prefix="/api/v1/applications",
    tags=["applications"],
)

app.include_router(
    billing_routes.router,
    prefix="/api/v1/billing",
    tags=["billing"],
)

app.include_router(
    credits_routes.router,
    prefix="/api/v1/credits",
    tags=["credits"],
)

app.include_router(
    institution_routes.router,
    prefix="/api/v1/institutions",
    tags=["institutions"],
)


@app.get("/")
async def root():
    return {"message": "InterviewGPT AI API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
