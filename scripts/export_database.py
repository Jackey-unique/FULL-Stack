"""Export actual MongoDB collections with mongoexport (Canonical Extended JSON)."""
import argparse
import shutil
import subprocess
from pathlib import Path
from brainage import ROOT, create_app

COLLECTIONS = ('samples', 'users', 'audit_logs', 'revoked_tokens')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='brainage_connect')
    parser.add_argument('--output', default='exports/local')
    args = parser.parse_args()
    app = create_app({'MONGO_DB': args.database})
    executable = shutil.which('mongoexport') or next((str(x) for x in (ROOT / 'tools').rglob('mongoexport.exe')), None)
    if not executable:
        raise SystemExit('Install MongoDB Database Tools or place them under tools/.')
    target = (ROOT / args.output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    for collection in COLLECTIONS:
        subprocess.run([executable, '--uri', app.config['MONGO_URI'], '--db', args.database,
            '--collection', collection, '--jsonArray', '--jsonFormat=canonical', '--pretty',
            '--out', str(target / (collection + '.json'))], check=True)
    print('Exported actual database collections to', target)

if __name__ == '__main__':
    main()
