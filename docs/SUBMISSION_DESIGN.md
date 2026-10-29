# Design and development

## 1. Application purpose and implementation scope

BrainAge Connect is a Flask/MongoDB backend for infant MRI session metadata, research notes and externally supplied precomputed developmental-age estimates. The intended workflow is to identify suitable scan sessions, manage access, record observations and supplied results, and compare descriptive summaries. It does not preprocess MRI, construct connectomes, run a model, or make clinical diagnoses.

The original plan used the title "Infant Brain Developmental Maturity Diagnostic Support". The delivered scope is narrower and explicitly research-oriented. The plan made prediction conditional on the availability of suitable precomputed results or a pretrained model. No verified model was available. Consequently, real records have empty analysis histories until authorized results are supplied; the demonstration database uses labelled invented fixtures. Age is postmenstrual age at scan, not chronological age since birth.

## 2. Data preparation and provenance

The student supplied local dMRI and fMRI folders associated with RichardErkhov/dhcp_dmri_pipeline and RichardErkhov/dhcp_fmri_pipeline on Hugging Face. The importer reads participants.tsv, subject session TSVs and dataset descriptions. A dictionary indexed by subject and session merges corresponding modalities without conflating repeat visits. Source metadata and relative file references are retained for traceability.

The previously recorded local import contains 558 scan sessions, 546 sessions represented in both metadata sources and 12,514 indexed files. Primary-image presence checks recorded 490 dMRI, 512 fMRI and 444 paired sessions. These are import-snapshot figures, not a new complete MRI download or QC verification performed while writing this report. Presence means expected file name, nontrivial size and gzip signature; it does not establish image integrity or scientific quality. Invalid or conflicting ages are preserved in raw metadata and standardized to null rather than invented.

The shareable submission database contains 150 entirely synthetic sessions, 150 initial notes and 232 synthetic result fixtures, with two demonstration accounts. The fixed random seed makes the fixture values repeatable, although ObjectIds and timestamps are generated at execution. There are no real patients or MRI files in this ZIP. Synthetic modality flags are testing conditions, not evidence of images. The course Clinic explicitly permits realistic constructed datasets. Real research exports remain private; the project does not claim independently verified redistribution permission for the source mirror.

## 3. Architecture and request lifecycle

An application factory loads configuration, creates a MongoClient, checks connectivity, creates indexes and registers four Blueprints: authentication, samples/nested resources, statistics/exports and administration. Shared helpers centralize validation, serialization, visibility filtering, pagination, auditing and version-checked updates. Waitress binds the educational deployment to loopback.

A protected request follows: Bearer token decoding and issuer/audience/expiry checks; current account and session-version lookup; optional administrator check; visibility and ownership checks; request validation; MongoDB query or mutation; audit event for mutations; JSON-safe serialization. ObjectIds become 24-hex strings, dates become UTC ISO 8601 and password_hash/auth_version are withheld from public JSON. Error handlers produce a consistent status/message object, including 503 for MongoDB failures.

The design separates domain logic from the entry point and permits independent test applications with unique database names. It avoids global database handles shared across real, demo and test environments. The tests exercise a real MongoDB server rather than a substitute in-memory implementation.

## 4. Data structures and alternatives

The four collections are samples, users, audit_logs and revoked_tokens. A sample embeds notes, analyses and file references. Notes and analyses have independent ObjectIds, authors and timestamps, allowing REST sub-resources without separate collections. Embedding makes a session detail available in one read and keeps related updates within one sample document. Each editable child array is capped at 200 entries to bound document growth.

Users are independent because shared identities and permission changes have their own lifecycle. owner_id and author_id reference user ObjectIds. Accounts are deactivated rather than deleted so references remain meaningful. Audit events are independent append records. Revocations use a unique jti and a TTL index on expiry; explicit lookup prevents a revoked token from remaining valid while asynchronous TTL cleanup is pending.

An alternative is separate notes and results collections. That would scale history beyond the cap and allow direct indexing of analysis fields, but would require additional queries or joins and explicit parent/reference consistency. Embedded structures are suitable for this coursework scale. File payloads remain outside MongoDB; the backend stores metadata, not large MRI binaries.

## 5. Validation and access control

Request bodies must be JSON objects. Allowed-field lists reject unknown and server-managed fields. Numeric checks exclude booleans, non-finite values and out-of-range ages. Birth age cannot exceed scan age. Modalities, sex, status, visibility and note categories are enumerations. Query keys cannot be unknown or repeated. Text search escapes input as a literal substring rather than accepting arbitrary regular expressions or MongoDB operators.

Registration creates an inactive researcher. Only administrators approve access or change roles; this invalidates previous tokens through auth_version. Passwords are bcrypt hashes with a 72-byte UTF-8 limit. Password changes invalidate all prior sessions; logout revokes one jti. Private records are visible to owner/admin; shared records are visible to approved users. Sample mutation requires owner/admin, while note/result mutation requires author/admin. An inaccessible record returns 404 to avoid confirming private-record existence.

The same visibility predicate is applied before statistics and exports. This is necessary because a protected detail endpoint alone would still permit indirect disclosure through counts or summaries. The application provides software access controls; it does not independently approve research ethics or institutional data access.

## 6. Query algorithms and complexity

List retrieval combines visibility, literal sample-code search, age bounds and categorical filters. Large embedded arrays are excluded from list projections. Sorting adds an ObjectId tie-breaker. skip/limit is simple and appropriate for hundreds of sessions; deep pagination would benefit from cursor/keyset pagination. Leading substring regex can require a scan, so an index should not be claimed to accelerate every search without explain evidence.

Overview statistics use a visibility-first match followed by facet pipelines for total, source, status and modality counts. Cohorts group by source and postmenstrual-age band. Boundaries are below 32, 32 to below 37, 37 to below 42, 42 or above, and unknown. These are descriptive groups rather than diagnostic thresholds. Counts represent scan sessions, not independent infants.

Maturity unwinds histories, sorts by creation time and embedded ObjectId, selects the first result per sample/modality, then computes source/modality summaries. Historical reanalysis therefore does not give one session disproportionate weight. Editing an older result changes updated_at but not created_at, so it does not become the latest created result.

Paired comparison selects latest dMRI/fMRI results, groups them per session, requires both, converts the key/value pairs into an object and computes the signed dMRI-minus-fMRI difference. An unpaired session does not contribute. The server also derives estimated-age-minus-scan-age for each supplied analysis and recomputes it when the reference age changes; an unknown reference produces null.

Maturity supports exact method/version filters before latest selection, optional scan-age bands and a count of non-null age differences. Comparison supports distinct filters for each modality before selecting the latest pair. Without filters, results can still mix methods and versions; repeated sessions of a participant are not adjusted for correlation. These remain exploratory summaries, not calibrated model evaluation.

## 7. Concurrency, auditing and REST decisions

Sample edits compare the version observed by the server with the stored version, increment it on success and return 409 on a competing write. Nested updates rewrite the bounded array under the same condition. Deletion also checks version. This protects overlapping server read-modify-write operations. It does not implement a client-supplied If-Match/ETag protocol for a browser that fetched a record much earlier.

Every resource has a plural REST path; child paths include their parent session. Create returns 201, successful reads/updates 200 and delete/logout 204 with no body. PUT and PATCH intentionally update only supplied editable fields, following the Clinic recommendation for flexible edits. This departure from full-replacement PUT semantics is stated in the API reference. IDs, source labels, owners and derived values are server-controlled.

Resource and audit writes are separate operations on the standalone server. They are not an atomic multi-document transaction during database failure. A replica set plus transaction handling would be needed for that stronger guarantee. The report therefore does not claim production-grade transactional audit integrity.

## 8. Testing and reproducibility

The review run passed 51 pytest cases, including parameterized invalid-input scenarios, against isolated real MongoDB databases. A subsequent documentation-enriched Postman collection passed 48 HTTP requests and 63 assertions with Newman. The test PDF lists individual outcomes and the exact test assertions; not all tests validate business values, and no complete branch-coverage percentage is claimed.

Postman obtains tokens and IDs dynamically, creates and approves a temporary account, exercises main/child lifecycles, checks permission failures, queries statistics and exports, deletes its sample, changes passwords, revokes sessions and disables the account. The runner starts a disposable API and removes its prefixed temporary database. No test resets the shared real or demo database.

The submitted database is genuine canonical Extended JSON produced by mongoexport. The existing restore verification checks record counts and preservation of ObjectIds, dates and nested IDs. Reproduction requires Python 3.12+, MongoDB Community Server, MongoDB Database Tools, a fresh virtual environment and a random JWT secret. Node/Newman is needed for command-line Postman collection execution. The full evidence set includes the code listing, operation catalogue, collection-derived reference, test results and assessment grid.

The PDFs improve documentation and presentation; they do not prove medical validity, source licensing, load capacity or security of an internet deployment. A native Postman 12.34.1 Runner screenshot was captured on 28 October 2026; a native documentation printout has not been produced. The supplied documents label collection/Newman provenance rather than impersonating those application outputs.

## 9. AI assistance and personal contribution

OpenAI Codex substantially assisted implementation of the API, importer, fixtures, tests, tooling, browser console and documentation. The student supplied the project plan and downloaded datasets. This document is also AI-assisted. The recovered conversation appendix presents the available user-visible prompts and assistant responses, with technical secrets redacted; it is not a substitute for the student's own explanation or critical review.

The local log contains damaged character encoding in some historical prompts. Text is preserved as available; missing words are not reconstructed as quotations. System/developer instructions, hidden reasoning, tool payloads and approval-review agent conversations are omitted because they are not the user/assistant dialogue required by the coursework. The appendix states its export cutoff and source hashes.

Before submission, the student should personally review the evidence-based self-evaluation and demonstrate understanding in the video. In particular, explain the subject/session key, embedding tradeoffs, authorization-before-aggregation, latest-per-modality pipeline, token invalidation and limits of version checks. This document does not assert that the student has already demonstrated that understanding.

## 10. References

COM661 CW1 Specification, Semester 1 2026-2027, pages 2-3 and 6; CW1 Assessment Grid, supplied template; API Coursework Clinic - Detail, sections 1-5; original Application Plan, Boyu Yuan / B01089181. Implementation evidence: app.py, brainage/, scripts/, tests/test_api.py, docs/API.md and the exported Postman collection. Dataset mirror links: https://huggingface.co/datasets/RichardErkhov/dhcp_dmri_pipeline and https://huggingface.co/datasets/RichardErkhov/dhcp_fmri_pipeline.
