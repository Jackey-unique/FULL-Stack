"""Verify a synthetic mongoexport/mongoimport round trip in a disposable database."""
import json
import subprocess
import uuid
from bson import ObjectId
from datetime import datetime
from brainage import ROOT, create_app
from scripts.import_database import restore_export

def main():
    app = create_app()
    client = app.extensions['mongo_client']
    name = 'brainage_roundtrip_' + uuid.uuid4().hex
    target = client[name]
    try:
        counts = restore_export(client, app.config['MONGO_URI'], name, ROOT / 'exports/demo')
        assert counts['samples'] == 150
        sample = target.samples.find_one()
        assert isinstance(sample['_id'], ObjectId)
        assert isinstance(sample['created_at'], datetime)
        assert isinstance(sample['notes'][0]['_id'], ObjectId)
        assert target.samples.count_documents({'source': {'$ne': 'synthetic'}}) == 0
        report = {'status': 'passed', 'counts': counts,
            'objectid_and_datetime_types_preserved': True,
            'note': 'Actual mongoexport output imported into an isolated real MongoDB database.'}
        (ROOT / 'runtime/export-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        assert name.startswith('brainage_roundtrip_')
        client.drop_database(name)

if __name__ == '__main__':
    main()
