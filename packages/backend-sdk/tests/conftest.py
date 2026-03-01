"""Test configuration and fixtures."""

import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application."""
    return FastAPI()


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_jwks_service() -> MagicMock:
    """Create a mock JWKS service."""
    service = MagicMock()
    service.get_public_key = AsyncMock()
    return service


@pytest.fixture
def valid_jwt_token() -> str:
    """Create a valid JWT token for testing."""
    # This will be implemented with actual JWT generation
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2lkIn0..."


@pytest.fixture
def expired_jwt_token() -> str:
    """Create an expired JWT token for testing."""
    return "expired.token.here"


@pytest.fixture
def invalid_signature_token() -> str:
    """Create a JWT token with invalid signature."""
    return "invalid.signature.token"
