# BrainAge Connect — COM661 CW1

Python Flask + MongoDB research-data API, implemented from the project plan. The scope is CW1 back-end development, with a small browser console for inspection. The separate Angular/CW2 application is not included.

## 本机快速使用

1. 双击 **START_PROJECT.cmd**：运行真实本地数据版本，地址 http://127.0.0.1:5000 。
2. 打开 **docs/LOCAL_ACCESS.txt** 查看本机管理员用户名和随机密码。该文件不要提交或共享。
3. 登录网页控制台，可查看统计、搜索/筛选样本、翻页、打开样本详情。
4. 双击 **START_DEMO.cmd**：运行独立合成演示库，地址 http://127.0.0.1:5001 。演示管理员 `demo.admin` / `DemoAdmin!2026`，研究员 `demo.researcher` / `DemoResearch!2026`。
5. 完整接口操作及自动化测试：将 `postman/` 中 collection 和 environment 两个 JSON 导入 Postman，选择本地演示环境，按顺序运行整个集合。
6. 双击 **STOP_PROJECT.cmd** 可停止登记的项目后台服务。
7. 双击 **RUN_TESTS.cmd**：在临时数据库运行 Python 集成测试。测试不会修改真实数据或演示库。

运行所需环境已在此目录准备好：`.venv/` 是 Python 虚拟环境，`tools/` 是便携 MongoDB 和数据库工具。MongoDB 仅监听本机 27018 端口；API 仅监听本机。首次启动若被防火墙询问，不需要开放公网访问。

## Data and scientific boundaries

- Real database: `brainage_connect`; imported from the user's local dHCP dMRI/fMRI directories. Records are private to the administrator by default.
- Demo database: `brainage_demo`; 150 invented samples, 232 invented precomputed-result fixtures. These are NEVER represented as dHCP observations or valid brain-age predictions.
- Real scan age is **postmenstrual age in weeks**, not chronological age since birth.
- Primary image availability reflects a local file presence/size/gzip-header check, not complete-download verification or imaging QC.
- The downloaded files do not supply a verified brain-age prediction model. This project manages and compares supplied precomputed estimates; it does not implement MRI preprocessing, tractography, connectome construction, model training, or clinical diagnosis.
- There are no fabricated brain-age estimates in the real dHCP database. Empty analysis histories are expected until authorized precomputed results are supplied.

## Main functionality

- JWT login, expiring tokens, logout revocation, bcrypt password hashing, password-change session invalidation.
- New accounts require administrator approval; admin account activation/roles; private/shared records; owner/author checks.
- Sample CRUD; embedded note and analysis CRUD; partial PUT/PATCH; derived age differences.
- Pagination, stable sorting, literal text search, age ranges, modality, sex, source and processing-status filters.
- MongoDB aggregation pipelines for overview, age cohorts, latest per-modality results and paired modality differences.
- CSV/JSON cohort exports; audit logs; unique/indexed queries; conflict detection for concurrent edits.
- Local BIDS metadata importer, repeatable synthetic data generator, precomputed-result importer and genuine `mongoexport` exports.

## Project structure

| Path | Purpose |
|---|---|
| `brainage/` | Application factory, Blueprints, validation, authentication and query logic |
| `scripts/` | Bootstrap, imports, demo seed, exports, packaging, schema and Postman runner |
| `tests/` | Automated tests against a real isolated MongoDB database |
| `postman/` | Importable collection and local demonstration environment |
| `static/` | Small browser inspection console |
| `docs/` | API reference, design/AI disclosure, requirements mapping and data notes |
| `data/private/` | Local source paths and detailed import report; do not redistribute |
| `runtime/` | MongoDB files, logs and raw test reports; not submission material |
| `exports/local/` | Local research database export, including account hashes; not for public sharing |
| `exports/demo/` | Exported synthetic demonstration database |
| `submission/` | Code ZIP and synthetic-database ZIP |

## Reproduce on another computer

Use Python 3.12 or newer and MongoDB Community Server. Create `.venv`, install `requirements-dev.txt`, copy `.env.example` to `.env` and replace its secret with a random value. Start MongoDB at the configured URI. Run these commands from the project root:

```powershell
.venv\Scripts\python.exe -m scripts.bootstrap
.venv\Scripts\python.exe -m scripts.import_dhcp --dmri "path/to/dhcp_dmri_pipeline" --fmri "path/to/dhcp_fmri_pipeline"
.venv\Scripts\python.exe -m scripts.seed_demo
.venv\Scripts\python.exe -m scripts.generate_openapi
.venv\Scripts\python.exe app.py
```

The importer never moves the original images. It indexes their relative paths and reads TSV/JSON metadata. Existing sample records are preserved on rerun; `--refresh-files` updates file availability only. To restore exported collections, run `python -m scripts.import_database --database brainage_restored --input exports/demo`. This uses mongoimport for populated collections, creates empty collections explicitly, and rebuilds indexes. It refuses to overwrite a nonempty database. Set MONGO_DB to the restored name when serving it.

## Testing and packaging

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=runtime/pytest-results.xml
.venv\Scripts\python.exe -m scripts.run_postman
.venv\Scripts\python.exe -m scripts.export_database
.venv\Scripts\python.exe -m scripts.package_submission
```

Newman requires Node.js and `npm install --prefix tools/postman-runner newman`. An installation is included locally under `tools/`; it is excluded from the code ZIP. Dependencies are pinned in requirements files.

## Submission scope

`submission/BrainAgeConnect_Code.zip` contains source, tests and textual documentation. `submission/BrainAgeConnect_SyntheticDatabase.zip` contains actual `mongoexport` output from the synthetic database. The real dHCP export is kept separately under `exports/local/` because the bundled dHCP terms restrict redistribution. Do not upload that export or the entire project folder indiscriminately.

Written submission materials are in `submission/PDFs/`: complete code listing, endpoint catalogue, actual Newman/pytest results, collection-derived API reference, and design/development with a recovered visible-chat appendix. The official assessment workbook is filled in `submission/CW1_Self_Evaluation_B01089181.xlsx`; its marks are provisional for the student to review. Video remains excluded. Native Postman Runner screenshots and a Postman-generated documentation printout have not been captured; the collection-derived reference is explicitly labelled. See `docs/SUBMISSION_STATUS.md` for the exact remaining actions. Postman web publication has not been performed.
