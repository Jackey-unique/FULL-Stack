"""Administrator-only accounts and audit history."""
from flask import Blueprint, g, request
from .auth import auth_required
from .common import APIError, audit, body, boolean, choice, db, oid, page_result, pagination, query_args, response

bp = Blueprint('admin', __name__)

@bp.get('/users')
@auth_required(admin=True)
def users():
    query_args({'page', 'page_size'})
    page, size = pagination()
    rows = list(db().users.find().sort('_id', 1).skip((page-1)*size).limit(size))
    return response(page_result(rows, db().users.count_documents({}), page, size))

@bp.get('/users/<user_id>')
@auth_required(admin=True)
def user_detail(user_id):
    user = db().users.find_one({'_id': oid(user_id)})
    if not user:
        raise APIError(404, 'User not found.')
    return response({'data': user})

@bp.route('/users/<user_id>', methods=['PUT', 'PATCH'])
@auth_required(admin=True)
def update_user(user_id):
    identifier = oid(user_id)
    if identifier == g.user['_id']:
        raise APIError(409, 'Administrators cannot change their own role or activation state.')
    data = body({'role', 'active'})
    if not data:
        raise APIError(400, 'Provide role or active.')
    if 'role' in data:
        choice(data['role'], 'role', ('admin', 'researcher'))
    if 'active' in data:
        boolean(data['active'], 'active')
    result = db().users.update_one({'_id': identifier}, {'$set': data, '$inc': {'auth_version': 1}})
    if not result.matched_count:
        raise APIError(404, 'User not found.')
    audit('permissions_updated', 'users', identifier)
    return response({'data': db().users.find_one({'_id': identifier})})

@bp.get('/audit-logs')
@auth_required(admin=True)
def audit_logs():
    query_args({'page', 'page_size'})
    page, size = pagination()
    rows = list(db().audit_logs.find().sort([('created_at', -1), ('_id', -1)]).skip((page-1)*size).limit(size))
    return response(page_result(rows, db().audit_logs.count_documents({}), page, size))
