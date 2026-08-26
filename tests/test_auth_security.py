"""
Comprehensive Authentication and Authorization Testing for EcoBuddy
Tests include credential validation, session lifecycle, access control,
and unauthorized access prevention.
"""

import pytest
flask = pytest.importorskip("flask")
from flask import Flask, session
from datetime import datetime, timedelta
import json

# Note: Update these imports based on the actual project structure
# Check components folder to find the correct module names
try:
    from app import app, db, User  # Try common pattern
except ImportError:
    try:
        from components.app import app, db, User
    except ImportError:
        # Adjust based on what you find in the components folder
        pass

class TestAuthentication:
    """Test suite for user authentication mechanisms."""

    @pytest.fixture
    def client(self):
        """Set up test client with in-memory database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                # Create test user
                test_user = User(
                    username='testuser',
                    email='test@example.com'
                )
                test_user.set_password('ValidPass123!')
                db.session.add(test_user)
                db.session.commit()
                yield client
            db.drop_all()

    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers for a valid user."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'ValidPass123!'
        })
        token = response.json.get('access_token')
        return {'Authorization': f'Bearer {token}'}

    # === Test Case 1: Successful Authentication ===
    def test_successful_authentication_with_valid_credentials(self, client):
        """Test successful authentication with valid credentials."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'ValidPass123!'
        })
        assert response.status_code == 200
        data = response.json
        assert 'access_token' in data
        assert data['message'] == 'Login successful'

    # === Test Case 2: Authentication Failure with Incorrect Credentials ===
    def test_authentication_failure_with_incorrect_credentials(self, client):
        """Test authentication failure with incorrect password."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'WrongPassword123'
        })
        assert response.status_code == 401
        assert 'Invalid credentials' in response.json.get('error', '')

    # === Test Case 3: Non-existent Account ===
    def test_authentication_attempt_non_existent_account(self, client):
        """Test authentication attempt using a non-existent account."""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123'
        })
        assert response.status_code == 401
        assert 'Invalid credentials' in response.json.get('error', '')

    # === Test Case 4: Access Protected Resources Without Authentication ===
    def test_access_protected_resources_without_authentication(self, client):
        """Test access to protected resources without authentication."""
        response = client.get('/api/protected/endpoint')
        assert response.status_code == 401
        assert 'Authentication required' in response.json.get('error', '')

    # === Test Case 5: Access Using Expired Token ===
    def test_access_with_expired_session_credentials(self, client, auth_headers):
        """Test access using expired or malformed session credentials."""
        # Modify token to simulate expired (implementation specific)
        expired_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' \
                        'eyJleHAiOjE1MDAwMDAwMDB9.' \
                        'signature'
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = client.get('/api/protected/endpoint', headers=headers)
        assert response.status_code in [401, 403]
        assert 'expired' in response.json.get('error', '').lower()

    # === Test Case 6: Session Invalidation After Logout ===
    def test_session_invalidation_after_logout(self, client, auth_headers):
        """Test session invalidation after logout."""
        # First, ensure we can access protected endpoint
        response = client.get('/api/protected/endpoint', headers=auth_headers)
        assert response.status_code == 200

        # Perform logout
        response = client.post('/api/auth/logout', headers=auth_headers)
        assert response.status_code == 200
        assert response.json.get('message') == 'Logout successful'

        # Try to access protected endpoint again
        response = client.get('/api/protected/endpoint', headers=auth_headers)
        assert response.status_code in [401, 403]

    # === Test Case 7: Access Resources Outside User's Authorization Scope ===
    def test_access_resources_outside_authorization_scope(self, client):
        """Test attempted access to resources outside the user's authorization scope."""
        # Create a limited user
        limited_user = User(
            username='limited',
            email='limited@example.com',
            role='viewer'  # Assuming role-based access
        )
        limited_user.set_password('LimitedPass123!')
        db.session.add(limited_user)
        db.session.commit()

        # Login as limited user
        response = client.post('/api/auth/login', json={
            'email': 'limited@example.com',
            'password': 'LimitedPass123!'
        })
        token = response.json.get('access_token')
        headers = {'Authorization': f'Bearer {token}'}

        # Try to access admin-only endpoint (if exists)
        response = client.get('/api/admin/users', headers=headers)
        assert response.status_code == 403

    # === Test Case 8: Repeated Authentication Failures ===
    def test_repeated_authentication_failures(self, client):
        """Test repeated authentication failures and account lockout."""
        # Attempt multiple failed logins
        for i in range(5):
            response = client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': f'WrongPassword{i}'
            })
            assert response.status_code == 401

        # Check if account is locked or temporarily blocked
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'ValidPass123!'  # Correct password
        })
        # After 5 failures, should be locked or rate limited
        assert response.status_code in [429, 403]

    # === Test Case 9: Authentication State Persistence ===
    def test_authentication_state_persistence_across_requests(self, client, auth_headers):
        """Test authentication state persistence across multiple requests."""
        # Make several requests to protected endpoints
        for _ in range(3):
            response = client.get('/api/protected/endpoint', headers=auth_headers)
            assert response.status_code == 200
            # Verify session state is maintained
            assert 'user_id' in response.json or response.json.get('authenticated') == True

    # === Additional Security Tests ===
    def test_invalid_authentication_tokens(self, client):
        """Test authentication with invalid tokens."""
        invalid_tokens = [
            'Bearer invalid_token',
            'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid',
            'Bearer ',
            ''
        ]
        for token in invalid_tokens:
            headers = {'Authorization': token}
            response = client.get('/api/protected/endpoint', headers=headers)
            assert response.status_code in [401, 403]

    def test_privilege_level_validation(self, client):
        """Test privilege/access-level validation for different roles."""
        roles = ['viewer', 'editor', 'admin']
        test_data = [
            {'role': 'viewer', 'access': ['/api/profile']},
            {'role': 'editor', 'access': ['/api/profile', '/api/posts']},
            {'role': 'admin', 'access': ['/api/profile', '/api/posts', '/api/admin']}
        ]
        # Implementation would depend on your specific role system
        for role in test_data:
            # Create user with role
            user = User(
                username=f'{role["role"]}_user',
                email=f'{role["role"]}@example.com',
                role=role["role"]
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()

            # Login and test access to each endpoint
            response = client.post('/api/auth/login', json={
                'email': f'{role["role"]}@example.com',
                'password': 'TestPass123!'
            })
            token = response.json.get('access_token')
            headers = {'Authorization': f'Bearer {token}'}

            # Test allowed endpoints (should succeed)
            for endpoint in role['access']:
                response = client.get(endpoint, headers=headers)
                assert response.status_code == 200

    def test_authentication_failure_handling(self, client):
        """Test proper error handling for authentication failures."""
        # Test missing credentials
        response = client.post('/api/auth/login', json={})
        assert response.status_code == 400
        assert 'Missing credentials' in response.json.get('error', '')

        # Test malformed request
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com'
            # Missing password
        })
        assert response.status_code == 400
        assert 'Missing password' in response.json.get('error', '')

        # Test SQL injection attempt
        response = client.post('/api/auth/login', json={
            'email': "test@example.com' OR '1'='1",
            'password': "anything' OR '1'='1"
        })
        assert response.status_code == 401


