from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.cases import router as cases_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.statistics import router as statistics_router
from app.api.v1.onboarding import router as onboarding_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["认证授权"])
api_router.include_router(ingestion_router, prefix="/ingestion", tags=["数据接入"])
api_router.include_router(cases_router, prefix="/cases", tags=["案件管理"])
api_router.include_router(evidence_router, prefix="/evidence", tags=["证据管理"])
api_router.include_router(statistics_router, prefix="/statistics", tags=["统计分析"])
api_router.include_router(onboarding_router, prefix="/onboarding", tags=["新手引导"])
