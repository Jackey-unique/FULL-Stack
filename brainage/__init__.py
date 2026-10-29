"""Application factory. Database handles belong to the application, not global imports."""
import os
from pathlib import Path
from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.exceptions import HTTPException
from .common import APIError

ROOT = Path(__file__).resolve().parent.parent

def ensure_indexes(database):
    database.users.create_index('username', unique=True)
    database.samples.create_index('sample_code', unique=True)
    database.samples.create_index([('owner_id', 1), ('age_at_scan_weeks', 1)])
    database.samples.create_index([('visibility', 1), ('status', 1), ('sample_code', 1)])
    database.samples.create_index([('source', 1), ('age_at_scan_weeks', 1)])
    database.revoked_tokens.create_index('jti', unique=True)
    database.revoked_tokens.create_index('expires_at', expireAfterSeconds=0)
    database.audit_logs.create_index('created_at')

def create_app(config=None):
    load_dotenv(ROOT / '.env')
    app = Flask(__name__, static_folder=str(ROOT / 'static'))
    app.config.update(MONGO_URI=os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27018'),
        MONGO_DB=os.getenv('MONGO_DB', 'brainage_connect'), JWT_SECRET=os.getenv('JWT_SECRET'),
        MAX_CONTENT_LENGTH=1024 * 1024, TOKEN_SECONDS=3600, TESTING=False)
    if config:
        app.config.update(config)
    if not app.config['JWT_SECRET'] or len(app.config['JWT_SECRET']) < 32 or app.config['JWT_SECRET'].startswith('replace-'):
        raise RuntimeError('Set a random JWT_SECRET of at least 32 characters in .env.')
    client = MongoClient(app.config['MONGO_URI'], serverSelectionTimeoutMS=5000, tz_aware=True)
    app.extensions['mongo_client'] = client
    app.extensions['mongo_db'] = client[app.config['MONGO_DB']]
    client.admin.command('ping')
    ensure_indexes(app.extensions['mongo_db'])
    CORS(app, resources={r'/api/*': {'origins': os.getenv('CORS_ORIGINS', 'http://localhost:4200,http://127.0.0.1:4200').split(',')}})
    from .auth import bp as auth_bp
    from .samples import bp as samples_bp
    from .analytics import bp as analytics_bp
    from .admin import bp as admin_bp
    for bp in (auth_bp, samples_bp, analytics_bp, admin_bp):
        app.register_blueprint(bp, url_prefix='/api/v1')

    @app.get('/api/v1/health')
    def health():
        client.admin.command('ping')
        return {'status': 'ok', 'application': 'BrainAge Connect', 'version': '1.0.0'}

    @app.get('/')
    def home():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/api/v1/openapi.json')
    def openapi():
        return send_from_directory(str(ROOT / 'docs'), 'openapi.json')

    @app.errorhandler(APIError)
    def api_error(exc):
        return jsonify(error={'status': exc.status, 'message': exc.message}), exc.status

    @app.errorhandler(DuplicateKeyError)
    def duplicate(exc):
        return jsonify(error={'status': 409, 'message': 'A record with that unique value already exists.'}), 409

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return jsonify(error={'status': exc.code, 'message': exc.description}), exc.code

    @app.errorhandler(PyMongoError)
    def database_error(exc):
        app.logger.exception('Database operation failed')
        return jsonify(error={'status': 503, 'message': 'Database temporarily unavailable.'}), 503

    @app.errorhandler(Exception)
    def internal_error(exc):
        app.logger.exception('Unexpected request error')
        return jsonify(error={'status': 500, 'message': 'Internal server error.'}), 500

    @app.after_request
    def headers(result):
        result.headers['X-Content-Type-Options'] = 'nosniff'
        result.headers['X-Frame-Options'] = 'DENY'
        result.headers['Cache-Control'] = 'no-store'
        return result
    return app
