"""Create local configuration and a single administrator without overwriting existing secrets."""
import secrets
from brainage import ROOT, create_app
from brainage.auth import hash_password
from brainage.common import now

def main():
    path = ROOT / '.env'
    if not path.exists():
        path.write_text('MONGO_URI=mongodb://127.0.0.1:27018\nMONGO_DB=brainage_connect\nJWT_SECRET=' +
            secrets.token_urlsafe(48) + '\nPORT=5000\n', encoding='utf-8')
    app = create_app()
    db = app.extensions['mongo_db']
    if not db.users.find_one({'role': 'admin', 'active': True}):
        secret = secrets.token_urlsafe(15)
        db.users.insert_one({'username': 'admin', 'password_hash': hash_password(secret),
            'display_name': 'Project Administrator', 'role': 'admin', 'active': True,
            'auth_version': 0, 'created_at': now()})
        (ROOT / 'docs' / 'LOCAL_ACCESS.txt').write_text(
            'Local development only. Do not submit or share this file.\nURL: http://127.0.0.1:5000\n'
            'Username: admin\nPassword: ' + secret + '\nChange using PUT /api/v1/auth/password.\n', encoding='utf-8')
    print('Configuration and administrator ready. Credentials: docs/LOCAL_ACCESS.txt')

if __name__ == '__main__':
    main()
