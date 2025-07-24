"""
Canvas Multi-Instance Integration Tests
Story 2.4: Canvas Integration & Testing

Tests for multi-instance Canvas configuration, switching, and health checks.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.config import get_settings, reload_settings, CanvasInstanceConfig
from app.services.canvas_service import create_canvas_service_for_instance
from app.core.rate_limiter import get_rate_limiter
from app.core.canvas_error_handler import get_canvas_error_handler


class TestCanvasInstanceConfiguration:
    """Test Canvas instance configuration functionality."""
    
    def test_canvas_instance_config_creation(self):
        """Test creating CanvasInstanceConfig objects."""
        config = CanvasInstanceConfig(
            name="test",
            base_url="https://www.aculeo.test.instructure.com",
            client_id="test_client_id",
            private_key_base64="dGVzdF9wcml2YXRlX2tleQ=="  # base64 "test_private_key"
        )
        
        assert config.name == "test"
        assert config.base_url == "https://www.aculeo.test.instructure.com"
        assert config.client_id == "test_client_id"
        assert config.api_base_url == "https://www.aculeo.test.instructure.com/api/v1"
        assert config.private_key == "test_private_key"
    
    def test_canvas_instance_config_properties(self):
        """Test CanvasInstanceConfig properties and methods."""
        config = CanvasInstanceConfig(
            name="beta",
            base_url="https://www.aculeo.beta.instructure.com",
            client_id="beta_client_id",
            private_key_base64="YmV0YV9wcml2YXRlX2tleQ==",  # base64 "beta_private_key"
            rate_limit_per_minute=150,
            rate_limit_per_hour=4000,
            description="Test Beta Instance"
        )
        
        assert config.rate_limit_per_minute == 150
        assert config.rate_limit_per_hour == 4000
        assert config.description == "Test Beta Instance"
        assert config.private_key == "beta_private_key"
    
    def test_invalid_private_key_base64(self):
        """Test handling of invalid base64 private key."""
        config = CanvasInstanceConfig(
            name="test",
            base_url="https://www.aculeo.test.instructure.com",
            client_id="test_client_id",
            private_key_base64="invalid_base64!"
        )
        
        # Should return None for invalid base64
        assert config.private_key is None


class TestMultiInstanceSettings:
    """Test multi-instance settings functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self, monkeypatch):
        """Set up test environment variables."""
        # Clear any existing settings
        monkeypatch.setenv("CANVAS_TEST_CLIENT_ID", "test_client_123")
        monkeypatch.setenv("CANVAS_TEST_PRIVATE_KEY", "dGVzdF9wcml2YXRlX2tleQ==")
        monkeypatch.setenv("CANVAS_BETA_CLIENT_ID", "beta_client_456")
        monkeypatch.setenv("CANVAS_BETA_PRIVATE_KEY", "YmV0YV9wcml2YXRlX2tleQ==")
        monkeypatch.setenv("CANVAS_PROD_CLIENT_ID", "prod_client_789")
        monkeypatch.setenv("CANVAS_PROD_PRIVATE_KEY", "cHJvZF9wcml2YXRlX2tleQ==")
        monkeypatch.setenv("CANVAS_ACTIVE_INSTANCE", "test")
        
        # Reload settings to pick up new environment
        reload_settings()
    
    def test_get_canvas_instances(self):
        """Test retrieving all configured Canvas instances."""
        settings = get_settings()
        instances = settings.get_canvas_instances()
        
        assert "test" in instances
        assert "beta" in instances
        assert "prod" in instances
        
        # Verify test instance
        test_instance = instances["test"]
        assert test_instance.name == "test"
        assert test_instance.client_id == "test_client_123"
        assert test_instance.base_url == "https://www.aculeo.test.instructure.com"
        
        # Verify beta instance
        beta_instance = instances["beta"]
        assert beta_instance.name == "beta"
        assert beta_instance.client_id == "beta_client_456"
        assert beta_instance.base_url == "https://www.aculeo.beta.instructure.com"
    
    def test_get_active_canvas_instance(self):
        """Test getting the active Canvas instance."""
        settings = get_settings()
        active_instance = settings.get_active_canvas_instance()
        
        assert active_instance is not None
        assert active_instance.name == "test"
        assert active_instance.client_id == "test_client_123"
    
    def test_set_active_canvas_instance(self):
        """Test switching the active Canvas instance."""
        settings = get_settings()
        
        # Switch to beta
        success = settings.set_active_canvas_instance("beta")
        assert success is True
        assert settings.canvas_active_instance == "beta"
        
        # Switch to invalid instance
        success = settings.set_active_canvas_instance("invalid")
        assert success is False
        assert settings.canvas_active_instance == "beta"  # Should remain unchanged
    
    def test_get_canvas_instance_summary(self):
        """Test getting Canvas instance summary."""
        settings = get_settings()
        summary = settings.get_canvas_instance_summary()
        
        assert "active_instance" in summary
        assert "available_instances" in summary
        assert "total_instances" in summary
        assert "instances_detail" in summary
        
        assert summary["active_instance"] == "test"
        assert "test" in summary["available_instances"]
        assert "beta" in summary["available_instances"]
        assert "prod" in summary["available_instances"]
        assert summary["total_instances"] == 3
    
    def test_validate_canvas_instances(self):
        """Test Canvas instance configuration validation."""
        settings = get_settings()
        validation_results = settings.validate_canvas_instances()
        
        assert "valid" in validation_results
        assert "active_instance_valid" in validation_results
        assert "instances" in validation_results
        
        # Should be valid with our test configuration
        assert validation_results["valid"] is True
        assert validation_results["active_instance_valid"] is True
        
        # Check individual instance validation
        assert "test" in validation_results["instances"]
        assert validation_results["instances"]["test"]["valid"] is True
    
    def test_allowed_canvas_instances_property(self):
        """Test the allowed_canvas_instances property."""
        settings = get_settings()
        allowed_instances = settings.allowed_canvas_instances
        
        assert "www.aculeo.test.instructure.com" in allowed_instances
        assert "www.aculeo.beta.instructure.com" in allowed_instances
        assert "www.aculeo.instructure.com" in allowed_instances


class TestCanvasServiceMultiInstance:
    """Test Canvas service with multi-instance support."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self, monkeypatch):
        """Set up test environment."""
        monkeypatch.setenv("CANVAS_TEST_CLIENT_ID", "test_client_123")
        monkeypatch.setenv("CANVAS_TEST_PRIVATE_KEY", "dGVzdF9wcml2YXRlX2tleQ==")
        monkeypatch.setenv("CANVAS_BETA_CLIENT_ID", "beta_client_456") 
        monkeypatch.setenv("CANVAS_BETA_PRIVATE_KEY", "YmV0YV9wcml2YXRlX2tleQ==")
        monkeypatch.setenv("CANVAS_ACTIVE_INSTANCE", "test")
        reload_settings()
    
    def test_create_canvas_service_for_instance(self):
        """Test creating Canvas service for specific instance."""
        # Test creating service for test instance
        service = create_canvas_service_for_instance(
            instance_name="test",
            access_token="test_token",
            user_id="test_user"
        )
        
        assert service.base_url == "https://www.aculeo.test.instructure.com"
        assert service.access_token == "test_token"
        assert service.user_id == "test_user"
    
    def test_create_canvas_service_invalid_instance(self):
        """Test creating Canvas service for invalid instance."""
        with pytest.raises(ValueError) as exc_info:
            create_canvas_service_for_instance(
                instance_name="invalid",
                access_token="test_token"
            )
        
        assert "not configured" in str(exc_info.value)
        assert "Available instances" in str(exc_info.value)
    
    @patch('app.services.canvas_service.logger')
    def test_canvas_service_logging(self, mock_logger):
        """Test that Canvas service logs instance information."""
        create_canvas_service_for_instance(
            instance_name="test",
            access_token="test_token",
            user_id="test_user"
        )
        
        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "test" in log_call
        assert "www.aculeo.test.instructure.com" in log_call


class TestMultiInstanceHealthChecks:
    """Test health check endpoints with multi-instance support."""
    
    @pytest.mark.asyncio
    async def test_canvas_health_check_all_instances(self):
        """Test Canvas health check across all instances."""
        from app.api.routes.health import canvas_health_check
        
        with patch('app.api.routes.health.get_settings') as mock_get_settings:
            # Mock settings with test instances
            mock_settings = MagicMock()
            mock_settings.canvas_active_instance = "test"
            mock_settings.get_canvas_instance_summary.return_value = {
                "active_instance": "test",
                "available_instances": ["test", "beta"],
                "total_instances": 2
            }
            mock_settings.get_canvas_instances.return_value = {
                "test": CanvasInstanceConfig(
                    name="test",
                    base_url="https://www.aculeo.test.instructure.com",
                    client_id="test_client"
                ),
                "beta": CanvasInstanceConfig(
                    name="beta", 
                    base_url="https://www.aculeo.beta.instructure.com",
                    client_id="beta_client"
                )
            }
            mock_settings.validate_canvas_instances.return_value = {
                "valid": True,
                "active_instance_valid": True,
                "instances": {}
            }
            mock_get_settings.return_value = mock_settings
            
            with patch('app.api.routes.health.get_rate_limiter') as mock_rate_limiter:
                mock_rate_limiter.return_value = AsyncMock()
                
                with patch('app.api.routes.health.check_canvas_rate_limit') as mock_rate_check:
                    mock_rate_check.return_value = MagicMock(
                        allowed=True,
                        remaining_requests=100,
                        current_usage=10
                    )
                    
                    with patch('aiohttp.ClientSession') as mock_session:
                        # Mock successful Canvas API responses
                        mock_response = AsyncMock()
                        mock_response.status = 200
                        mock_response.json.return_value = {"status": "ok"}
                        
                        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
                        
                        # Call health check
                        response = await canvas_health_check()
                        
                        # Verify response structure
                        assert response.status_code in [200, 503]
                        response_data = response.body.decode()
                        assert "active_instance" in response_data
                        assert "instance_summary" in response_data
    
    @pytest.mark.asyncio
    async def test_canvas_health_check_specific_instance(self):
        """Test Canvas health check for specific instance."""
        from app.api.routes.health import canvas_health_check
        
        with patch('app.api.routes.health.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_canvas_instances.return_value = {
                "test": CanvasInstanceConfig(
                    name="test",
                    base_url="https://www.aculeo.test.instructure.com", 
                    client_id="test_client"
                )
            }
            mock_get_settings.return_value = mock_settings
            
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {"status": "ok"}
                
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
                
                # Call health check for specific instance
                response = await canvas_health_check(instance="test")
                
                assert response.status_code in [200, 503]


class TestInstanceSwitching:
    """Test runtime instance switching functionality."""
    
    @pytest.mark.asyncio
    async def test_switch_canvas_instance_success(self):
        """Test successful Canvas instance switching."""
        from app.api.routes.health import switch_canvas_instance
        
        with patch('app.api.routes.health.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_canvas_instances.return_value = {
                "beta": CanvasInstanceConfig(
                    name="beta",
                    base_url="https://www.aculeo.beta.instructure.com",
                    client_id="beta_client",
                    private_key_base64="YmV0YV9rZXk="
                )
            }
            mock_settings.set_active_canvas_instance.return_value = True
            mock_settings.canvas_active_instance = "test"
            mock_get_settings.return_value = mock_settings
            
            # Mock current user
            mock_user = {"id": "test_user", "is_admin": True}
            
            # Call switch instance
            response = await switch_canvas_instance("beta", mock_user)
            
            assert response["status"] == "success"
            assert response["new_active_instance"] == "beta"
            assert "Switched to Canvas instance: beta" in response["message"]
    
    @pytest.mark.asyncio
    async def test_switch_canvas_instance_invalid(self):
        """Test switching to invalid Canvas instance."""
        from app.api.routes.health import switch_canvas_instance
        from fastapi import HTTPException
        
        with patch('app.api.routes.health.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_canvas_instances.return_value = {}
            mock_get_settings.return_value = mock_settings
            
            mock_user = {"id": "test_user", "is_admin": True}
            
            # Should raise HTTPException for invalid instance
            with pytest.raises(HTTPException) as exc_info:
                await switch_canvas_instance("invalid", mock_user)
            
            assert exc_info.value.status_code == 400
            assert "not configured" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_canvas_instances_endpoint(self):
        """Test the get canvas instances endpoint."""
        from app.api.routes.health import get_canvas_instances
        
        with patch('app.api.routes.health.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.get_canvas_instance_summary.return_value = {
                "active_instance": "test",
                "available_instances": ["test", "beta", "prod"]
            }
            mock_settings.validate_canvas_instances.return_value = {
                "valid": True,
                "instances": {}
            }
            mock_get_settings.return_value = mock_settings
            
            response = await get_canvas_instances()
            
            assert "instance_summary" in response
            assert "validation_results" in response
            assert "environment_mapping" in response
            assert response["environment_mapping"]["development"] == "test"
            assert response["environment_mapping"]["staging"] == "beta"
            assert response["environment_mapping"]["production"] == "prod"


class TestEnvironmentSpecificConfiguration:
    """Test environment-specific Canvas instance configuration."""
    
    def test_development_environment_defaults(self, monkeypatch):
        """Test development environment defaults to test instance."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("CANVAS_TEST_CLIENT_ID", "test_client")
        reload_settings()
        
        settings = get_settings()
        env_config = settings.get_environment_config()
        
        assert env_config["canvas_active_instance"] == "test"
        assert env_config["debug"] is True
        assert env_config["session_cookie_secure"] is False
    
    def test_staging_environment_defaults(self, monkeypatch):
        """Test staging environment defaults to beta instance."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        reload_settings()
        
        settings = get_settings()
        env_config = settings.get_environment_config()
        
        assert env_config["canvas_active_instance"] == "beta"
        assert env_config["debug"] is False
        assert env_config["session_cookie_secure"] is True
    
    def test_production_environment_defaults(self, monkeypatch):
        """Test production environment defaults to prod instance."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        reload_settings()
        
        settings = get_settings()
        env_config = settings.get_environment_config()
        
        assert env_config["canvas_active_instance"] == "prod"
        assert env_config["debug"] is False
        assert env_config["session_cookie_secure"] is True


class TestLegacyCompatibility:
    """Test backward compatibility with legacy single-instance configuration."""
    
    def test_legacy_configuration_fallback(self, monkeypatch):
        """Test fallback to legacy configuration when multi-instance not configured."""
        # Clear multi-instance config
        monkeypatch.delenv("CANVAS_TEST_CLIENT_ID", raising=False)
        monkeypatch.delenv("CANVAS_BETA_CLIENT_ID", raising=False)
        monkeypatch.delenv("CANVAS_PROD_CLIENT_ID", raising=False)
        
        # Set legacy config
        monkeypatch.setenv("CANVAS_CLIENT_ID", "legacy_client")
        monkeypatch.setenv("LTI_PRIVATE_KEY", "bGVnYWN5X2tleQ==")
        reload_settings()
        
        settings = get_settings()
        instances = settings.get_canvas_instances()
        
        assert "legacy" in instances
        legacy_instance = instances["legacy"]
        assert legacy_instance.client_id == "legacy_client"
        assert legacy_instance.private_key == "legacy_key"
    
    def test_lti_private_key_property_legacy(self, monkeypatch):
        """Test lti_private_key property with legacy configuration."""
        monkeypatch.setenv("CANVAS_CLIENT_ID", "legacy_client")
        monkeypatch.setenv("LTI_PRIVATE_KEY", "bGVnYWN5X2tleQ==")
        monkeypatch.setenv("CANVAS_ACTIVE_INSTANCE", "legacy")
        reload_settings()
        
        settings = get_settings()
        
        # Should return legacy private key
        assert settings.lti_private_key == "legacy_key"


@pytest.mark.integration
class TestMultiInstanceIntegration:
    """Integration tests for multi-instance functionality."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_instance_switching(self):
        """Test end-to-end instance switching workflow."""
        # This would be a more comprehensive test that actually
        # switches instances and verifies the entire workflow
        pass
    
    @pytest.mark.asyncio 
    async def test_rate_limiting_per_instance(self):
        """Test that rate limiting works correctly per instance."""
        # Test that rate limits are tracked separately per instance
        pass
    
    @pytest.mark.asyncio
    async def test_canvas_api_calls_with_different_instances(self):
        """Test actual Canvas API calls with different instances."""
        # This would require actual Canvas test instances
        # and should be run in a proper test environment
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 