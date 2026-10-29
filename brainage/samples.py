"""Sample and embedded analysis/note resources; all reads enforce visibility."""
import re
from bson import ObjectId
from flask import Blueprint, g, request
from .auth import auth_required
from .common import (APIError, audit, body, boolean, choice, db, now, number, oid,
    page_result, pagination, query_args, response, sample, string, update_sample, visibility)

bp = Blueprint('samples', __name__)
SAMPLE_FIELDS = {'sample_code', 'age_at_scan_weeks', 'birth_age_weeks', 'sex',
    'has_dmri', 'has_fmri', 'status', 'visibility', 'description'}
FILTERS = {'q', 'age_min', 'age_max', 'modality', 'status', 'source', 'sex'}

def validate_sample(data, old=None):
    result = dict(data)
    for key in ('sample_code', 'description'):
        if key in result:
            result[key] = string(result[key], key, 120 if key == 'sample_code' else 2000, 1 if key == 'sample_code' else 0)
    if 'sample_code' in result and not re.fullmatch(r'[A-Za-z0-9_.-]+', result['sample_code']):
        raise APIError(400, 'sample_code may contain letters, numbers, _, . and - only.')
    for key, low, high in [('age_at_scan_weeks', 20, 80), ('birth_age_weeks', 20, 45)]:
        if key in result:
            result[key] = number(result[key], key, low, high, nullable=True)
    for key in ('has_dmri', 'has_fmri'):
        if key in result:
            result[key] = boolean(result[key], key)
    for key, options in [('sex', ('Female', 'Male', 'Unknown')),
        ('status', ('registered', 'ready', 'processing', 'completed', 'failed')),
        ('visibility', ('private', 'shared'))]:
        if key in result:
            result[key] = choice(result[key], key, options)
    combined = {**(old or {}), **result}
    birth, scan = combined.get('birth_age_weeks'), combined.get('age_at_scan_weeks')
    if birth is not None and scan is not None and birth > scan:
        raise APIError(400, 'birth_age_weeks cannot exceed age_at_scan_weeks.')
    if old and old.get('source') == 'dhcp_local' and any(k in data for k in ('sample_code', 'has_dmri', 'has_fmri')):
        raise APIError(400, 'Imported sample identity and local file availability are managed by the importer.')
    if old:
        for analysis_entry in old.get('analyses', []):
            mode = analysis_entry['modality']
            if ((mode in ('dmri', 'combined') and not combined.get('has_dmri')) or
                (mode in ('fmri', 'combined') and not combined.get('has_fmri'))):
                raise APIError(409, 'Remove dependent analyses before disabling a modality.')
    return result

def filters():
    clauses = [visibility()]
    if 'q' in request.args:
        term = string(request.args['q'], 'q', 120)
        clauses.append({'sample_code': {'$regex': re.escape(term), '$options': 'i'}})
    limits = {}
    for name, operator in [('age_min', '$gte'), ('age_max', '$lte')]:
        if name in request.args:
            try:
                value = float(request.args[name])
            except ValueError:
                raise APIError(400, name + ' must be numeric.')
            limits[operator] = number(value, name, 20, 80)
    if limits:
        if limits.get('$gte', 20) > limits.get('$lte', 80):
            raise APIError(400, 'age_min must not exceed age_max.')
        clauses.append({'age_at_scan_weeks': limits})
    for name, options in [('status', ('registered', 'ready', 'processing', 'completed', 'failed')),
        ('source', ('dhcp_local', 'manual', 'synthetic')), ('sex', ('Female', 'Male', 'Unknown'))]:
        if name in request.args:
            clauses.append({name: choice(request.args[name], name, options)})
    if 'modality' in request.args:
        mode = choice(request.args['modality'], 'modality', ('dmri', 'fmri', 'both', 'neither'))
        clauses.append({'dmri': {'has_dmri': True}, 'fmri': {'has_fmri': True},
            'both': {'has_dmri': True, 'has_fmri': True}, 'neither': {'has_dmri': False, 'has_fmri': False}}[mode])
    return {'$and': clauses}

def sort_order(allowed, default):
    key = choice(request.args.get('sort', default), 'sort', allowed)
    order = choice(request.args.get('order', 'asc'), 'order', ('asc', 'desc'))
    return key, 1 if order == 'asc' else -1

@bp.get('/samples')
@auth_required()
def list_samples():
    query_args(FILTERS | {'page', 'page_size', 'sort', 'order'})
    page, size = pagination()
    key, direction = sort_order(('sample_code', 'age_at_scan_weeks', 'created_at', 'updated_at'), 'sample_code')
    query = filters()
    projection = {'notes': 0, 'analyses': 0, 'files': 0, 'source_metadata': 0}
    items = list(db().samples.find(query, projection).sort([(key, direction), ('_id', 1)]).skip((page - 1) * size).limit(size))
    return response(page_result(items, db().samples.count_documents(query), page, size))

@bp.post('/samples')
@auth_required()
def create_sample():
    data = validate_sample(body(SAMPLE_FIELDS, {'sample_code', 'age_at_scan_weeks'}))
    item = {'_id': ObjectId(), 'owner_id': g.user['_id'], 'source': 'manual', 'visibility': 'private',
        'sex': 'Unknown', 'birth_age_weeks': None, 'has_dmri': False, 'has_fmri': False,
        'status': 'registered', 'description': '', 'notes': [], 'analyses': [], 'files': [],
        'created_at': now(), 'updated_at': now(), 'version': 1, **data}
    db().samples.insert_one(item)
    audit('created', 'samples', item['_id'])
    return response({'data': item}, 201)

@bp.get('/samples/<sample_id>')
@auth_required()
def get_sample(sample_id):
    return response({'data': sample(sample_id)})

@bp.route('/samples/<sample_id>', methods=['PUT', 'PATCH'])
@auth_required()
def edit_sample(sample_id):
    original = sample(sample_id, write=True)
    data = body(SAMPLE_FIELDS)
    if not data:
        raise APIError(400, 'At least one editable field is required.')
    changes = validate_sample(data, original)
    # Recompute differences if the reference age changes; never leave stale derived values.
    if 'age_at_scan_weeks' in changes:
        analyses = original['analyses']
        for result in analyses:
            result['age_difference_weeks'] = difference(result['estimated_age_weeks'], changes['age_at_scan_weeks'])
        changes['analyses'] = analyses
    return response({'data': update_sample(original, changes, 'updated')})

@bp.delete('/samples/<sample_id>')
@auth_required()
def delete_sample(sample_id):
    original = sample(sample_id, write=True)
    result = db().samples.delete_one({'_id': original['_id'], 'version': original['version']})
    if not result.deleted_count:
        raise APIError(409, 'The sample changed concurrently. Retry after fetching it.')
    audit('deleted', 'samples', original['_id'])
    return '', 204

def difference(estimate, age):
    return None if age is None else round(estimate - age, 6)

ANALYSIS_FIELDS = {'modality', 'estimated_age_weeks', 'method', 'model_version', 'provenance', 'quality_score'}
NOTE_FIELDS = {'text', 'category'}

def validate_child(kind, data, parent, original=None):
    merged = {**(original or {}), **data}
    if kind == 'notes':
        merged['text'] = string(merged.get('text'), 'text', 4000)
        merged['category'] = choice(merged.get('category', 'research'), 'category', ('research', 'quality', 'review'))
    else:
        merged['modality'] = choice(merged.get('modality'), 'modality', ('dmri', 'fmri', 'combined'))
        mode = merged['modality']
        if ((mode in ('dmri', 'combined') and not parent['has_dmri']) or
            (mode in ('fmri', 'combined') and not parent['has_fmri'])):
            raise APIError(400, 'The requested modality is not available for this sample.')
        merged['estimated_age_weeks'] = number(merged.get('estimated_age_weeks'), 'estimated_age_weeks', 20, 80)
        for key in ('method', 'model_version', 'provenance'):
            merged[key] = string(merged.get(key), key, 1000 if key == 'provenance' else 120)
        merged['quality_score'] = number(merged.get('quality_score'), 'quality_score', 0, 1, nullable=True)
        merged['age_difference_weeks'] = difference(merged['estimated_age_weeks'], parent['age_at_scan_weeks'])
        merged['result_type'] = 'synthetic_demonstration' if parent['source'] == 'synthetic' else 'user_supplied_precomputed'
    return merged

def child_owner(item):
    if g.user['role'] != 'admin' and item['author_id'] != g.user['_id']:
        raise APIError(403, 'Only the author or an administrator may modify this entry.')

# The same resource workflow is used for both independently named embedded collections.
def register_children(kind):
    path = '/samples/<sample_id>/' + kind
    allowed = NOTE_FIELDS if kind == 'notes' else ANALYSIS_FIELDS
    required = {'text'} if kind == 'notes' else ANALYSIS_FIELDS - {'quality_score'}

    @auth_required()
    def listing(sample_id):
        query_args({'page', 'page_size', 'sort', 'order'})
        parent = sample(sample_id)
        page, size = pagination()
        key, direction = sort_order(('created_at', 'updated_at'), 'created_at')
        entries = sorted(parent[kind], key=lambda x: (x[key], str(x['_id'])), reverse=direction == -1)
        return response(page_result(entries[(page-1)*size:page*size], len(entries), page, size))

    @auth_required()
    def create(sample_id):
        parent = sample(sample_id)
        data = body(allowed, required)
        if len(parent[kind]) >= 200:
            raise APIError(409, 'This sample already has the maximum of 200 entries in this collection.')
        entry = validate_child(kind, data, parent)
        entry.update(_id=ObjectId(), author_id=g.user['_id'], created_at=now(), updated_at=now())
        update_sample(parent, {kind: parent[kind] + [entry]}, kind + '_created')
        return response({'data': entry}, 201)

    @auth_required()
    def detail(sample_id, child_id):
        parent = sample(sample_id)
        identifier = oid(child_id)
        entry = next((x for x in parent[kind] if x['_id'] == identifier), None)
        if not entry:
            raise APIError(404, 'Entry not found.')
        if request.method == 'GET':
            return response({'data': entry})
        child_owner(entry)
        if request.method == 'DELETE':
            entries = [x for x in parent[kind] if x['_id'] != identifier]
            update_sample(parent, {kind: entries}, kind + '_deleted')
            return '', 204
        data = body(allowed)
        if not data:
            raise APIError(400, 'At least one editable field is required.')
        updated = validate_child(kind, data, parent, entry)
        updated['updated_at'] = now()
        entries = [updated if x['_id'] == identifier else x for x in parent[kind]]
        update_sample(parent, {kind: entries}, kind + '_updated')
        return response({'data': updated})

    bp.add_url_rule(path, kind + '_list', listing, methods=['GET'])
    bp.add_url_rule(path, kind + '_create', create, methods=['POST'])
    bp.add_url_rule(path + '/<child_id>', kind + '_detail', detail, methods=['GET', 'PUT', 'PATCH', 'DELETE'])

register_children('notes')
register_children('analyses')
