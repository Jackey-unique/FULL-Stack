# Design, implementation and AI assistance

## Authorship disclosure

This implementation was generated with substantial assistance from OpenAI Codex in this chat: API code, validation, authentication, importer, demo generator, tests, Postman collection, local tooling, schema, browser console and documentation. The project plan and downloaded datasets were provided by the student. Do not represent the generated implementation as independently authored without assistance.

This file records design decisions and the scope of assistance. It is NOT a complete chat transcript, and it does not claim the student has reviewed or understood the code. Export/append the actual full chat history when preparing the coursework Design and Development document. The excluded video/PDF/self-evaluation materials remain to be prepared by the student.

## User-provided implementation instructions (excerpts)

> 除了视频 分别的pdf文件和自我评估表 你去给我完成其他所有的代码内容 所有项目内容放在桌面的"C:\Users\18712\Desktop\full stack" 中 里面有一个plan文件是我的项目计划 这两个pdf是需要用到的软件和课程手册 你可以去参考

> 两个huggingface的数据我都下载到本地了 在桌面上

The assistant inspected the plan, referenced the supplied Flask/MongoDB course material, built the implementation, imported local metadata, and ran automated verification. Exact intermediate responses and tool interactions remain in the original chat and must not be replaced by this summary if full history is required.

## Architecture

Flask application factory creates an independent database client/configuration for each environment. Blueprints divide authentication, samples/nested resources, administration and analytics. Shared helpers implement strict validation, JSON serialization, visibility and compare-and-swap updates. There is no dependency on the Biz Directory codebase.

MongoDB collections: samples, users, audit_logs, revoked_tokens. Notes and analyses are embedded document arrays with ObjectIds. File references are another embedded array. The sample detail can be retrieved in one read. Passwords are bcrypt hashes; tokens carry identity and auth_version, and every request checks the current database account. Revoked tokens expire using a MongoDB TTL index, but validity is checked immediately independently of TTL cleanup.

Users are separate from sample documents because they are shared identities with independently mutable permissions. Author/owner fields refer to user ObjectIds. Accounts are deactivated rather than deleted, preserving references. API serialization excludes password_hash and auth_version.

## Algorithms and alternatives

- BIDS import uses a dictionary keyed by (subject, session), merging modality metadata without joining unrelated repeat scans. Raw TSV data are retained for traceability. Re-import uses insert-only semantics; an explicit refresh touches file presence only. An alternative is replacing entire records, which would lose user notes/edits and is deliberately avoided.
- Pagination uses skip/limit and indexed sort with an ObjectId tie-breaker. This is appropriate for hundreds of records. Cursor pagination would scale better for very large offsets.
- Literal regex search escapes input to prevent clients injecting a regex or MongoDB expression. Leading substring searches may scan; an Atlas search index would help much larger datasets.
- Embedded edits read a version and update only if it still matches. Concurrent changes produce 409 instead of silently overwriting another writer. A separate notes/results collection would scale beyond the explicit 200-entry cap but would require extra joins/queries.
- Analytics uses $match, $facet, $unwind, $sort, $group, $arrayToObject and arithmetic expressions. The visibility predicate is applied before aggregation. Latest-per-modality selection avoids giving extra weight to repeated analyses of the same sample.
- A server-derived signed age difference is recalculated after estimate/reference-age updates. No random prediction endpoint is provided. Choosing or training an MRI model is not substituted with a guessed formula.

## Access model

Public registration creates an inactive researcher. Only admins activate accounts or set roles. Private records are visible only to owner/admin. Shared records are visible to approved users. Only the sample owner/admin can edit/delete a sample. Any user who can see a sample can add a note/result; only that entry's author/admin can modify it. Admins cannot change their own role/activation, preventing self-lockout through that route.

The local deployment binds to loopback. It is an educational application, not a hardened multi-institution production service. Before network deployment add TLS, database authentication, login throttling, an appropriate consent/access workflow and operational backups. Audit writes are separate from resource writes on the standalone MongoDB server, so they are not transactionally atomic during a database failure. Multi-document transactions would require a replica set.

## Scope and known boundaries

The implementation fulfills the planned CW1 data-management backend. It does not construct connectivity matrices, run inference, issue diagnoses, train a model or implement the separate CW2 Angular application. The browser console is a convenience inspection UI, not a replacement for the full API/automated testing. The raw MRI file content is not exposed through an HTTP download route.

Real records and synthetic fixtures use separate databases. No actual user passwords or JWT secrets are placed in submission archives. Local dHCP exports are not included in the shareable synthetic database package.

## Review before recording the walkthrough

Trace a request from auth_required through visibility and validation to MongoDB. Explain why sessions use a composite source key; how embedded ObjectIds differ from sample ObjectIds; why the age unit is postmenstrual weeks; how revocation/auth_version work; why optimistic locking returns 409; and how the aggregation pipeline avoids counting all historical analyses as independent samples. Review the tests and explain what they establish and what they do not establish scientifically.
