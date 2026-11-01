"""Read-only, authenticated federation evidence dashboard."""

from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import require_hospital_admin
from app.services.authentication import Principal

router = APIRouter(prefix="/federation", tags=["Federation"])

PORTS = {
    "superlink": 18080,
    "fleet_api": 18082,
    "A": 18094,
    "B": 18095,
    "C": 18096,
    "D": 18097,
}

EXPERIMENTS = (
    (
        "fedavg_ab",
        "FedAvg Round 1 — A+B",
        "fedavg_round1_AB",
        "aggregation_metadata.json",
    ),
    (
        "fedavg_abc",
        "FedAvg Round 1 — A+B+C",
        "fedavg_round1_ABC",
        "aggregation_metadata.json",
    ),
    (
        "secure_abc",
        "Secure Aggregation Smoke Test — A+B+C",
        "secagg_quantized_round1_ABC",
        "security_metrics.json",
    ),
)


def read_json(path: Path) -> dict:
    """Only read fixed, small evidence documents."""
    try:
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size > 256_000
        ):
            return {}

        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def file_sha256(path: Path) -> str | None:
    """Compute SHA256 without loading a checkpoint into PyTorch."""
    try:
        if not path.is_file() or path.is_symlink():
            return None

        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(
                lambda: source.read(1024 * 1024), b""
            ):
                digest.update(chunk)

        return digest.hexdigest()
    except OSError:
        return None


def tcp_listening(port: int) -> bool:
    """Only test a fixed loopback endpoint; not FL participation."""
    try:
        with socket.create_connection(
            ("127.0.0.1", port), timeout=0.3
        ):
            return True
    except OSError:
        return False


def checkpoint_evidence(
    root: Path,
    experiment_dir: str,
    metadata: dict,
) -> dict:
    path = root / experiment_dir / "global_model.pth"
    computed = file_sha256(path)

    expected = (
        metadata.get("global_model_sha256")
        or metadata.get("global_model_sha")
    )

    if computed is None:
        integrity = "unavailable"
    elif isinstance(expected, str):
        integrity = (
            "matches_metadata"
            if computed.lower() == expected.lower().removeprefix("0x")
            else "mismatch"
        )
    else:
        integrity = "sha256_computed_only"

    return {
        "sha256": computed,
        "integrity": integrity,
        "size_bytes": (
            path.stat().st_size
            if computed is not None
            else None
        ),
    }


def experiment_summary(root: Path, definition: tuple) -> dict:
    identifier, title, folder, filename = definition
    metadata = read_json(root / folder / filename)

    participants = metadata.get("participants", [])
    if not isinstance(participants, list):
        participants = []

    return {
        "id": identifier,
        "title": title,
        "metadata_available": bool(metadata),
        "round": metadata.get("round"),
        "participants": [
            value
            for value in participants
            if value in ("A", "B", "C", "D")
        ],
        "total_samples": metadata.get("total_samples"),
        "aggregation": metadata.get("aggregation"),
        "changed_global_parameters": metadata.get(
            "changed_global_parameters"
        ),
        "global_update_l2_norm": metadata.get(
            "global_update_l2_norm"
        ),
        "secure_aggregation": metadata.get(
            "secure_aggregation", False
        ),
        "distributed_privacy_verified": metadata.get(
            "distributed_privacy_verified", False
        ),
        "zk_proof_generated": metadata.get(
            "zk_proof_generated", False
        ),
        "blockchain_committed": metadata.get(
            "blockchain_committed", False
        ),
        "clinical_validation": metadata.get(
            "clinical_validation", False
        ),
        "single_process_smoke_test": metadata.get(
            "single_process_smoke_test", False
        ),
        "secure_sum_mismatches": metadata.get(
            "secure_sum_mismatches"
        ),
        "checkpoint": checkpoint_evidence(
            root, folder, metadata
        ),
    }


@router.get("/summary")
def federation_summary(
    principal: Principal = Depends(require_hospital_admin),
) -> dict:
    """Global research evidence, never MRI files or private witnesses."""

    configured_path = os.environ.get(
        "CEREBRACHAIN_FEDERATION_EVIDENCE_DIR"
    )
    if not configured_path:
        raise HTTPException(
            status_code=503,
            detail="Federation evidence directory is not configured.",
        )

    root = Path(configured_path)
    if not root.is_dir() or root.is_symlink():
        raise HTTPException(
            status_code=503,
            detail="Federation evidence directory is unavailable.",
        )

    experiments = [
        experiment_summary(root, definition)
        for definition in EXPERIMENTS
    ]

    nodes = []
    for code in ("A", "B", "C", "D"):
        metadata = read_json(
            root / f"hospital_{code}" / "training_metadata.json"
        )

        node = {
            "hospital": code,
            "port": PORTS[code],
            "tcp_listening": tcp_listening(PORTS[code]),
            "local_training_evidence": bool(metadata),
            "participated_in_fedavg_abc": code in (
                experiments[1]["participants"]
            ),
        }

        # Individual training metrics are hospital-scoped.
        # Unknown slugs receive no local metrics.
        principal_slug = getattr(
            principal, "hospital_slug", None
        )
        if principal_slug == f"hospital-{code.lower()}":
            node["own_local_training"] = {
                "epochs": metadata.get("epochs"),
                "training_loss": metadata.get("training_loss"),
                "training_seconds": metadata.get(
                    "training_seconds"
                ),
                "patch_size": metadata.get("patch_size"),
                "federated_round_completed": metadata.get(
                    "federated_round_completed", False
                ),
                "purpose": metadata.get("purpose"),
            } if metadata else None

        nodes.append(node)

    round6 = read_json(
        root / "live_round6_single_chunk" / "round_manifest.json"
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_source": "legacy_local_read_only",
        "flower": {
            "superlink_tcp_listening": tcp_listening(
                PORTS["superlink"]
            ),
            "fleet_api_tcp_listening": tcp_listening(
                PORTS["fleet_api"]
            ),
            "nodes": nodes,
        },
        "experiments": experiments,
        "protocol_test": {
            "round_label": round6.get("round"),
            "purpose": round6.get("purpose"),
            "full_model_proven": round6.get(
                "fullModelProven", False
            ),
            "live_proof_submitted": round6.get(
                "liveProofSubmitted", False
            ),
            "blockchain_verification_completed": round6.get(
                "blockchainVerificationCompleted", False
            ),
        },
        "disclaimer": (
            "Research/prototype evidence only. TCP listening "
            "does not prove participation, successful training, "
            "aggregation, data privacy, or ZK verification."
        ),
    }
