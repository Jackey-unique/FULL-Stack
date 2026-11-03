# COM661 CW1 submission audit - 2 November 2026

Source: the six-page `COM661 CW1 Specification.pdf` supplied by the student, especially pages 1-3 and the page 6 marking proforma. This is an evidence review, not a prediction of the examiner's mark.

## Verdict

The Flask/MongoDB backend is above the Biz Directory example in scope: 35 HTTP operations, main and embedded resource CRUD, account approval and token invalidation, compound filtering and aggregation. Its claimed purpose is management of infant MRI *metadata and externally supplied precomputed results*. It does not perform MRI inference or clinical diagnosis.

Update 3 November 2026: the package is **not yet fully at the 80-100% submission standard** because the mandatory student video is intentionally outstanding. `04_Postman_Collection_Documentation.pdf` now contains a public Postman link, eight genuine pointer-free documentation screenshots with explanations, a detailed local reference, and the original 57-page print-to-PDF output from the live Postman-hosted document. A genuine Postman Runner export and a pointer-free view of its screenshot are also present. The student must personally verify their critical appraisal and demonstrate understanding of AI-assisted code in the video.

## Requirement-by-requirement evidence

| Specification requirement / rubric | Current evidence | Judgment |
|---|---|---|
| Python Flask API with MongoDB; main and subdocument CRUD | `brainage/`, `tests/test_api.py`, code listing, code ZIP | Implemented. |
| Dataset size, types, populated subdocuments (15%) | Synthetic mongoexport ZIP: 150 sessions, two users, nested notes/analyses; separate documented 558-session local dHCP metadata import | Strong structure, but the submitted dataset is synthetic; do not call it real dHCP data or model output. |
| Complex database queries (25%) | Facet, latest matching model result, paired dMRI/fMRI comparison, age-band aggregation, filters and exports | Strong functionality. Unfiltered model means can mix methods/versions; no current query-plan or load benchmark evidence. |
| RESTful API and design (25%) | 35 operations, four Blueprints, documented status codes, auth/permission rules | Strong for a coursework backend. OpenAPI success schemas are example-derived and non-exhaustive; PUT has documented partial-update semantics. |
| Usability and validation (25%) | 52 real-MongoDB pytest cases passed in the recorded 28 October run; strict type/range checking and actionable errors; 48-request Postman lifecycle | Strong covered behavior. This audit did not rerun MongoDB integration on 2 November; no claim of exhaustive coverage, scientific validity or production security. |
| Backend code ZIP | `BrainAgeConnect_Code.zip` | Present; rebuilt after this audit's code/collection changes. |
| One mongoexport JSON per collection in a ZIP | `BrainAgeConnect_SyntheticDatabase.zip` has samples, users, audit_logs, revoked_tokens | Present; two collections are legitimately empty in the recorded export. |
| Complete backend code listing PDF | `01_Complete_Code_Listing.pdf` | Present and refreshed after runner change. |
| All API endpoints summary PDF | `02_API_Endpoint_Summary.pdf` | Present: 35 operations. |
| Automated Postman test printout PDF | `03_Automated_API_Test_Results.pdf`; native Runner PNG and native Postman 2 JSON | Present. The PDF includes a genuine earlier Newman run and a pointer-free displayed portion of the later native Runner screenshot. |
| Postman-generated API documentation printout PDF | `04_Postman_Collection_Documentation.pdf` | Present: 28-page annotated front section, public Postman URL, eight pointer-free UI screenshots with explanations, and 57 pages printed directly from the live Postman-hosted document. |
| Self-evaluation sheet | Official assessment grid workbook with weighted formula, plus evidence/rationale sheet | Present and updated to reflect model filtering, age bands and Runner evidence. Provisional self-mark 77.25/100 is not an awarded grade. |
| Design/development and AI chat history | `05_Design_Development_and_AI_Record.pdf` | Present, now including 85 available visible user/assistant messages through its stated cutoff. Earlier source snapshots have expired from local logs; their preserved redacted export and recorded hashes remain. The live conversation after the cutoff is naturally outside the PDF. |
| Video <=5 minutes | No video, per student's explicit exclusion | Outstanding and critical: the specification says missing video can severely affect high marks. |

## Current Postman state

The genuine native results are `Postman2_Runner_2026-10-28.json` and two Runner PNGs. The local collection includes 48 requests, 63 assertions and 48 saved redacted response examples. The maturity/comparison descriptions explain exact model filters and age bands. Standard Postman 12.34.1 contains the authorized synthetic-only collection and environment in the student cloud workspace. With the student's explicit confirmation, the collection documentation was published at https://documenter.getpostman.com/view/59247931/2sBYHXQdXe without publishing an environment. The URL returned HTTP 200 without authentication on 3 November. The 57-page browser printout is appended in `04`; the original printout is also supplied separately. Seven desktop documentation screenshots plus one public-page screenshot are embedded with explanatory captions. The local collection's Runs view has no saved run, so the original 28 October Runner result is used as dated evidence in `03`. No new integration execution on 3 November is claimed.

## Submission sequence

1. Student records the <=5-minute demonstration in their own words: domain/dataset, Postman CRUD/auth/statistics, and the most complex code. The specification warns that absence of video severely limits high marks.
2. Student reviews the official self-evaluation and AI record, then uploads the individual required files to Blackboard. The combined written pack is only a convenience copy; the specification calls for separate code/data ZIPs and separate PDFs. The self-evaluation was prepared before the native Postman printout was obtained and should be reviewed as a provisional self-assessment.

The code was not changed for the sake of claiming a higher band. This audit distinguishes verified execution evidence from specification compliance and from scientific claims.
