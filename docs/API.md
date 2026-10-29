# BrainAge Connect API reference

Base path: `/api/v1`. Send `Authorization: Bearer <access_token>` except for health, schema, registration and login. JSON requests require `Content-Type: application/json`. Unknown fields, repeated/unknown query parameters and invalid types are rejected.

## Endpoint catalogue

| Method | Resource | Behavior / authorization |
|---|---|---|
| GET | `/health` | Database health; public |
| GET | `/openapi.json` | Machine-readable API description; public |
| POST | `/auth/register` | Create inactive researcher account; public |
| POST | `/auth/login` | Credentials to one-hour JWT; active users only |
| GET | `/auth/me` | Current profile, never password hash |
| POST | `/auth/logout` | Revoke current token; 204 |
| PUT | `/auth/password` | Change password and revoke all existing sessions |
| GET | `/samples` | Search/filter/sort/paginate visible records |
| POST | `/samples` | Create a private manual record owned by the caller |
| GET | `/samples/{id}` | Full visible record, including nested data and relative file references |
| PUT/PATCH | `/samples/{id}` | Update supplied fields only; owner/admin |
| DELETE | `/samples/{id}` | Delete record and embedded data; owner/admin; 204 |
| GET/POST | `/samples/{id}/notes` | List/paginate notes or create a note on a visible record |
| GET/PUT/PATCH/DELETE | `/samples/{id}/notes/{note_id}` | Retrieve/edit/delete note; mutation requires author/admin |
| GET/POST | `/samples/{id}/analyses` | List/paginate history or store a supplied precomputed estimate |
| GET/PUT/PATCH/DELETE | `/samples/{id}/analyses/{analysis_id}` | Retrieve/edit/delete result; mutation requires author/admin |
| GET | `/statistics/overview` | Counts by status, source and modality |
| GET | `/statistics/cohorts` | Age-group counts and mean scan age |
| GET | `/statistics/maturity` | Latest matching estimate per sample/modality; optional model and age grouping |
| GET | `/statistics/comparison` | Paired latest matching dMRI minus fMRI estimate; optional model selection |
| GET | `/exports/cohorts` | Same cohort summary as JSON or CSV |
| GET | `/users` | Paginated accounts; admin only |
| GET | `/users/{id}` | Single account; admin only |
| PUT/PATCH | `/users/{id}` | Set role/active and invalidate sessions; admin only, not own account |
| GET | `/audit-logs` | Paginated mutation events; admin only |

## Request examples

Register: `{"username":"researcher.one","display_name":"Researcher One","password":"A-strong-password"}`. The administrator must set `{"active":true}` on the new user before login succeeds. Role is never accepted at registration. Passwords must have at least 10 characters and at most 72 UTF-8 bytes.

Login: `{"username":"researcher.one","password":"A-strong-password"}`. Response includes `access_token`, `token_type`, `expires_in`, and `user`. Password update: `{"current_password":"...","new_password":"..."}`.

Create sample:

```json
{
  "sample_code": "RESEARCH-001",
  "age_at_scan_weeks": 40.5,
  "birth_age_weeks": 38.0,
  "sex": "Female",
  "has_dmri": true,
  "has_fmri": true,
  "status": "ready",
  "visibility": "private",
  "description": "Research metadata record"
}
```

`sample_code` and `age_at_scan_weeks` are required; age may be null when unknown. Scan age range is 20–80 weeks; birth age range is 20–45 and cannot exceed scan age. These are application input bounds, not diagnostic thresholds. Status: registered/ready/processing/completed/failed. Sex: Female/Male/Unknown. Visibility: private/shared. Public registration does not grant access to real data; imported records are private to their owner. An administrator must deliberately share records or approve a suitably authorized user. The server does not verify institutional research permissions.

For imported dHCP samples, sample_code and detected modality flags are read-only through the API. The importer controls them. Age and descriptive metadata can be corrected by the owner/admin, while raw source metadata remain available for provenance. Editing age recomputes stored age differences.

Create note: `{"text":"Research observation","category":"research"}`. Categories: research/quality/review. Text length: 1–4000. A maximum of 200 notes and 200 analyses per sample bounds document growth. Notes/analyses have their own `_id`, author and timestamps.

Create analysis:

```json
{
  "modality": "dmri",
  "estimated_age_weeks": 41.2,
  "method": "Name of externally executed method",
  "model_version": "Exact model version",
  "provenance": "Description or reference for the authorized precomputed result",
  "quality_score": null
}
```

Required: all fields above except quality_score. Modalities: dmri/fmri/combined; corresponding images must be marked available. Estimated age must be 20–80; quality_score is null or 0–1. The server calculates `age_difference_weeks = estimated_age_weeks - age_at_scan_weeks`; it is null for unknown scan age. It is not a diagnostic score. Source, result_type, identifiers, owner/author, timestamps, version and derived differences are server-managed. API input provenance is a declaration from the user, not independently verified scientific validation.

## Queries and responses

`GET /samples?q=sub-CC&age_min=37&age_max=42&modality=both&status=ready&source=dhcp_local&page=1&page_size=20&sort=age_at_scan_weeks&order=asc`

Filters: q (literal case-insensitive sample-code substring), inclusive age_min/age_max, modality (dmri/fmri/both/neither), status, source (dhcp_local/manual/synthetic), sex. These same filters are available on statistics and cohort export endpoints. Null ages do not match numeric age ranges.

Pagination defaults: page=1, page_size=20, maximum size=100. Page must be 1–1,000,000. Sample sort: sample_code, age_at_scan_weeks, created_at, updated_at. Nested lists sort by created_at or updated_at; order asc/desc. Stable ID tie-breakers avoid ambiguous ordering. An out-of-range page is an empty array with correct totals.

List shape: `{"data":[...],"pagination":{"page":1,"page_size":20,"total":558,"pages":28}}`. Single record: `{"data":{...}}`. Identifiers are 24-character ObjectId strings; timestamps are UTC ISO 8601. Lists omit large nested arrays; fetch a detail or nested endpoint for those.

Created resources return 201; reads/updates return 200; successful deletes/logout return 204 with an empty body. Errors use `{"error":{"status":400,"message":"..."}}`. Statuses: 400 invalid input, 401 missing/invalid/expired/revoked session, 403 insufficient privilege/inactive account, 404 absent or invisible resource, 409 duplicate or concurrent update, 413 body too large, 415 non-JSON body, 503 database unavailable.

## Aggregations and exports

Cohort intervals: <32, 32–<37, 37–<42, >=42 weeks, unknown. They are descriptive grouping bins only. Counts are scanning sessions, not unique infants; a participant with multiple sessions contributes multiple records. Means ignore null ages. Sources are grouped separately so synthetic and real results are not averaged together.

Maturity accepts optional exact, case-sensitive `method` and `model_version` filters (1–120 characters), applied before selecting the latest *created* result per sample and modality. `group_by=age_group` adds scan-age bands (<32, 32–<37, 37–<42, >=42 and unknown); the default `overall` groups by source and modality. `difference_count` is the number of selected results with a non-null age difference and is the denominator for its mean. Editing an old result does not make it newest. Comparison accepts separate `dmri_method`, `dmri_model_version`, `fmri_method`, and `fmri_model_version` filters, applied before latest selection; only matching paired samples contribute. Without filters, methods or versions may be mixed. All results are exploratory descriptions, not calibrated scientific estimates. Empty histories produce empty arrays.

`GET /exports/cohorts?format=csv` returns a download named cohorts.csv; format=json is the default. All summary pipelines apply exactly the same visibility filter as sample reads. No endpoint serves raw MRI files or accepts arbitrary local file paths.

## Postman

Import the collection and environment from `postman/`. Start the synthetic demo on port 5001 and run all requests in order. The collection obtains tokens, creates/approves a temporary researcher, tests success and failure paths, exercises CRUD and summaries, deletes its sample and disables its test account. It leaves audit history and the disabled test account in the selected database. `python -m scripts.run_postman` instead uses a temporary real database and removes it after the run.

Importing the collection gives request descriptions, payload examples and automated assertions. Publish through your own Postman workspace if a public documentation URL is needed; no account publication has been performed by this project.
