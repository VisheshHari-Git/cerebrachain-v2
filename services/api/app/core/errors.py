"""Structured application errors returned by the HTTP API."""

from __future__ import annotations


class ApiServiceError(Exception):
    """A safe, client-facing failure with a stable HTTP status and error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ConfigurationUnavailableError(ApiServiceError):
    """Required protected runtime configuration is missing or invalid."""

    def __init__(self, message: str = "MRI inference is not configured.") -> None:
        super().__init__(503, "mri_service_unavailable", message)


class MriInputError(ApiServiceError):
    """An uploaded MRI file set cannot safely be processed."""

    def __init__(self, message: str) -> None:
        super().__init__(422, "invalid_mri_input", message)


class MriJobNotFoundError(ApiServiceError):
    """A requested job identifier is unknown to configured result storage."""

    def __init__(self) -> None:
        super().__init__(404, "mri_job_not_found", "MRI segmentation job was not found.")


class MriResultUnavailableError(ApiServiceError):
    """A job does not yet have a downloadable segmentation result."""

    def __init__(self, message: str = "MRI segmentation result is not available.") -> None:
        super().__init__(409, "mri_result_unavailable", message)


class MriInferenceUnavailableError(ApiServiceError):
    """The verified model cannot safely run in the current environment."""

    def __init__(self, message: str) -> None:
        super().__init__(503, "mri_inference_unavailable", message)


class MriInferenceFailedError(ApiServiceError):
    """Inference started but did not complete successfully."""

    def __init__(self) -> None:
        super().__init__(500, "mri_inference_failed", "MRI segmentation did not complete.")
