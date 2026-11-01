# ZKP-CerebraChain V2 Engineering Rules

## Scope and delivery

- Work only in this repository unless a task explicitly authorizes a read-only inspection of an external legacy asset.
- Keep the V2 system a modular monorepo: React web application, FastAPI API, and focused integration packages. Do not introduce microservices without an approved operational reason.
- Build features in independently testable phases. Do not implement a future phase opportunistically.
- Keep each module focused. Do not place application logic in a frontend entry point, a FastAPI entry point, or a route handler.
- Update the relevant documentation whenever an integration contract, architecture boundary, or safety assumption changes.

## Frontend

- Use React, TypeScript, Vite, Tailwind CSS, Framer Motion, React Three Fiber, Three.js, and Recharts only when the relevant feature is implemented.
- Place pages and route composition in apps/web/src/app. Keep reusable presentation components in components and domain logic in features.
- Put HTTP clients in apps/web/src/services. Keep auth state in a dedicated feature or store, not in visual components.
- Use strict TypeScript types, accessible labels and controls, responsive layouts, and explicit loading, error, and empty states.
- Treat Google Stitch output as source material. Refactor it into reusable components and design tokens; never paste generated page-sized markup into the application unchanged.

## Backend

- Version all public API routes below /api/v1.
- Keep FastAPI route handlers thin. Request and response schemas belong in schemas, persistence in repositories, and business rules in services or modules.
- Use SQLAlchemy with PostgreSQL and Alembic migrations. Do not use raw SQL in routes.
- Use Pydantic validation, structured error responses, type annotations, structured logging, and tests for every security-sensitive service.
- Enforce hospital tenancy at the query boundary and the authorization boundary. A client-provided hospital identifier never grants access.
- Keep authorization role-based and deny by default.

## MRI and machine learning

- Never add MRI, DICOM, NIfTI, NPZ, model weights, checkpoints, generated masks, or patient records to Git.
- Do not train, alter, convert, or overwrite legacy model artifacts unless an explicit task authorizes it.
- Load model paths, expected SHA-256 values, device selection, and storage locations from validated configuration. Application code must not contain absolute asset paths.
- Keep preprocessing, model loading, inference, postprocessing, and artifact persistence separate from HTTP handling.
- Do not describe research-only output as clinical advice, a diagnosis, clinically validated, or independently validated unless evidence is recorded and reviewed.
- Preserve the verified source model modality order: flair, t1, t1ce, t2. Any change requires an explicit compatibility test and documentation update.

## Federated learning, ZK, blockchain, and IPFS

- Never fabricate rounds, metrics, proof results, chain transactions, CIDs, or model provenance.
- Treat Flower clients and the aggregation server as separate trust domains. A round must record input model hashes, participant identities, sample counts, outputs, and validation status.
- Reuse a Flower, circuit, verifier, contract, or IPFS component only after an interface, security, and version compatibility review.
- State exactly what a circuit proves. A proof of quantized-update integrity or norm bounds does not prove clinical validity, data provenance, or correct neural-network training.
- Private keys, proving keys, witness data, private update chunks, and local IPFS payloads must remain outside the repository and out of terminal output.
- Require environment-provided chain credentials in any future runtime. Never retain a development-key fallback in V2 code.

## Security and privacy

- Never commit secrets, environment files, private keys, credentials, tokens, database URLs, patient data, or clinical artifacts.
- Do not print secret values. When checking configuration, report only the presence or readiness of a value.
- Use safe synthetic or explicitly de-identified demo data only. Treat research identifiers and metadata as sensitive unless approved for publication.
- Validate file type, size, content, paths, and tenancy before accepting uploads. Store protected artifacts outside the repository.
- Use signed, short-lived authentication tokens or secure server-side sessions as appropriate; passwords must be salted and hashed with a modern password-hashing algorithm.

## Quality and Git

- Use descriptive names, small composable functions, explicit error paths, and no unused imports or dead code.
- Run formatting, linting, type checks, unit tests, integration tests, and production builds relevant to the change before committing.
- Review git diff and staged diff before every commit. Check staged files for secrets and prohibited medical/model artifacts.
- Stage only intended files. Never force-push, rewrite history, initialize another repository, or modify unrelated files.
- Use concise imperative commit messages. Push only after validation succeeds.
