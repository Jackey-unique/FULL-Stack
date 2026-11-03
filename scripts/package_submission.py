"""Build code and synthetic-data ZIPs. Never bundle local dHCP data or secrets."""
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED
from brainage import ROOT, create_app

def main():
    target = ROOT / 'submission'
    target.mkdir(exist_ok=True)
    app = create_app({'MONGO_DB': 'brainage_demo'})
    database = app.extensions['mongo_db']
    if not database.samples.count_documents({}) or database.samples.count_documents({'source': {'$ne': 'synthetic'}}):
        raise SystemExit('Submission dataset must be a nonempty, exclusively synthetic database.')
    subprocess.run([sys.executable, '-m', 'scripts.export_database', '--database', 'brainage_demo',
        '--output', 'exports/demo'], check=True, cwd=ROOT)
    include_dirs = ['brainage', 'scripts', 'tests', 'postman', 'static']
    include_files = ['app.py', 'requirements.txt', 'requirements-dev.txt', '.env.example', '.gitignore',
        'README.md', '开始使用.md', 'START_PROJECT.cmd', 'START_DEMO.cmd', 'STOP_PROJECT.cmd', 'RUN_TESTS.cmd', 'setup.ps1', 'start.ps1',
        'stop.ps1', 'docs/API.md', 'docs/DESIGN_AND_AI.md', 'docs/DATA.md', 'docs/openapi.json',
        'docs/TEST_REPORT.md', 'docs/REQUIREMENTS_MAPPING.md', 'docs/SUBMISSION_DESIGN.md',
        'docs/SUBMISSION_STATUS.md', 'docs/FINAL_AUDIT_2026-11-02.md',
        'docs/POSTMAN_PUBLIC_DOCUMENTATION_URL.txt', '项目交接文档.md']
    with ZipFile(target / 'BrainAgeConnect_Code.zip', 'w', ZIP_DEFLATED) as archive:
        for directory in include_dirs:
            for path in (ROOT / directory).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    archive.write(path, path.relative_to(ROOT))
        for name in include_files:
            path = ROOT / name
            if path.is_file():
                archive.write(path, name)
    with ZipFile(target / 'BrainAgeConnect_SyntheticDatabase.zip', 'w', ZIP_DEFLATED) as archive:
        for path in (ROOT / 'exports/demo').glob('*.json'):
            archive.write(path, path.name)
    print('Created code ZIP and synthetic database ZIP in submission/.')

if __name__ == '__main__':
    main()
