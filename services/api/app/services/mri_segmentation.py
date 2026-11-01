"""MRI segmentation orchestration separated from FastAPI route handling."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import torch
from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import (
    ConfigurationUnavailableError,
    MriInferenceFailedError,
    MriInferenceUnavailableError,
    MriInputError,
    MriJobNotFoundError,
    MriResultUnavailableError,
)
from app.models.mri import MriJob, MriJobStatus
from app.repositories.mri_jobs import (
    FileSystemMriJobRepository,
    MriJobRepositoryError,
    MriUploadError,
)
from cerebrachain_ml.architecture import (
    MODEL_ARCHITECTURE,
    MODEL_PARAMETER_COUNT,
    MODALITY_ORDER,
)
from cerebrachain_ml.artifacts import save_segmentation_mask
from cerebrachain_ml.checkpoint import LoadedModel, load_verified_model, verify_checkpoint
from cerebrachain_ml.errors import (
    CheckpointIntegrityError,
    InferenceError,
    ModelLoadError,
    MriValidationError,
)
from cerebrachain_ml.inference import run_segmentation
from cerebrachain_ml.preprocessing import preprocess_mri
from cerebrachain_ml.statistics import calculate_tumor_statistics

logger = logging.getLogger("cerebrachain.mri")


class MriSegmentationService:
    """Serialize CPU inference jobs and persist their non-identifying metadata."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = (
            FileSystemMriJobRepository(settings.result_storage_dir)
            if settings.result_storage_dir is not None
            else None
        )
        self._model_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._loaded_model: LoadedModel | None = None

        if settings.cpu_threads > 0:
            torch.set_num_threads(settings.cpu_threads)

    def health_status(self) -> dict[str, bool | str]:
        """Return process liveness and safe configuration readiness."""

        return {
            "status": (
                "ok"
                if self._settings.model_is_configured
                and self._settings.result_storage_is_configured
                else "degraded"
            ),
            "service": "zkp-cerebrachain-mri-api",
            "model_configured": self._settings.model_is_configured,
            "result_storage_configured": self._settings.result_storage_is_configured,
        }

    def model_info(self) -> dict[str, object]:
        """Return architecture and checkpoint integrity without loading weights."""

        response: dict[str, object] = {
            "model_name": "MONAI 3D U-Net",
            "modality_order": list(MODALITY_ORDER),
            "architecture": MODEL_ARCHITECTURE,
            "expected_parameter_count": MODEL_PARAMETER_COUNT,
            "configured": self._settings.model_is_configured,
            "integrity_status": "not_configured",
            "checkpoint": None,
            "model_loaded": self._loaded_model is not None,
        }
        if not self._settings.model_is_configured:
            return response

        assert self._settings.model_checkpoint_path is not None
        assert self._settings.model_sha256 is not None
        try:
            checkpoint = verify_checkpoint(
                self._settings.model_checkpoint_path,
                self._settings.model_sha256,
            )
        except CheckpointIntegrityError:
            response["integrity_status"] = "failed"
            return response

        response["integrity_status"] = "verified"
        response["checkpoint"] = {
            "sha256": checkpoint.sha256,
            "size_bytes": checkpoint.size_bytes,
        }
        return response

    def submit(self, uploads: Mapping[str, UploadFile], *, job_id: str | None = None) -> MriJob:
        """Store uploads, run one real inference job, and persist the derived mask."""

        repository = self._require_repository()
        self._require_model_configuration()
        self._validate_uploads(uploads)
        job = MriJob.create(job_id)

        try:
            repository.create(job)
            for modality in MODALITY_ORDER:
                upload = uploads[modality]
                repository.save_upload(
                    job.job_id,
                    modality,
                    upload.file,
                    max_bytes=self._settings.max_upload_bytes,
                )

            job.status = MriJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job.touch()
            repository.update(job)

            with self._inference_lock:
                loaded_model = self._get_loaded_model()
                prepared_mri = preprocess_mri(repository.modality_paths(job.job_id))
                prediction = run_segmentation(
                    loaded_model.model,
                    prepared_mri,
                    device=self._settings.inference_device,
                    overlap=self._settings.sliding_window_overlap,
                )
                statistics = calculate_tumor_statistics(
                    prediction.mask,
                    prepared_mri.reference.header,
                )
                save_segmentation_mask(
                    prediction.mask,
                    prepared_mri.reference,
                    repository.segmentation_path(job.job_id),
                )

            job.status = MriJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.model_sha256 = loaded_model.checkpoint.sha256
            job.input_shape = tuple(int(value) for value in prepared_mri.input_tensor.shape)
            job.segmentation_shape = tuple(int(value) for value in prediction.mask.shape)
            job.labels = prediction.labels
            job.statistics = statistics
            job.inference_seconds = prediction.duration_seconds
            job.touch()
            repository.update(job)
            logger.info(
                "mri_job_completed",
                extra={"job_id": job.job_id, "status": job.status.value},
            )
            return job
        except MriUploadError as exc:
            self._mark_failed(job, "upload_failed", "MRI upload could not be accepted.")
            raise MriInputError(str(exc)) from exc
        except MriValidationError as exc:
            self._mark_failed(job, "mri_validation_failed", "MRI validation failed.")
            raise MriInputError(str(exc)) from exc
        except CheckpointIntegrityError as exc:
            self._mark_failed(job, "checkpoint_integrity_failed", "Model integrity verification failed.")
            raise MriInferenceUnavailableError("Verified model checkpoint is unavailable.") from exc
        except ModelLoadError as exc:
            self._mark_failed(job, "model_load_failed", "Model checkpoint could not be loaded.")
            raise MriInferenceUnavailableError("Verified model checkpoint could not be loaded.") from exc
        except InferenceError as exc:
            self._mark_failed(job, "inference_failed", "MRI inference failed.")
            raise MriInferenceFailedError() from exc
        except MriJobRepositoryError as exc:
            self._mark_failed(job, "storage_failed", "Result storage failed.")
            raise MriInferenceFailedError() from exc
        except Exception as exc:
            self._mark_failed(job, "unexpected_failure", "MRI inference failed.")
            logger.exception("mri_job_failed", extra={"job_id": job.job_id, "status": "failed"})
            raise MriInferenceFailedError() from exc

    def get_job(self, job_id: str) -> MriJob:
        """Retrieve safe metadata for one persisted MRI job."""

        try:
            return self._require_repository().get(job_id)
        except MriJobRepositoryError as exc:
            raise MriJobNotFoundError() from exc

    def get_completed_result(self, job_id: str) -> MriJob:
        """Retrieve a completed job only when its derived NIfTI artifact exists."""

        job = self.get_job(job_id)
        if job.status is not MriJobStatus.COMPLETED:
            raise MriResultUnavailableError("MRI segmentation job has not completed.")
        if not self._require_repository().segmentation_path(job_id).is_file():
            raise MriResultUnavailableError()
        return job

    def result_artifact_path(self, job_id: str) -> Path:
        """Return an authorized completed result artifact path for response streaming."""

        self.get_completed_result(job_id)
        return self._require_repository().segmentation_path(job_id)

    def _get_loaded_model(self) -> LoadedModel:
        if self._loaded_model is not None:
            return self._loaded_model

        with self._model_lock:
            if self._loaded_model is None:
                assert self._settings.model_checkpoint_path is not None
                assert self._settings.model_sha256 is not None
                self._loaded_model = load_verified_model(
                    self._settings.model_checkpoint_path,
                    self._settings.model_sha256,
                    device=self._settings.inference_device,
                )
            return self._loaded_model

    def _require_model_configuration(self) -> None:
        if not self._settings.model_is_configured:
            raise ConfigurationUnavailableError("MRI model checkpoint configuration is missing.")
        if self._settings.inference_device != "cpu":
            raise ConfigurationUnavailableError("Only CPU inference is supported by this Phase 2 service.")

    def _require_repository(self) -> FileSystemMriJobRepository:
        if self._repository is None:
            raise ConfigurationUnavailableError("MRI result storage configuration is missing.")
        return self._repository

    @staticmethod
    def _validate_uploads(uploads: Mapping[str, UploadFile]) -> None:
        if set(uploads) != set(MODALITY_ORDER):
            raise MriInputError("Exactly FLAIR, T1, T1CE, and T2 MRI files are required.")
        for modality in MODALITY_ORDER:
            filename = uploads[modality].filename or ""
            if not filename.lower().endswith(".nii.gz"):
                raise MriInputError(f"{modality.upper()} must be a .nii.gz MRI file.")

    def _mark_failed(self, job: MriJob, code: str, message: str) -> None:
        """Persist a safe failure state without masking the original service error."""

        if self._repository is None:
            return
        try:
            job.status = MriJobStatus.FAILED
            job.error_code = code
            job.error_message = message
            job.completed_at = datetime.now(timezone.utc)
            job.touch()
            self._repository.update(job)
            logger.info("mri_job_failed", extra={"job_id": job.job_id, "status": job.status.value})
        except MriJobRepositoryError:
            logger.exception("mri_failure_state_not_persisted", extra={"job_id": job.job_id})
