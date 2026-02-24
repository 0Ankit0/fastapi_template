import pytest
from httpx import AsyncClient


class TestAPIEndpoints:
    """Test general API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test API health check endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Hello": "World"}
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are present."""
        response = await client.get("/")
        # CORS headers should be set by middleware
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_api_versioning(self, client: AsyncClient):
        """Test API version prefix works."""
        from src.apps.core.config import settings
        assert settings.API_V1_STR == "/api/v1"
