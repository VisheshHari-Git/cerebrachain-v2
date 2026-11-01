"""Route composition for version 1 public endpoints."""

from fastapi import APIRouter

from app.api.v1 import model, mri

router = APIRouter(prefix="/api/v1")
router.include_router(model.router)
router.include_router(mri.router)
