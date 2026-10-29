"""Read local BIDS metadata without moving MRI files or fabricating results.

Idempotent inserts: existing samples are never replaced. Use --refresh-files to refresh
only detected file inventories/availability. User edits, notes and analyses survive reruns.
"""
import argparse
import csv
import json
import math
from pathlib import Path
from bson import ObjectId
from brainage import ROOT, create_app
from brainage.common import now

def rows(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))

def numeric(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def inventory(root, subject, session, modality):
    base = root / ('sub-' + subject) / ('ses-' + session)
    files = []
    available = False
    for path in sorted(base.rglob('*')) if base.exists() else []:
        if not path.is_file():
            continue
        size = path.stat().st_size
        primary = path.name.endswith('_desc-preproc_dwi.nii.gz') if modality == 'dmri' else path.name.endswith('_task-rest_desc-preproc_bold.nii.gz')
        # Detect obvious LFS stubs and empty files. This is NOT full MRI quality control.
        signature_ok = False
        if primary and size > 1024:
            with path.open('rb') as handle:
                signature_ok = handle.read(2) == b'\x1f\x8b'
        available = available or signature_ok
        files.append({'_id': ObjectId(), 'modality': modality, 'relative_path': path.relative_to(root).as_posix(),
            'size_bytes': size, 'primary_image': primary, 'gzip_signature_valid': signature_ok if primary else None})
    return files, available

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dmri', type=Path, default=Path.home() / 'Desktop/dhcp_dmri_pipeline')
    parser.add_argument('--fmri', type=Path, default=Path.home() / 'Desktop/dhcp_fmri_pipeline')
    parser.add_argument('--refresh-files', action='store_true')
    args = parser.parse_args()
    app = create_app()
    db = app.extensions['mongo_db']
    admin = db.users.find_one({'role': 'admin', 'active': True})
    if not admin:
        raise SystemExit('Run python -m scripts.bootstrap first.')
    merged, descriptions, conflicts = {}, {}, []
    for modality, root in [('dmri', args.dmri), ('fmri', args.fmri)]:
        if not (root / 'participants.tsv').is_file():
            raise SystemExit(f'Missing participants.tsv: {root}')
        descriptions[modality] = json.loads((root / 'dataset_description.json').read_text(encoding='utf-8'))
        participants = {r['participant_id'].removeprefix('sub-'): r for r in rows(root / 'participants.tsv')}
        for subject_dir in sorted(root.glob('sub-*')):
            if not subject_dir.is_dir():
                continue
            subject = subject_dir.name.removeprefix('sub-')
            participant = participants.get(subject, {})
            for session_row in rows(subject_dir / (subject_dir.name + '_sessions.tsv')):
                session = session_row['session_id'].removeprefix('ses-')
                code = f'sub-{subject}_ses-{session}'
                age = numeric(session_row.get('scan_age'))
                birth = numeric(participant.get('birth_age'))
                if age is not None and not 20 <= age <= 80:
                    conflicts.append({'sample_code': code, 'field': 'scan_age_out_of_range', 'value': age}); age = None
                if birth is not None and (not 20 <= birth <= 45 or (age is not None and birth > age)):
                    conflicts.append({'sample_code': code, 'field': 'birth_age_invalid', 'value': birth}); birth = None
                if code not in merged:
                    merged[code] = {'sample_code': code, 'subject_code': subject, 'session_code': session,
                        'age_at_scan_weeks': age, 'birth_age_weeks': birth,
                        'sex': participant.get('gender') if participant.get('gender') in ('Male', 'Female') else 'Unknown',
                        'has_dmri': False, 'has_fmri': False, 'metadata_modalities': [], 'files': [], 'source_metadata': {}}
                item = merged[code]
                if age is not None and item['age_at_scan_weeks'] is not None and abs(age - item['age_at_scan_weeks']) > 0.00001:
                    conflicts.append({'sample_code': code, 'field': 'scan_age_conflict', 'values': [item['age_at_scan_weeks'], age]})
                    item['age_at_scan_weeks'] = None
                files, available = inventory(root, subject, session, modality)
                item['files'].extend(files)
                item['has_' + modality] = available
                item['metadata_modalities'].append(modality)
                item['source_metadata'][modality] = {'participant': participant, 'session': session_row}
    inserted = refreshed = skipped = 0
    for item in merged.values():
        existing = db.samples.find_one({'sample_code': item['sample_code']})
        if existing:
            if args.refresh_files:
                result = db.samples.update_one({'_id': existing['_id'], 'source': 'dhcp_local', 'version': existing['version']},
                    {'$set': {**{k: item[k] for k in ('files', 'has_dmri', 'has_fmri', 'metadata_modalities')}, 'updated_at': now()}, '$inc': {'version': 1}})
                refreshed += result.modified_count
            else:
                skipped += 1
            continue
        note = {'_id': ObjectId(), 'author_id': admin['_id'], 'category': 'quality',
            'text': 'Importer observation: metadata available for ' + ', '.join(item['metadata_modalities']) +
            '. File presence is not a quality assessment. No developmental age has been inferred.',
            'created_at': now(), 'updated_at': now()}
        item.update(_id=ObjectId(), owner_id=admin['_id'], source='dhcp_local', visibility='private',
            status='ready' if item['has_dmri'] or item['has_fmri'] else 'registered',
            description='Local dHCP research metadata; postmenstrual age in weeks.',
            notes=[note], analyses=[], created_at=now(), updated_at=now(), version=1)
        db.samples.insert_one(item)
        inserted += 1
    report = {'imported_at': now().isoformat(), 'discovered_sessions': len(merged),
        'inserted': inserted, 'refreshed': refreshed, 'skipped': skipped,
        'dmri_images_present': sum(x['has_dmri'] for x in merged.values()),
        'fmri_images_present': sum(x['has_fmri'] for x in merged.values()),
        'both_images_present': sum(x['has_dmri'] and x['has_fmri'] for x in merged.values()),
        'metadata_in_both': sum(len(x['metadata_modalities']) == 2 for x in merged.values()),
        'files_indexed': sum(len(x['files']) for x in merged.values()),
        'conflicts': conflicts, 'dataset_descriptions': descriptions,
        'note': 'Presence check only: size and gzip magic; no decompression, scan QC or brain-age inference performed.'}
    private = ROOT / 'data/private'
    private.mkdir(parents=True, exist_ok=True)
    (private / 'import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (private / 'source_paths.json').write_text(json.dumps({'dmri': str(args.dmri.resolve()), 'fmri': str(args.fmri.resolve())}, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('conflicts', 'dataset_descriptions')}, indent=2))

if __name__ == '__main__':
    main()
