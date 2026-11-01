# Architecture

## Purpose and current boundary

ZKP-CerebraChain V2 is a modular monorepo for a research-only, hospital-scoped neuroimaging workflow. Phase 1 establishes the boundaries only. It contains no runtime dependencies, production code, migrations, services, copied model weights, proof artifacts, or medical data.

V2 should remain a practical modular monolith: one web application, one API application, and narrowly scoped packages for ML, federated learning, and trust-layer integrations. It should not become a set of independently deployed microservices unless operational evidence requires that change.

## Target system

    Browser
      |
      | HTTPS, typed API client
      v
    React web application
      |
      | /api/v1
      v
    FastAPI application
      |-- authentication and authorization
      |-- hospital tenancy and audit events
      |-- study, upload, report, and dashboard services
      |-- model-inference orchestration
      |-- federation-monitoring read model
      |-- trust-layer orchestration
      |
      +--> PostgreSQL               metadata, identities, audits, workflow state
      +--> protected object store   MRI inputs, derived masks, report assets
      +--> ML adapter               external checkpoint and MONAI inference
      +--> Flower adapter           optional hospital-local training integration
      +--> trust adapter            proof verification, chain client, CID tracking

The browser never accesses MRI storage, model weights, private model updates, secrets, wallets, proof witnesses, or database credentials directly.

## Repository ownership

| Path | Responsibility |
| --- | --- |
| apps/web | Vite/React user interface, routes, feature presentation, API client, design tokens |
| services/api | FastAPI routes, dependency injection, application services, persistence, migrations, tests |
| packages/ml-adapter | Model configuration validation, artifact hashing, preprocessing, inference, postprocessing |
| packages/federation-adapter | Flower client/server integration contracts and round-metadata readers |
| packages/trust-adapter | Groth16 verification orchestration, contract client, content-addressed artifact references |
| packages/contracts | Reviewed Solidity and deployment source, isolated from web/API code |
| packages/shared-types | API/domain schemas shared across generated clients, never a source of database authority |
| infra | Future local orchestration and observability configuration |
| docs | Architecture decisions, inventory, APIs, roadmap, and operational guidance |

## Frontend design

The web application will use React, TypeScript, Vite, Tailwind CSS, Framer Motion, React Three Fiber, Three.js, and Recharts where feature needs justify them.

Page composition belongs in apps/web/src/app. Reusable layout and accessible primitives belong in components. Feature state and UI-specific domain logic belong in features. HTTP calls and response mapping belong in services. Shared browser utilities, styles, and TypeScript types remain separate. App startup should only compose providers and routes.

Google Stitch designs are an input to the design system, not a source-file format. When available, the design will be broken into pages, reusable components, accessible forms, tokens, and feature modules.

## Backend design

The API will expose versioned routes under /api/v1. Route handlers validate requests, resolve an authenticated actor and hospital scope, delegate to application services, and return Pydantic response schemas. They must not contain ORM queries, inference implementation, password hashing details, proof generation, or chain calls.

The main layers are:

1. core — configuration, error mapping, logging, security primitives, and dependency injection.
2. db — SQLAlchemy engine/session lifecycle and Alembic integration.
3. models — persistence entities and constraints.
4. repositories — hospital-scoped data access.
5. schemas — Pydantic request, response, and internal transfer schemas.
6. services — transactional business operations and audit events.
7. modules — cohesive domains: auth, hospitals, imaging, analysis, federation, and trust.
8. api/v1 — routers that assemble dependencies and service calls.

PostgreSQL is the system of record for identities, hospital membership, authorization grants, metadata, workflow state, audit events, model registrations, federated-round summaries, and trust-layer references. It must not store bulk MRI volumes or trained model weights.

## Identity, roles, and hospital isolation

The initial authorization model should distinguish at least platform administrator, hospital administrator, doctor, and hospital service account roles. A user can have one or more hospital memberships only when explicitly granted.

Every hospital-owned record must carry a hospital_id. The active hospital is derived from the authenticated membership and request context, then enforced by repository predicates and foreign-key relationships. An identifier supplied in a URL or body can select only an object already authorized within that active hospital. Administrative cross-hospital reads require an explicit role and an audit event.

Phase 2 will choose the concrete token/session mechanism. It must use short-lived credentials, secure password hashing, refresh/revocation rules, rate limiting for authentication, and no hard-coded demo secrets.

## MRI inference boundary

The ML adapter will receive a validated study record and protected artifact references, not an HTTP UploadFile or an arbitrary file path. It will:

1. require all four expected modalities in the verified order;
2. validate NIfTI decoding, dimensions, alignment, affine compatibility, size, and finite values;
3. require a configured checkpoint location and expected SHA-256 hash;
4. strictly load the known MONAI architecture;
5. execute the documented preprocessing and sliding-window inference;
6. restore the documented BraTS label convention;
7. persist derived artifacts only to protected storage and return metadata;
8. record the model artifact hash, inference configuration, and result status for auditability.

The API service will own authorization, job status, error translation, and audit records. The adapter will own the deterministic technical pipeline. The client will only request and visualize authorized result artifacts.

## Federated-learning boundary

Flower is an optional hospital-side integration, not a prerequisite for basic hospital workflows. A future federation module must separate:

- immutable model registration and artifact hashes;
- hospital client registration and capability status;
- round definition and eligibility;
- signed client metadata;
- aggregation output and measured validation data;
- monitoring read models.

No dashboard should infer a completed round from an uploaded file alone. The system must surface the actual status, participants, model hashes, sample counts, aggregation configuration, verification state, and any missing evidence.

## Trust-layer boundary

The trust adapter must be explicit about what it can verify:

- the legacy update_chunk circuit is designed around a quantized update chunk, an 8-bit range check, a squared-norm contribution, a context binding, a Poseidon commitment, and a polynomial evaluation;
- this does not prove clinical validity, correct model training, data provenance, or that a hospital used a particular MRI dataset;
- a proof-anchor record only stores integrity commitments for an externally verified proof set; it is not proof verification by itself.

All proof generation material, witnesses, private update chunks, provider tokens, and wallets remain outside the repository. Any deployment client must require environment-provided credentials and explicit chain/network configuration. The V2 trust adapter will return observed verification state rather than fabricate a success state.

## Artifact storage and provenance

MRI inputs, segmentation masks, model checkpoints, proof artifacts, and local IPFS payloads belong in protected external storage. PostgreSQL stores opaque storage references, content hashes, MIME types, ownership, purpose, retention information, and audit events. A CID is an integrity locator, not proof that its content is clinically valid, private, available, or authorized for a requester.

## Observability and failure handling

Future services will emit structured logs and correlation IDs without raw MRI, patient identifiers, credentials, private updates, proof witnesses, or other secrets. API failures will use a stable error envelope and machine-readable codes. Long-running inference, federation, and trust operations will expose explicit queued, running, succeeded, failed, and unavailable states.

## Integration decisions recorded in Phase 1

- The verified legacy source checkpoint is compatible with the documented MONAI 3D U-Net architecture, but V2 will not copy it into Git.
- The legacy three-hospital FedAvg artifact is a prototype and is not independently validated, ZK-proven, blockchain-committed, or clinically validated.
- Legacy FastAPI routes, Flower modules, circuit, contracts, and IPFS helper contain promising source material, but each will be ported through the V2 boundaries after a dedicated review.
- The legacy chain wrapper includes a development key fallback. V2 must not reuse that behavior.
