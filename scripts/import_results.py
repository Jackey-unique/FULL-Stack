"""Import precomputed results via the same authenticated, validated API used by clients.

Input JSON: [{"sample_id": "24-hex-id", "result": { ... analysis fields ... }}].
Token is read from BRAINAGE_TOKEN; it is never written to disk or logs.
No MRI inference or model training occurs here. Duplicate imports create new history entries.
"""
import argparse
import json
import os
import requests

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file')
    parser.add_argument('--base-url', default='http://127.0.0.1:5000/api/v1')
    args = parser.parse_args()
    token = os.environ.get('BRAINAGE_TOKEN')
    if not token:
        raise SystemExit('Set BRAINAGE_TOKEN to a current authenticated session token.')
    with open(args.file, encoding='utf-8') as handle:
        items = json.load(handle)
    if not isinstance(items, list):
        raise SystemExit('Input must be a JSON array.')
    success = 0
    for index, item in enumerate(items):
        response = requests.post(args.base_url + '/samples/' + item['sample_id'] + '/analyses',
            json=item['result'], headers={'Authorization': 'Bearer ' + token}, timeout=30)
        if response.status_code != 201:
            raise SystemExit(f'Row {index+1} failed ({response.status_code}): {response.text}. {success} earlier rows were imported.')
        success += 1
    print(f'Imported {success} precomputed results.')

if __name__ == '__main__':
    main()
