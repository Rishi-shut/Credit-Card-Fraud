"""
Tests for authentication endpoints — register, login, profile.
Run with: pytest tests/test_auth.py -v
"""


class TestRegister:
    def test_register_creates_account(self, client):
        r = client.post('/auth/register', json={
            'email': 'newuser@test.com',
            'password': 'securepass123'
        })
        assert r.status_code == 201
        data = r.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'newuser@test.com'

    def test_register_rejects_duplicate_email(self, client):
        client.post('/auth/register', json={'email': 'dup@test.com', 'password': 'pass12345'})
        r = client.post('/auth/register', json={'email': 'dup@test.com', 'password': 'pass12345'})
        assert r.status_code == 409

    def test_register_rejects_short_password(self, client):
        r = client.post('/auth/register', json={'email': 'short@test.com', 'password': '123'})
        assert r.status_code == 400

    def test_register_rejects_invalid_email(self, client):
        r = client.post('/auth/register', json={'email': 'notanemail', 'password': 'pass12345'})
        assert r.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        client.post('/auth/register', json={'email': 'login@test.com', 'password': 'mypassword1'})
        r = client.post('/auth/login', json={'email': 'login@test.com', 'password': 'mypassword1'})
        assert r.status_code == 200
        assert 'access_token' in r.get_json()

    def test_login_wrong_password(self, client):
        client.post('/auth/register', json={'email': 'wp@test.com', 'password': 'correctpass'})
        r = client.post('/auth/login', json={'email': 'wp@test.com', 'password': 'wrongpass'})
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post('/auth/login', json={'email': 'nobody@test.com', 'password': 'anything'})
        assert r.status_code == 401


class TestProfile:
    def test_me_requires_auth(self, client):
        r = client.get('/auth/me')
        assert r.status_code == 401

    def test_me_returns_user(self, client, auth_headers):
        r = client.get('/auth/me', headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'user' in data
        assert 'email' in data['user']

    def test_history_requires_auth(self, client):
        r = client.get('/predict/history')
        assert r.status_code == 401

    def test_history_returns_empty_for_new_user(self, client, auth_headers):
        r = client.get('/predict/history', headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'predictions' in data
