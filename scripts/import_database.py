"""Restore exported collections into an empty database; never delete existing data."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from brainage import ROOT, create_app, ensure_indexes
from scripts.export_database import COLLECTIONS

def restore_export(client, uri, database_name, directory):
    database = client[database_name]
    if any(database[name].count_documents({}) for name in database.list_collection_names()):
        raise RuntimeError('Target database is not empty; choose a new name. No data have been deleted.')
    executable = shutil.which('mongoimport') or next((str(p) for p in (ROOT / 'tools').rglob('mongoimport.exe')), None)
    if not executable:
        raise RuntimeError('MongoDB Database Tools (mongoimport) are required.')
    prepared = []
    for name in COLLECTIONS:
        path = Path(directory) / (name + '.json')
        records = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(records, list):
            raise ValueError(f'{path.name} must contain a JSON array.')
        prepared.append((name, path, len(records)))
    counts = {}
    for name, path, length in prepared:
        if length:
            subprocess.run([executable, '--uri', uri, '--db', database_name,
                '--collection', name, '--jsonArray', '--file', str(path)], check=True)
        elif name not in database.list_collection_names():
            # mongoimport rejects an empty JSON array; create its empty collection explicitly.
            database.create_collection(name)
        counts[name] = database[name].count_documents({})
        if counts[name] != length:
            raise RuntimeError(f'Import count mismatch for {name}.')
    ensure_indexes(database)
    return counts

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='brainage_restored')
    parser.add_argument('--input', type=Path, default=ROOT / 'exports/demo')
    args = parser.parse_args()
    app = create_app()
    print(restore_export(app.extensions['mongo_client'], app.config['MONGO_URI'], args.database, args.input))
    print('Set MONGO_DB in .env to the restored name to serve this database.')

if __name__ == '__main__':
    main()
