# API Plan

## Conventions

All browser-facing API endpoints will be versioned below /api/v1 and use JSON unless explicitly handling a protected upload or download stream. Routes require an authenticated actor unless marked public. The API will derive the active hospital from membership and authorization context rather than trusting a hospital ID supplied by the client.

The proposed error envelope is:

    {
      "error": {
        "code": "study_not_found",
        "message": "The requested study is not available in the active hospital.",
        "request_id": "..."
      }
    }

Validation errors will retain field-level details. Error responses must not disclose whether inaccessible cross-hospital records exist.

## Authentication and identity

| Method and path | Purpose | Initial authorization |
| --- | --- | --- |
| POST /auth/hospitals/register | Begin hospital registration workflow | Public, rate limited; not an automatic approval |
| POST /auth/hospitals/login | Authenticate a hospital administrator or service account | Public, rate limited |
| POST /auth/doctors/register | Create a doctor account within an approved hospital | Hospital administrator |
| POST /auth/doctors/login | Authenticate a doctor | Public, rate limited |
| POST /auth/refresh | Rotate a valid refresh credential | Authenticated refresh context |
| POST /auth/logout | Revoke current session/refresh credential | Authenticated |
| GET /auth/me | Return actor, roles, and active hospital memberships | Authenticated |

The final mechanism will be selected in Phase 2. Passwords must be salted and securely hashed; issued credentials must be short-lived and revocable. Safe demo accounts, if later required, must use environment-provided non-production values.

## Hospital and dashboard

| Method and path | Purpose | Authorization |
| --- | --- | --- |
| GET /hospitals/me | Return active hospital profile and permitted capabilities | Hospital member |
| PATCH /hospitals/me | Update authorized hospital metadata | Hospital administrator |
| GET /dashboard/summary | Counts, workflow statuses, and model/round summaries for the active hospital | Hospital member |
| GET /dashboard/activity | Paginated hospital-scoped audit/activity feed | Hospital member |

## Studies, uploads, and artifacts

| Method and path | Purpose | Authorization |
| --- | --- | --- |
| POST /studies | Create a de-identified study record | Doctor or hospital administrator |
| GET /studies | List only active-hospital studies with pagination/filtering | Hospital member |
| GET /studies/{study_id} | Read one authorized study and workflow state | Hospital member |
| POST /studies/{study_id}/uploads | Initiate protected four-modality upload | Doctor or authorized service account |
| POST /studies/{study_id}/uploads/{upload_id}/complete | Validate uploaded artifact set and mark ready/rejected | Uploader or authorized service account |
| GET /studies/{study_id}/artifacts | List authorized input/derived artifact metadata, never storage secrets | Hospital member |
| GET /studies/{study_id}/preview | Return a guarded rendered slice/overlay representation | Hospital member |

The API will accept only an approved storage-upload flow, enforce size and content limits, validate all four modalities, reject unsafe paths, and log artifact metadata. Raw MRI is never embedded in JSON, application logs, Git, or browser state.

## Analysis and reports

| Method and path | Purpose | Authorization |
| --- | --- | --- |
| POST /studies/{study_id}/analyses | Request a research-only segmentation job | Doctor or authorized service account |
| GET /studies/{study_id}/analyses | List analysis jobs and statuses | Hospital member |
| GET /analyses/{analysis_id} | Read job state, model provenance, and result metadata | Hospital member |
| GET /analyses/{analysis_id}/report | Return authorized structured research report | Hospital member |
| GET /analyses/{analysis_id}/visualization | Return visualization manifest for authorized derived artifacts | Hospital member |

Analysis submission must fail closed if the configured checkpoint hash, modality requirements, storage access, or model compatibility checks fail. A result will include provenance and research-only language, not a diagnosis.

## Federated learning monitoring

| Method and path | Purpose | Authorization |
| --- | --- | --- |
| GET /federation/models | List registered global/local model metadata available to the hospital | Hospital member |
| GET /federation/rounds | List round summaries and observed status | Hospital member |
| GET /federation/rounds/{round_id} | Return a round's participants, hashes, metrics, and verification evidence | Hospital member |
| GET /federation/rounds/{round_id}/metrics | Return measured, explicitly labelled monitoring series | Hospital member |

These endpoints are read models first. A later write API must require an approved federation operator flow and record all inputs, outputs, and failures. The service must not derive performance or verification state from filenames or unverified client assertions.

## Trust-layer records

| Method and path | Purpose | Authorization |
| --- | --- | --- |
| GET /trust/proofs | List proof-record metadata visible to the active hospital | Hospital member |
| GET /trust/proofs/{proof_id} | Return verification status, circuit/version bindings, and non-sensitive receipt metadata | Hospital member |
| GET /trust/anchors | List recorded chain-anchor metadata | Hospital member |
| GET /trust/anchors/{anchor_id} | Return anchor, transaction, and CID reference metadata | Hospital member |

V2 will expose observed states such as unavailable, pending, verified, rejected, failed, or not_requested. It will not infer proof verification from a CID or an anchored integrity root. Private proof inputs and witness material are never API responses.

## Health and operations

| Method and path | Purpose | Authorization |
| --- | --- | --- |
| GET /health | Process liveness only; no secrets or dependency details | Public or infrastructure-only |
| GET /ready | Readiness of configured dependencies, reported without secrets | Infrastructure-only |
| GET /openapi.json | Generated API schema | Deployment policy controlled |

## Data contracts and pagination

List responses will use cursor or bounded offset pagination, explicit sort fields, and stable response schemas. UUIDs will identify V2 records. Timestamps use UTC ISO 8601. Model, storage, proof, and chain references will carry algorithms and hashes where applicable.

The React client will consume generated or shared TypeScript types rather than duplicate handwritten API shapes. Database entities remain backend-private and are never directly serialized.
