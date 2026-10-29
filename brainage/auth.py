"""JWT authentication, bcrypt password hashing, logout revocation and account checks."""
from datetime import timedelta, datetime, timezone
from functools import wraps
from uuid import uuid4
import re
import bcrypt
import jwt
from flask import Blueprint, current_app, g, request
from .common import APIError, audit, body, db, now, oid, response, string

bp = Blueprint('auth', __name__)

def password(value):
    # bcrypt accepts at most 72 bytes, not 72 Unicode characters.
    if not isinstance(value, str) or len(value) < 10 or len(value.encode('utf-8')) > 72:
        raise APIError(400, 'Password must have at least 10 characters and at most 72 UTF-8 bytes.')
    return value

def hash_password(value):
    return bcrypt.hashpw(password(value).encode(), bcrypt.gensalt()).decode()

def username(value):
    value = string(value, 'username', 40, 3).lower()
    if not re.fullmatch(r'[a-z0-9_.-]+', value):
        raise APIError(400, 'username may contain letters, numbers, _, . and - only.')
    return value

def auth_required(admin=False):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            header = request.headers.get('Authorization', '')
            if not header.startswith('Bearer '):
                raise APIError(401, 'A Bearer token is required.')
            try:
                claims = jwt.decode(header[7:], current_app.config['JWT_SECRET'], algorithms=['HS256'],
                    issuer='brainage-connect', audience='brainage-api',
                    options={'require': ['exp', 'iat', 'sub', 'jti', 'ver']})
                user_id = oid(claims['sub'])
            except (jwt.PyJWTError, APIError, TypeError, KeyError):
                raise APIError(401, 'Invalid or expired token.')
            user = db().users.find_one({'_id': user_id, 'active': True})
            if not user or user['auth_version'] != claims['ver'] or db().revoked_tokens.find_one({'jti': claims['jti']}):
                raise APIError(401, 'Session is no longer valid. Please log in again.')
            if admin and user['role'] != 'admin':
                raise APIError(403, 'Administrator access is required.')
            g.user, g.claims = user, claims
            return fn(*args, **kwargs)
        return wrapped
    return decorate

@bp.post('/auth/register')
def register():
    """New registrations are inactive until an administrator approves access."""
    data = body({'username', 'password', 'display_name'}, {'username', 'password', 'display_name'})
    user = {'username': username(data['username']), 'password_hash': hash_password(data['password']),
        'display_name': string(data['display_name'], 'display_name', 80), 'role': 'researcher',
        'active': False, 'auth_version': 0, 'created_at': now()}
    db().users.insert_one(user)
    return response({'data': user, 'message': 'Account created. Administrator approval is required.'}, 201)

@bp.post('/auth/login')
def login():
    data = body({'username', 'password'}, {'username', 'password'})
    name, secret = username(data['username']), password(data['password'])
    user = db().users.find_one({'username': name})
    if not user or not bcrypt.checkpw(secret.encode(), user['password_hash'].encode()):
        raise APIError(401, 'Invalid credentials.')
    if not user['active']:
        raise APIError(403, 'Account is inactive or awaiting administrator approval.')
    timestamp = now()
    token = jwt.encode({'sub': str(user['_id']), 'jti': str(uuid4()), 'iat': timestamp,
        'exp': timestamp + timedelta(seconds=current_app.config['TOKEN_SECONDS']),
        'iss': 'brainage-connect', 'aud': 'brainage-api', 'ver': user['auth_version']},
        current_app.config['JWT_SECRET'], algorithm='HS256')
    return response({'access_token': token, 'token_type': 'Bearer',
        'expires_in': current_app.config['TOKEN_SECONDS'], 'user': user})

@bp.post('/auth/logout')
@auth_required()
def logout():
    db().revoked_tokens.update_one({'jti': g.claims['jti']}, {'$set': {
        'expires_at': datetime.fromtimestamp(g.claims['exp'], timezone.utc)}}, upsert=True)
    return '', 204

@bp.get('/auth/me')
@auth_required()
def me():
    return response({'data': g.user})

@bp.put('/auth/password')
@auth_required()
def change_password():
    data = body({'current_password', 'new_password'}, {'current_password', 'new_password'})
    old = password(data['current_password'])
    if not bcrypt.checkpw(old.encode(), g.user['password_hash'].encode()):
        raise APIError(401, 'Current password is incorrect.')
    db().users.update_one({'_id': g.user['_id']}, {'$set': {'password_hash': hash_password(data['new_password'])},
        '$inc': {'auth_version': 1}})
    audit('password_changed', 'users', g.user['_id'])
    return response({'message': 'Password changed. All existing sessions are now invalid.'})
