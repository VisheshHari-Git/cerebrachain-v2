"""MRI upload, job-status, and derived-segmentation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies import (
    get_current_principal,
    get_database_session,
    get_mri_service,
)
from app.core.errors import ApiServiceError
from app.schemas.mri import (
    MriJobResponse,
    MriSegmentationResultResponse,
    TumorStatisticsResponse,
    serialize_job,
)
from app.services.mri_segmentation import MriSegmentationService
from app.services.authentication import Principal
from app.services.mri_ownership import MriOwnershipService

router = APIRouter(prefix="/mri", tags=["MRI Segmentation"])


def get_mri_ownership_service(
    session: Session = Depends(get_database_session),
) -> MriOwnershipService:
    """Construct the database ownership service for one authenticated request."""

    return MriOwnershipService(session)


@router.post(
    "/segment",
    response_model=MriJobResponse,
    status_code=201,
    summary="Upload four MRI modalities and run real 3D segmentation",
)
def segment_mri(
    flair: UploadFile = File(..., description="FLAIR MRI in .nii.gz format."),
    t1: UploadFile = File(..., description="T1 MRI in .nii.gz format."),
    t1ce: UploadFile = File(..., description="T1CE MRI in .nii.gz format."),
    t2: UploadFile = File(..., description="T2 MRI in .nii.gz format."),
    service: MriSegmentationService = Depends(get_mri_service),
    principal: Principal = Depends(get_current_principal),
    ownership_service: MriOwnershipService = Depends(get_mri_ownership_service),
) -> MriJobResponse:
    """Serialize one CPU job and return its persisted lifecycle state."""

    record = ownership_service.reserve(principal)
    ownership_service.mark_running(record)
    try:
        job = service.submit(
            {"flair": flair, "t1": t1, "t1ce": t1ce, "t2": t2},
            job_id=str(record.id),
        )
    except ApiServiceError:
        ownership_service.mark_failed(record)
        raise
    ownership_service.mark_completed(record, model_sha256=job.model_sha256)
    return serialize_job(job)


@router.get(
    "/jobs/{job_id}",
    response_model=MriJobResponse,
    summary="Read non-identifying MRI job status",
)
def get_mri_job(
    job_id: str,
    service: MriSegmentationService = Depends(get_mri_service),
    principal: Principal = Depends(get_current_principal),
    ownership_service: MriOwnershipService = Depends(get_mri_ownership_service),
) -> MriJobResponse:
    """Return persisted state for a specific segmentation job."""

    ownership_service.require_owned(job_id, principal)
    return serialize_job(service.get_job(job_id))


@router.get(
    "/jobs/{job_id}/result",
    response_model=MriSegmentationResultResponse,
    summary="Read result metadata or download derived segmentation NIfTI",
)
def get_mri_result(
    job_id: str,
    download: bool = Query(
        default=False,
        description="When true, stream the derived NIfTI segmentation artifact.",
    ),
    service: MriSegmentationService = Depends(get_mri_service),
    principal: Principal = Depends(get_current_principal),
    ownership_service: MriOwnershipService = Depends(get_mri_ownership_service),
) -> MriSegmentationResultResponse | FileResponse:
    """Return viewer-ready result metadata or an explicitly requested NIfTI download."""

    ownership_service.require_owned(job_id, principal)
    if download:
        artifact = service.result_artifact_path(job_id)
        return FileResponse(
            artifact,
            media_type="application/gzip",
            filename=f"{job_id}-segmentation.nii.gz",
            headers={"Cache-Control": "private, no-store"},
        )

    job = service.get_completed_result(job_id)
    assert job.model_sha256 is not None
    assert job.input_shape is not None
    assert job.segmentation_shape is not None
    assert job.statistics is not None
    assert job.inference_seconds is not None
    return MriSegmentationResultResponse(
        job_id=job.job_id,
        status=job.status.value,
        model_sha256=job.model_sha256,
        input_shape=list(job.input_shape),
        segmentation_shape=list(job.segmentation_shape),
        labels=job.labels,
        statistics=TumorStatisticsResponse(
            tumor_voxels=job.statistics.tumor_voxels,
            label_voxels=job.statistics.label_voxels,
            voxel_volume_mm3=job.statistics.voxel_volume_mm3,
            tumor_volume_mm3=job.statistics.tumor_volume_mm3,
            tumor_volume_ml=job.statistics.tumor_volume_ml,
        ),
        inference_seconds=job.inference_seconds,
        artifact_download_url=f"/api/v1/mri/jobs/{job.job_id}/result?download=true",
    )
