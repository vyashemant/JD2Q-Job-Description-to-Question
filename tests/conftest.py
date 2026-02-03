"""
Test configuration and fixtures for pytest.
"""
import pytest
import os
from app import create_app


@pytest.fixture
def app():
    """Create Flask app for testing."""
    # Set test environment
    os.environ['FLASK_ENV'] = 'testing'
    
    app = create_app('testing')
    
    yield app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_supabase_client(monkeypatch):
    """Mock Supabase client for testing."""
    class MockSupabaseClient:
        def __init__(self, url, key):
            self.url = url
            self.key = key
            
        def table(self, name):
            return MockTable(name)
        
        @property
        def auth(self):
            return MockAuth()
    
    class MockTable:
        def __init__(self, name):
            self.name = name
            self._data = []
            
        def select(self, *args):
            return self
            
        def insert(self, data):
            self._data.append(data)
            return self
            
        def update(self, data):
            return self
            
        def delete(self):
            return self
            
        def eq(self, field, value):
            return self
            
        def execute(self):
            class Response:
                data = []
            return Response()
    
    class MockAuth:
        def sign_in_with_otp(self, credentials):
            return {'user': {'id': 'test-user-id', 'email': credentials['email']}}
    
    def mock_create_client(url, key):
        return MockSupabaseClient(url, key)
    
    monkeypatch.setattr('app.services.supabase_service.create_client', mock_create_client)
    
    return mock_create_client
