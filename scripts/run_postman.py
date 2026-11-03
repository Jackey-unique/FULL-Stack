"""Run the exported Postman collection with Newman against an isolated real MongoDB."""
import os
import shutil
import subprocess
import sys
import time
import uuid
import requests
from brainage import ROOT, create_app
from scripts.seed_demo import seed

def main():
    name = 'brainage_postman_' + uuid.uuid4().hex
    app = create_app({'MONGO_DB': name})
    seed(app.extensions['mongo_db'], 10)
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js is required to run Newman; install Node.js and ensure node is on PATH.')
    newman = ROOT / 'tools/postman-runner/node_modules/newman/bin/newman.js'
    if not newman.is_file():
        raise SystemExit('Install newman with: npm install --prefix tools/postman-runner newman')
    env = {**os.environ, 'MONGO_DB': name, 'PORT': '5051'}
    runtime = ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    log = (runtime / 'postman-api.log').open('w', encoding='utf-8')
    process = subprocess.Popen([sys.executable, 'app.py'], cwd=ROOT, env=env, stdout=log, stderr=log)
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError('Isolated API failed to start; see runtime/postman-api.log.')
            try:
                if requests.get('http://127.0.0.1:5051/api/v1/health', timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.25)
        else:
            raise RuntimeError('Isolated API did not become ready.')
        result = subprocess.run([node, str(newman), 'run', str(ROOT / 'postman/BrainAgeConnect.postman_collection.json'),
            '--env-var', 'base_url=http://127.0.0.1:5051/api/v1', '--reporters', 'cli,json',
            '--reporter-json-export', str(runtime / 'newman-results.json')], cwd=ROOT)
        if result.returncode:
            raise SystemExit(result.returncode)
    finally:
        process.terminate()
        process.wait(timeout=15)
        log.close()
        assert name.startswith('brainage_postman_')
        app.extensions['mongo_client'].drop_database(name)
        app.extensions['mongo_client'].close()

if __name__ == '__main__':
    main()
