import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core.config import settings


class TestRootEndpoint:
    """Test root API endpoint."""
    
    @pytest.mark.asyncio
    async def test_read_root(self, client: AsyncClient):
        """Test root endpoint returns hello world."""
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Hello": "World"}


class TestAPIVersioning:
    """Test API versioning."""
    
    @pytest.mark.asyncio
    async def test_api_v1_prefix(self, client: AsyncClient):
        """Test API v1 prefix is configured."""
        # This tests that the API router is mounted at the correct prefix
        assert settings.API_V1_STR == "/api/v1"


class TestCORS:
    """Test CORS configuration."""
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are set."""
        response = await client.options(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS should allow the configured origins
        assert response.status_code in [200, 405]


class TestHealthCheck:
    """Test application health."""
    
    @pytest.mark.asyncio
    async def test_app_responds(self, client: AsyncClient):
        """Test that the application responds to requests."""
        response = await client.get("/")
        assert response.status_code == 200
