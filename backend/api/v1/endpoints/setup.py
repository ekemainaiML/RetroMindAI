from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.limiter import limiter
from core.models import Workshop

router = APIRouter()


@router.get("/setup/demo-key")
@limiter.limit("10/minute")
async def get_demo_key(request: Request, db: Session = Depends(get_db)):
    demo = db.query(Workshop).filter(Workshop.name == "Demo Workshop").first()
    if not demo:
        return {"api_key": None, "message": "Demo workshop not seeded yet. Restart the API server."}

    return {
        "api_key": demo.demo_raw_key,
        "api_key_prefix": demo.api_key_prefix,
    }
