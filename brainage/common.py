"""Shared serialization, validation, access control and optimistic writes."""
import math
import re
from datetime import datetime, timezone
from bson import ObjectId
from flask import current_app, g, jsonify, request

class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def db():
    return current_app.extensions['mongo_db']

def now():
    return datetime.now(timezone.utc)

def clean(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in ('password_hash', 'auth_version')}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value

def response(value, status=200):
    return jsonify(clean(value)), status

def oid(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-fA-F0-9]{24}', value):
        raise APIError(400, 'Invalid ObjectId: expected 24 hexadecimal characters.')
    return ObjectId(value)

def body(allowed, required=()):
    if not request.is_json:
        raise APIError(415, 'Content-Type must be application/json.')
    data = request.get_json()
    if not isinstance(data, dict):
        raise APIError(400, 'The request body must be a JSON object.')
    extra = set(data) - set(allowed)
    missing = set(required) - set(data)
    if extra:
        raise APIError(400, 'Unknown or read-only fields: ' + ', '.join(sorted(extra)))
    if missing:
        raise APIError(400, 'Missing fields: ' + ', '.join(sorted(missing)))
    return data

def string(value, name, maximum=200, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise APIError(400, f'{name} must be a string of {minimum}-{maximum} characters.')
    return value.strip()

def number(value, name, minimum, maximum, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise APIError(400, f'{name} must be a finite number between {minimum} and {maximum}.')
    return value

def choice(value, name, choices):
    if not isinstance(value, str) or value not in choices:
        raise APIError(400, f'{name} must be one of: ' + ', '.join(choices))
    return value

def boolean(value, name):
    if not isinstance(value, bool):
        raise APIError(400, f'{name} must be a JSON boolean.')
    return value

def query_args(allowed):
    if set(request.args) - set(allowed):
        raise APIError(400, 'Unknown query parameter.')
    if any(len(request.args.getlist(k)) != 1 for k in request.args):
        raise APIError(400, 'Query parameters must not be repeated.')

def pagination():
    try:
        page = int(request.args.get('page', '1'))
        size = int(request.args.get('page_size', '20'))
    except ValueError:
        raise APIError(400, 'page and page_size must be integers.')
    if not 1 <= page <= 1000000 or not 1 <= size <= 100:
        raise APIError(400, 'page must be 1-1000000; page_size must be 1-100.')
    return page, size

def page_result(items, total, page, size):
    return {'data': items, 'pagination': {'page': page, 'page_size': size,
        'total': total, 'pages': math.ceil(total / size)}}

def visibility():
    if g.user['role'] == 'admin':
        return {}
    return {'$or': [{'owner_id': g.user['_id']}, {'visibility': 'shared'}]}

def sample(sample_id, write=False):
    item = db().samples.find_one({'$and': [{'_id': oid(sample_id)}, visibility()]})
    if not item:
        raise APIError(404, 'Sample not found.')
    if write and g.user['role'] != 'admin' and item['owner_id'] != g.user['_id']:
        raise APIError(403, 'Only the sample owner or an administrator may modify this record.')
    return item

def audit(action, resource, resource_id):
    db().audit_logs.insert_one({'actor_id': g.user['_id'], 'action': action,
        'resource': resource, 'resource_id': str(resource_id), 'created_at': now()})

def update_sample(original, changes, action):
    # Compare-and-swap prevents lost updates when nested records are edited concurrently.
    result = db().samples.update_one({'_id': original['_id'], 'version': original['version']},
        {'$set': {**changes, 'updated_at': now()}, '$inc': {'version': 1}})
    if not result.matched_count:
        raise APIError(409, 'The sample changed concurrently. Fetch it again and retry.')
    audit(action, 'samples', original['_id'])
    return db().samples.find_one({'_id': original['_id']})
