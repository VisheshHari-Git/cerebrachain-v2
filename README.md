# ZKP-CerebraChain V2

ZKP-CerebraChain V2 is a research-oriented federated, zero-knowledge multi-modal MRI segmentation platform. It is being rebuilt as a maintainable full-stack system for hospital-scoped workflows, real MONAI 3D U-Net inference, federated model monitoring, and verifiable model-update provenance.

> Status: Phase 1 architecture preparation is complete. No frontend, API service, database, model inference endpoint, federated round, smart-contract deployment, or ZK proof flow is implemented in V2 yet.

## What V2 will support

- Hospital and doctor registration, authentication, and role-based access.
- Hospital-isolated dashboards and MRI study workflows.
- Upload, validation, segmentation, visualization, and research-only AI reports for four-modal brain MRI.
- Flower-based federated learning and FedAvg monitoring.
- Groth16 proof verification, blockchain anchoring, and content-addressed artifact tracking.

Clinical deployment is out of scope. Any future result must remain labelled research-only until the required clinical, security, privacy, and regulatory validation is complete.

## Phase 1 outcomes

- Inspected the legacy project in read-only mode and recorded reusable components in docs/ASSET_INVENTORY.md.
- Verified the externally stored, legacy-trained MONAI 3D U-Net checkpoint by SHA-256 and strict state-dictionary loading.
- Recorded its architecture, modality order, preprocessing, postprocessing, and existing research-only evaluation metadata.
- Created a dependency-free monorepo structure prepared for a Vite/React web app, FastAPI API, SQLAlchemy/PostgreSQL, Flower adapters, and trust-layer adapters.
- Added permanent engineering, security, architecture, and Git rules in AGENTS.md.

## Repository layout

    apps/
      web/                  Future React + TypeScript + Vite application
    services/
      api/                  Future FastAPI application and Alembic migrations
    packages/
      ml-adapter/           Validated model-loading and inference boundary
      federation-adapter/   Flower integration boundary
      trust-adapter/        ZK, chain, and artifact-tracking boundary
      contracts/            Reviewed contract source and deployment tooling
      shared-types/         Cross-boundary schemas and generated API types
    infra/
      compose/              Local development orchestration, added only when needed
      monitoring/           Observability configuration, added only when needed
    docs/                   Architecture, assets, API plan, and delivery roadmap

## Verified legacy checkpoint

The source model remains outside this repository and is intentionally ignored by Git. The configured V2 integration will require an explicit path and expected SHA-256 value instead of relying on the legacy relative-path fallback.

| Item | Recorded value |
| --- | --- |
| Artifact | model_final.pth |
| SHA-256 | fb633c102af016310b89c6cb42f7cf65f78a3e63575cfe1a6075d14cd69b973f |
| Architecture | MONAI 3D U-Net; 4 inputs, 4 outputs; channels 16, 32, 64, 128, 256 |
| Compatibility check | Strict load passed; 48 state tensors; 2,453,636 parameters |
| Modality order | flair, t1, t1ce, t2 |

See docs/ASSET_INVENTORY.md for the exact read-only source path, provenance caveats, legacy evaluation status, and reuse decisions.

## Documentation

- docs/ARCHITECTURE.md — system boundaries, data flow, tenancy, and integration rules.
- docs/ASSET_INVENTORY.md — legacy asset inventory and compatibility findings.
- docs/API_PLAN.md — proposed versioned API surface and error contract.
- docs/DEVELOPMENT_ROADMAP.md — phased delivery plan and quality gates.

## Current constraints

- Dependencies have not been installed.
- Services have not been started.
- No model was trained, copied, converted, or changed.
- No simulated predictions, federated rounds, proofs, transactions, or CIDs were created.
- All future runtime configuration must use environment variables and external protected storage.

## Next phase

Phase 2 should establish the Vite and FastAPI foundations, configuration, PostgreSQL/Alembic tenancy model, secure authentication boundaries, baseline tests, linting, and CI checks. It must not yet train a model or claim any new ML, Flower, ZK, or chain result.
