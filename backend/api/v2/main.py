from fastapi import APIRouter

from api.v2.endpoints.jobs import router as jobs_router

router = APIRouter()

router.include_router(jobs_router)
