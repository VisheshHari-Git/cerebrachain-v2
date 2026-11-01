# Frontend Design Specification

## Status and source-of-truth order

This document records the required V2 frontend direction. It does not authorize frontend implementation.

At the time of writing, the reference sketches and AI-generated visualization described by the project owner are not accessible as local files in this workspace or as attached images in this conversation. They have therefore not been inspected. Before implementation begins, the supplied references must be made available as accessible local files and recorded in the implementation task.

When available, visual direction is resolved in this order:

1. Google Stitch design files are the primary visual reference.
2. The three original frontend reference sketches and the AI-generated visualization refine missing or ambiguous details.
3. This specification defines non-visual product, accessibility, responsiveness, integrity, and modularity constraints.

Stitch output must be refactored into maintainable React components, tokens, routes, and feature modules. It must not be pasted into a single generated page component.

## Visual language

The application must present as a professional medical-technology interface, not a generic administration dashboard.

- Use a dark navy visual foundation.
- Use purple and cyan neon accents deliberately for interactive, status, and data-visualization elements.
- Use glassmorphism surfaces with controlled translucency, readable contrast, subtle borders, and layered depth.
- Use clean, legible typography with an explicit type scale.
- Use smooth, restrained Framer Motion transitions that support orientation and state changes without obscuring clinical/research information.
- Make an interactive 3D brain visualization a first-class experience where it is appropriate, not a decorative placeholder.
- Keep charts, imaging views, proof states, and chain records visually distinguishable while sharing the same design system.
- Support responsive layouts from smaller laptop/tablet widths through wide clinical-dashboard displays.

The final implementation must derive reusable design tokens for color, spacing, radii, blur, shadows, typography, chart colors, focus states, and animation timing from the approved Stitch/reference material.

## Required screens

| Screen | Purpose | Required content / integrity constraint |
| --- | --- | --- |
| Landing page | Explain the research platform and direct users to authorized workflows | Dark medical-technology hero, system overview, role entry points, clear research-only framing |
| Hospital login and registration | Hospital administrator onboarding and authentication | Separate login/registration paths, accessible form controls, explicit approval/error/pending states |
| Doctor login and registration | Doctor account onboarding and authentication | Hospital-aware account flow, accessible validation, no credential values in client logs |
| Hospital dashboard | Hospital-scoped operational overview | Authorized study/activity summaries, model/round status, empty/loading/error states |
| MRI upload and analysis | Submit four-modal MRI studies and observe analysis workflow | Explicit FLAIR, T1, T1CE, T2 requirements; upload validation and analysis status; no simulated result |
| Real 3D MRI segmentation viewer | Review authorized model output | Axial, sagittal, coronal views; interactive segmentation overlays; model/result provenance; unavailable state if no real result exists |
| Federated learning dashboard | Monitor Flower federation activity | Participating hospitals, Flower connectivity/status, measured training rounds, contribution records, and evidence status |
| Global model dashboard | Present registered global-model state and measured metrics | Model version/hash, provenance, validation scope, metrics only when actually recorded |
| ZKP verification dashboard | Present actual proof-workflow status | Circuit/version context, observed verification result, receipt metadata, explicit pending/failed/not-requested states |
| Blockchain explorer | Present actual on-chain provenance records | Configured network context, transaction hashes, model/anchor records, and unavailable/no-record states |

## MRI analysis and viewer requirements

The MRI workflow is a protected, hospital-scoped research workflow. It must support the verified modality order:

1. FLAIR
2. T1
3. T1CE
4. T2

The interface must make the four required modalities clear before submission and visually distinguish incomplete, validating, ready, queued, running, failed, and completed states.

The segmentation viewer must support:

- axial, sagittal, and coronal orientation controls;
- slice position controls appropriate to the rendered volume;
- interactive segmentation visibility and opacity overlays;
- an accessible legend for labels and overlays;
- provenance display for the model artifact hash, analysis time, and result status;
- loading, permission-denied, empty, failed, and unavailable states;
- responsive interaction patterns that remain usable without a large display.

The viewer must show only an actual authorized segmentation result returned by the backend/ML integration. Before that integration exists, it must render an explicit unavailable/empty state. It must not create synthetic masks, substitute arbitrary imagery, or imply a diagnostic result.

The existing trained MONAI 3D U-Net remains the planned model integration. Its loading, preprocessing, inference, and postprocessing stay in the backend ML boundary; React receives only authorized, derived visualization/report contracts.

## Federated-learning requirements

The federated dashboard must distinguish observed data from unavailable or unverified data. It must be able to show:

- participating hospitals and their permitted display names;
- Flower client/SuperLink status when an integration actually provides it;
- round identifiers, lifecycle state, timestamps, participants, sample-count evidence, and aggregation configuration;
- registered global-model version/hash and provenance;
- measured validation metrics with their dataset/evaluation scope;
- hospital contribution records and verification/evidence status.

It must not fabricate a successful round, hospital participation, metric, model update, or validation result. Missing evidence must be represented visibly rather than converted to a positive status.

## ZKP, blockchain, and IPFS requirements

Trust-layer screens must show only actual backend-provided verification and chain records.

- Proof status must distinguish not_requested, pending, verified, rejected, failed, and unavailable.
- A proof view must identify the circuit/version binding and non-sensitive receipt metadata.
- A blockchain view must display actual configured-network context, transaction hashes, model records, and anchor records when present.
- A CID is an integrity/content-addressed reference; the UI must not imply that it proves clinical validity, training correctness, data provenance, privacy, availability, or authorization.
- The UI must state only the properties actually enforced by the circuit and verified workflow.
- No wallet key, proving key, private witness, raw private update, or protected artifact content may reach the browser.

## Modularity plan for later implementation

The future React application should use the following boundaries:

| Area | Intended location |
| --- | --- |
| Route composition and page shells | apps/web/src/app |
| Shared visual primitives and glass layouts | apps/web/src/components/ui and apps/web/src/components/layout |
| Authentication workflows | apps/web/src/features/auth |
| Hospital overview workflows | apps/web/src/features/dashboard |
| Upload, viewer, and report workflows | apps/web/src/features/imaging |
| Federation monitoring | apps/web/src/features/federation |
| Proof/chain monitoring | apps/web/src/features/trust |
| Typed HTTP clients | apps/web/src/services |
| Shared browser types | apps/web/src/types |
| Design tokens and global styles | apps/web/src/styles |

React Three Fiber and Three.js should be isolated behind dedicated visualization components with graceful loading/error fallbacks. Recharts should consume normalized, typed monitoring data rather than make API calls directly. Framer Motion usage should remain at component/page transition boundaries, not inside domain services.

## Accessibility and responsive quality

- Maintain keyboard access, visible focus indicators, semantic landmarks, labelled form controls, and screen-reader names for all controls.
- Do not encode status only by color; use text, icons, and accessible labels.
- Respect reduced-motion preferences.
- Preserve sufficient contrast despite neon/glass styling.
- Provide usable layouts for narrow screens, including collapsible navigation and non-overlapping MRI/viewer controls.
- Make data tables, charts, and overlays understandable with textual summaries or accessible equivalents.

## Implementation gate

Frontend implementation may begin only when all of the following are available in the task scope:

1. Google Stitch design files or exported design assets.
2. Accessible local copies of the three original sketches and the AI-generated visualization.
3. A decision on the approved route/authentication contract from the backend foundation.
4. A confirmed backend contract for real MRI analysis and visualization artifacts before the segmentation viewer is connected.

Until then, this document is the design record and the repository must remain free of speculative frontend implementation.
