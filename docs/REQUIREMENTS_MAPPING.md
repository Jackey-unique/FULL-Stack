# Plan and assessment mapping

| Requirement | Implementation | Evidence |
|---|---|---|
| Python Flask + MongoDB | app factory, four Blueprints, actual MongoDB 8 local server | health endpoint, integration tests |
| Original application | BrainAge Connect schema/routes; no business-directory terminology | source and project plan |
| Dataset preparation | BIDS participant/session joins, image inventory, null/conflict handling | importer + local import report |
| Sufficient main records | 558 real sessions; separate 150-record synthetic demo | database counts |
| Multiple data types | strings, numeric weeks, booleans, ObjectIds, dates, arrays and nested objects | sample detail |
| Main CRUD | samples GET/POST/PUT/PATCH/DELETE | pytest + Postman lifecycle |
| Subdocument CRUD | notes and analyses, separate IDs/author/timestamps | pytest + Postman lifecycle |
| Queries | pagination, range/field/text filters, sorting | filter tests |
| Complex MongoDB operations | cohort/latest-result/paired-result aggregation, facet overview | numerical assertions |
| Authentication and ownership | JWT, bcrypt, approval, role/owner/author checks, revoke/version | success and failure tests |
| User management | list/read/activate/deactivate/change role | admin tests |
| Export | filtered JSON/CSV summaries and mongoexport scripts | Postman + exported JSON |
| Analysis histories | paginated stored precomputed results and signed differences | demo results and tests |
| Actual MRI brain-age prediction | Conditional in plan; no supplied verified model; not claimed implemented | documented scope |
| API documentation | API.md, OpenAPI JSON, described Postman collection | importable local artifacts |
| Submission code/database ZIPs | package script, synthetic dataset ZIP; real backup separate | submission/ |
| Video, separate PDFs, self-evaluation | Excluded by user request | student to prepare |
| AI disclosure/chat history | explicit assistance disclosure and design notes; complete chat must be appended by student | DESIGN_AND_AI.md |

No score or grade is promised. The student's final submission must accurately describe the dataset choice, synthetic demonstration boundary and AI contribution.
