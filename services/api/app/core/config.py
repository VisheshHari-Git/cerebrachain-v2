"""Typed environment configuration for the MRI API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _optional_path(name: str) -> Path | None:
    raw_value = os.getenv(name, "").strip()
    return Path(raw_value).expanduser() if raw_value else None


def _optional_value(name: str) -> str | None:
    """Read an optional environment value without supplying an insecure default."""

    value = os.getenv(name, "").strip()
    return value or None


def _positive_int(name: str, default: int, *, allow_zero: bool = False) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name} must be positive.")
    return value


def _unit_interval_float(name: str, default: float) -> float:
    """Read a floating-point value in the half-open [0, 1) interval."""

    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number from 0 (inclusive) to 1 (exclusive).") from exc
    if not 0 <= value < 1:
        raise ValueError(f"{name} must be from 0 (inclusive) to 1 (exclusive).")
    return value


@dataclass(frozen=True)
class Settings:
    """Runtime settings that never embed protected paths or secrets in source code."""

    model_checkpoint_path: Path | None
    model_sha256: str | None
    result_storage_dir: Path | None
    inference_device: str = "cpu"
    max_upload_bytes: int = 64 * 1024 * 1024
    cpu_threads: int = 0
    sliding_window_overlap: float = 0.5
    database_url: str | None = None
    jwt_secret: str | None = None
    jwt_issuer: str = "zkp-cerebrachain-v2"
    access_token_ttl_seconds: int = 900

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings from environment variables without reading secret values."""

        return cls(
            model_checkpoint_path=_optional_path("CEREBRACHAIN_MODEL_CHECKPOINT"),
            model_sha256=os.getenv("CEREBRACHAIN_MODEL_SHA256", "").strip() or None,
            result_storage_dir=_optional_path("CEREBRACHAIN_RESULT_STORAGE_DIR"),
            inference_device=os.getenv("CEREBRACHAIN_INFERENCE_DEVICE", "cpu").strip().lower(),
            max_upload_bytes=_positive_int(
                "CEREBRACHAIN_MAX_UPLOAD_BYTES",
                64 * 1024 * 1024,
            ),
            cpu_threads=_positive_int(
                "CEREBRACHAIN_CPU_THREADS",
                0,
                allow_zero=True,
            ),
            sliding_window_overlap=_unit_interval_float(
                "CEREBRACHAIN_SLIDING_WINDOW_OVERLAP",
                0.5,
            ),
            database_url=_optional_value("CEREBRACHAIN_DATABASE_URL"),
            jwt_secret=_optional_value("CEREBRACHAIN_JWT_SECRET"),
            jwt_issuer=os.getenv(
                "CEREBRACHAIN_JWT_ISSUER", "zkp-cerebrachain-v2"
            ).strip(),
            access_token_ttl_seconds=_positive_int(
                "CEREBRACHAIN_ACCESS_TOKEN_TTL_SECONDS",
                900,
            ),
        )

    @property
    def model_is_configured(self) -> bool:
        """Return whether both model path and integrity hash are configured."""

        return self.model_checkpoint_path is not None and self.model_sha256 is not None

    @property
    def result_storage_is_configured(self) -> bool:
        """Return whether a protected result-storage root is configured."""

        return self.result_storage_dir is not None

    @property
    def database_is_configured(self) -> bool:
        """Return whether a database connection URL was provided."""

        return self.database_url is not None

    @property
    def authentication_is_configured(self) -> bool:
        """Return whether database and a non-default JWT signing secret are available."""

        return (
            self.database_is_configured
            and self.jwt_secret is not None
            and len(self.jwt_secret) >= 32
            and bool(self.jwt_issuer)
        )
