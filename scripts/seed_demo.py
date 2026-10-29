"""Seed a SEPARATE fully synthetic, reproducible database for sharing/testing."""
import argparse
import random
from bson import ObjectId
from brainage import create_app
from brainage.auth import hash_password
from brainage.common import now

def seed(db, count=150):
    if db.samples.count_documents({}) or db.users.count_documents({}):
        raise RuntimeError('Demo database is not empty; refusing to overwrite it.')
    admin = {'_id': ObjectId(), 'username': 'demo.admin', 'password_hash': hash_password('DemoAdmin!2026'),
        'display_name': 'Synthetic Demo Administrator', 'role': 'admin', 'active': True, 'auth_version': 0, 'created_at': now()}
    researcher = {'_id': ObjectId(), 'username': 'demo.researcher', 'password_hash': hash_password('DemoResearch!2026'),
        'display_name': 'Synthetic Demo Researcher', 'role': 'researcher', 'active': True, 'auth_version': 0, 'created_at': now()}
    db.users.insert_many([admin, researcher])
    rng = random.Random(661)
    items = []
    for i in range(count):
        age = round(rng.uniform(28, 45), 4)
        dmri, fmri = i % 5 != 0, i % 4 != 0
        analyses = []
        for mode, present in [('dmri', dmri), ('fmri', fmri)]:
            if present:
                estimate = round(age + rng.uniform(-2, 2), 4)
                analyses.append({'_id': ObjectId(), 'author_id': researcher['_id'], 'modality': mode,
                    'estimated_age_weeks': estimate, 'age_difference_weeks': round(estimate-age, 6),
                    'method': 'Synthetic fixture: reference age plus random offset', 'model_version': 'fixture-v1',
                    'provenance': 'Entirely invented for software testing. Not an MRI-derived estimate.',
                    'quality_score': None, 'result_type': 'synthetic_demonstration', 'created_at': now(), 'updated_at': now()})
        items.append({'_id': ObjectId(), 'sample_code': f'DEMO-{i+1:04}', 'owner_id': researcher['_id'],
            'age_at_scan_weeks': age, 'birth_age_weeks': round(min(age, rng.uniform(25, 40)), 4),
            'sex': rng.choice(['Female', 'Male']), 'has_dmri': dmri, 'has_fmri': fmri,
            'visibility': 'shared', 'status': 'completed' if analyses else 'registered', 'source': 'synthetic',
            'description': 'Synthetic coursework fixture. No real person or image.', 'files': [],
            'notes': [{'_id': ObjectId(), 'author_id': researcher['_id'], 'text': 'Synthetic demonstration note.',
                'category': 'research', 'created_at': now(), 'updated_at': now()}],
            'analyses': analyses, 'created_at': now(), 'updated_at': now(), 'version': 1})
    db.samples.insert_many(items)
    return {'samples': len(items), 'analyses': sum(len(x['analyses']) for x in items)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='brainage_demo')
    args = parser.parse_args()
    if not args.database.startswith('brainage_demo'):
        raise SystemExit('Demo database name must start with brainage_demo.')
    app = create_app({'MONGO_DB': args.database})
    print(seed(app.extensions['mongo_db']))

if __name__ == '__main__':
    main()
