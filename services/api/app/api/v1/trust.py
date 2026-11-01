"""Authenticated, read-only blockchain and ZKP evidence audit."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import require_hospital_admin
from app.services.authentication import Principal

router = APIRouter(prefix="/trust", tags=["Blockchain Trust"])

RPC_URL = "http://127.0.0.1:8545"


def read_evidence(path: Path) -> dict[str, Any]:
    """Read a fixed evidence document without exposing its full content."""
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > 5_000_000
        ):
            return {}

        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def rpc(method: str, params: list[Any]) -> Any:
    """Execute only explicitly selected read-only Ethereum RPC calls."""
    allowed = {
        "eth_chainId",
        "eth_blockNumber",
        "eth_getBlockByNumber",
        "eth_getCode",
        "eth_getTransactionReceipt",
        "eth_getTransactionByHash",
    }

    if method not in allowed:
        raise ValueError("RPC method is not permitted.")

    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }).encode("utf-8")

    request = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=3) as response:
        result = json.load(response)

    if "error" in result:
        raise RuntimeError("Blockchain RPC returned an error.")

    return result.get("result")


def matches(first: Any, second: Any) -> bool:
    return (
        isinstance(first, str)
        and isinstance(second, str)
        and first.lower() == second.lower()
    )


def receipt_success(receipt: Any) -> bool:
    return (
        isinstance(receipt, dict)
        and receipt.get("status") == "0x1"
    )


@router.get("/summary")
def trust_summary(
    principal: Principal = Depends(require_hospital_admin),
) -> dict[str, Any]:
    """Reconcile historical evidence with the current local blockchain."""

    configured = os.environ.get(
        "CEREBRACHAIN_FEDERATION_EVIDENCE_DIR"
    )

    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Trust evidence is not configured.",
        )

    root = Path(configured)

    if root.is_symlink() or not root.is_dir():
        raise HTTPException(
            status_code=503,
            detail="Trust evidence directory is unavailable.",
        )

    anchor_dir = root / "zk_full_anchor_stage_v1"

    deployment = read_evidence(
        anchor_dir / "deployment_local31337_current_v3.json"
    )
    anchoring = read_evidence(
        anchor_dir / "anchoring_local31337_current_v3.json"
    )
    proofset = read_evidence(
        anchor_dir / "proofset_merkle_v1.json"
    )
    proof_jobs = read_evidence(
        root / "zk_full_proofs_stage_v1" / "manifest.json"
    )

    if not all((deployment, anchoring, proofset, proof_jobs)):
        raise HTTPException(
            status_code=503,
            detail="Required historical trust evidence is unavailable.",
        )

    address = deployment.get("contractAddress")
    deploy_hash = deployment.get("deploymentTransactionHash")
    anchor_hash = anchoring.get("transactionHash")

    evidence_addresses_valid = (
        isinstance(address, str)
        and address.startswith("0x")
        and len(address) == 42
        and isinstance(deploy_hash, str)
        and deploy_hash.startswith("0x")
        and len(deploy_hash) == 66
        and isinstance(anchor_hash, str)
        and anchor_hash.startswith("0x")
        and len(anchor_hash) == 66
    )

    historical_root_matches = matches(
        proofset.get("proofMerkleRoot"),
        anchoring.get("proofMerkleRoot"),
    )

    result: dict[str, Any] = {
        "network": {
            "rpc_available": False,
            "chain_id": None,
            "latest_block": None,
            "genesis_matches": False,
        },
        "contract": {
            "name": deployment.get("contractName"),
            "address": address,
            "runtime_hash_matches": False,
            "code_present": False,
        },
        "transactions": {
            "deployment_hash": deploy_hash,
            "deployment_confirmed": False,
            "anchoring_hash": anchor_hash,
            "anchoring_confirmed": False,
        },
        "proof_evidence": {
            "recorded_jobs": proof_jobs.get("totalJobs"),
            "proofset_total": proofset.get("totalProofs"),
            "hospital_count": proofset.get("hospitalCount"),
            "merkle_root_matches_historical_record":
                historical_root_matches,
            "merkle_root": proofset.get("proofMerkleRoot"),
            "historical_blockchain_anchored_flag":
                proofset.get("blockchainAnchored", False),
            "onchain_proof_verification_count":
                proofset.get("onchainProofVerificationCount", 0),
            "proofs_reverified_during_anchoring":
                anchoring.get("proofsReverifiedOnThisStep", 0),
            "verification_scope":
                anchoring.get("verificationScope"),
        },
        "verification": {
            "current_anchor_transaction_confirmed": False,
            "individual_groth16_proofs_verified_live": False,
        },
        "disclaimer": (
            "A confirmed anchoring transaction is not individual "
            "Groth16 proof verification. Historical flags and current "
            "chain state are reported separately. Research use only."
        ),
    }

    if not evidence_addresses_valid:
        return result

    try:
        chain_id = int(rpc("eth_chainId", []), 16)
        latest_block = int(rpc("eth_blockNumber", []), 16)
        genesis = rpc("eth_getBlockByNumber", ["0x0", False])

        genesis_hash = (
            genesis.get("hash")
            if isinstance(genesis, dict)
            else None
        )

        genesis_matches = (
            matches(genesis_hash, deployment.get("genesisHash"))
            and matches(genesis_hash, anchoring.get("genesisHash"))
        )

        chain_matches = (
            chain_id == 31337
            and genesis_matches
        )

        result["network"].update({
            "rpc_available": True,
            "chain_id": chain_id,
            "latest_block": latest_block,
            "genesis_matches": genesis_matches,
        })

        # Do not interpret an arbitrary chain with the same chain ID
        # as the deployment evidenced by the historical records.
        if not chain_matches:
            return result

        code = rpc("eth_getCode", [address, "latest"])

        code_present = (
            isinstance(code, str)
            and code.startswith("0x")
            and code != "0x"
        )

        runtime_matches = False

        if code_present:
            runtime_hash = hashlib.sha256(
                bytes.fromhex(code[2:])
            ).hexdigest()

            runtime_matches = matches(
                runtime_hash,
                deployment.get("runtimeCodeSha256"),
            )

        result["contract"].update({
            "code_present": code_present,
            "runtime_hash_matches": runtime_matches,
        })

        deployment_receipt = rpc(
            "eth_getTransactionReceipt",
            [deploy_hash],
        )

        anchor_receipt = rpc(
            "eth_getTransactionReceipt",
            [anchor_hash],
        )

        anchor_transaction = rpc(
            "eth_getTransactionByHash",
            [anchor_hash],
        )

        deployment_confirmed = (
            receipt_success(deployment_receipt)
            and matches(
                deployment_receipt.get("contractAddress"),
                address,
            )
            and int(
                deployment_receipt.get("blockNumber", "0x0"), 16
            ) == deployment.get("deploymentBlock")
        )

        anchoring_confirmed = (
            receipt_success(anchor_receipt)
            and isinstance(anchor_transaction, dict)
            and matches(anchor_transaction.get("to"), address)
            and matches(anchoring.get("contractAddress"), address)
            and int(
                anchor_receipt.get("blockNumber", "0x0"), 16
            ) == anchoring.get("anchoringBlock")
        )

        result["transactions"].update({
            "deployment_confirmed": deployment_confirmed,
            "anchoring_confirmed": anchoring_confirmed,
        })

        result["verification"][
            "current_anchor_transaction_confirmed"
        ] = (
            runtime_matches
            and deployment_confirmed
            and anchoring_confirmed
            and historical_root_matches
        )

    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        urllib.error.URLError,
    ):
        # Historical records remain visible, but no live success is
        # claimed if RPC verification fails.
        pass

    return result
