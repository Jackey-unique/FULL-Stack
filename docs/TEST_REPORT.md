# Verification report

Generated: 2026-10-27T20:36:55+08:00 (Asia/Shanghai).

| Check | Result |
|---|---|
| Real MongoDB integration tests (pytest) | 51 tests; 0 failures; 0 errors |
| Postman collection executed with Newman | 48 HTTP requests; 63 assertions; 0 failures |
| Export/import round trip | Passed: 150 synthetic samples and 2 users; ObjectIds/dates/nested IDs preserved |
| Import idempotency | Second local import inserted 0 and preserved all 558 existing sessions |
| Local API health | Real service on 5000 and synthetic demo on 5001 returned HTTP 200 |
| Browser inspection | Login, source disclosure, sample table and sample detail/analysis history checked |
| Syntax | Python source compiled; browser JavaScript passed Node syntax check |

## Environment

Windows; Python 3.12.14; Flask 3.1.3; PyMongo 4.19.0; MongoDB Community 8.0.16; MongoDB Database Tools 100.13.0. API tests use the real local MongoDB server, not a mock.

## Coverage

Authentication success/failure, inactive registration and approval, token expiration and logout revocation, password-change invalidation, admin/owner/author permissions, sample CRUD, nested note/result CRUD, duplicate IDs/codes, wrong types/ranges, malformed JSON, invalid IDs, missing resources, pagination/filtering/literal search, derived age-difference recalculation, prevention of disabling referenced modalities, oversized page numbers, aggregation latest-result selection and paired comparison, private-record exclusion from summaries, CSV export and optimistic concurrency.

## Evidence files

- runtime/pytest-results.xml: individual test cases and timings.
- runtime/newman-results.json: full Newman run output (local only; includes short-lived test tokens).
- runtime/newman-console.txt: console summary.
- runtime/export-verification.json: round-trip checks.
- data/private/import_report.json: local dataset inventory and anomalies.

Temporary test databases use unique brainage_test_, brainage_postman_ and brainage_roundtrip_ prefixes and are removed after each run. The shared demo database is not the pytest/Postman-runner test target.

## Limits

These tests establish software behavior for the covered scenarios. They do not validate medical accuracy, MRI completeness/quality, the scientific comparability of different models, load capacity, production security, or research licensing. No MRI-based brain-age model was run. No video, PDF evidence or self-evaluation sheet was generated.


## 2026-10-28 macOS update

After model-selection and age-group changes, 52 pytest cases passed with temporary MongoDB 8.0.25 and Python 3.13; see runtime/pytest-macos-2026-10-28.xml. Postman desktop 12.34.1 Runner executed the 48-request lifecycle against synthetic local data: 63 tests passed, 0 failed, 0 errors. See submission/Postman_Runner_2026-10-28.png. This validates software behavior, not model or clinical validity.
