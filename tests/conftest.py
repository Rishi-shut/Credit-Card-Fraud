"""
pytest fixtures — shared test setup for all test files.
"""
import pytest
from api.app import create_app
from api.database import db as _db


@pytest.fixture(scope='session')
def app():
    """Create a test Flask app with in-memory SQLite."""
    test_app = create_app()
    test_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'SECRET_KEY': 'test-secret',
        'MAIL_SUPPRESS_SEND': True,   # Don't actually send emails during tests
    })
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    """Register a test user and return JWT auth headers."""
    client.post('/auth/register', json={
        'email': 'test@fraudguard.com',
        'password': 'testpassword123'
    })
    resp = client.post('/auth/login', json={
        'email': 'test@fraudguard.com',
        'password': 'testpassword123'
    })
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}
