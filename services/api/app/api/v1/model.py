"""Read-only model metadata endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_mri_service
from app.schemas.mri import ModelInfoResponse
from app.services.mri_segmentation import MriSegmentationService

router = APIRouter(prefix="/model", tags=["Model"])


@router.get("/info", response_model=ModelInfoResponse, summary="Inspect configured model metadata")
def model_info(service: MriSegmentationService = Depends(get_mri_service)) -> ModelInfoResponse:
    """Return architecture and observed checkpoint integrity without exposing its path."""

    return ModelInfoResponse.model_validate(service.model_info())
