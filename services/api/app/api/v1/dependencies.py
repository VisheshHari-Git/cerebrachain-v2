"""FastAPI dependencies for application services."""

from __future__ import annotations

from fastapi import Request

from app.services.mri_segmentation import MriSegmentationService


def get_mri_service(request: Request) -> MriSegmentationService:
    """Return the application-scoped serialized MRI service."""

    return request.app.state.mri_service
