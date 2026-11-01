"""Endpoint-level test that performs exactly one real CPU MRI inference.

Real HTTP coverage is executed separately against Uvicorn because the reused
legacy environment's in-process ASGI transport can block before dispatch.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

import nibabel as nib
from fastapi import UploadFile
from fastapi.responses import FileResponse

from app.api.v1.mri import get_mri_job, get_mri_result, segment_mri
from app.core.config import Settings
from app.services.mri_segmentation import MriSegmentationService


def test_real_mri_segmentation_endpoint_flow(
    configured_settings: Settings,
    external_mri_paths: dict[str, Path],
) -> None:
    """Exercise endpoint handlers, real inference, persistence, and result download."""

    service = MriSegmentationService(configured_settings)
    with ExitStack() as stack:
        uploads = {
            modality: UploadFile(
                filename=path.name,
                file=stack.enter_context(path.open("rb")),
                headers={"content-type": "application/gzip"},
            )
            for modality, path in external_mri_paths.items()
        }
        submitted = segment_mri(service=service, **uploads)

    assert submitted.status == "completed"
    job_status = get_mri_job(submitted.job_id, service=service)
    assert job_status.status == "completed"

    result = get_mri_result(submitted.job_id, service=service)
    assert result.status == "completed"
    assert result.input_shape[0:2] == [1, 4]
    assert result.segmentation_shape == result.input_shape[2:]
    assert result.statistics.tumor_voxels >= 0
    assert result.statistics.tumor_volume_ml >= 0
    assert result.artifact_download_url.endswith("?download=true")

    artifact_path = configured_settings.result_storage_dir / submitted.job_id / "segmentation.nii.gz"
    assert artifact_path.is_file()
    saved_mask = nib.load(str(artifact_path))
    assert tuple(saved_mask.shape) == tuple(result.segmentation_shape)

    download = get_mri_result(submitted.job_id, download=True, service=service)
    assert isinstance(download, FileResponse)
    assert download.media_type == "application/gzip"
