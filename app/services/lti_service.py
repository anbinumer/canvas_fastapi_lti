"""
LTI 1.3 authentication business logic for Canvas integration
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import Request, HTTPException
# PyLTI1p3 imports - will be properly configured when PyLTI1p3 is installed
try:
    from pylti1p3.tool_config import ToolConfDict
    from pylti1p3.registration import Registration  
    from pylti1p3.message_launch import MessageLaunch
    from pylti1p3.deep_link import DeepLink
    from pylti1p3.oidc_login import OidcLogin
    from pylti1p3.exception import LtiException, OidcException
    PYLTI_AVAILABLE = True
except ImportError:
    # Mock classes for development without PyLTI1p3
    class ToolConfDict(dict): pass
    class Registration: pass
    class MessageLaunch: pass  
    class DeepLink: pass
    class OidcLogin: pass
    class LtiException(Exception): pass
    class OidcException(Exception): pass
    PYLTI_AVAILABLE = False

from app.core.config import settings
from app.core.exceptions import LTIAuthenticationError, LTIValidationError


logger = logging.getLogger(__name__)


class LTIService:
    """
    Canvas LTI 1.3 authentication and validation service
    Enhanced with multi-instance Canvas support
    """
    
    def __init__(self):
        self.tool_config = self._create_tool_config()
        self.registrations = self._create_registrations()
        
    def _create_tool_config(self) -> ToolConfDict:
        """Create LTI tool configuration for active Canvas instance"""
        if not PYLTI_AVAILABLE:
            logger.warning("PyLTI1p3 not available - using mock configuration")
            return ToolConfDict({})
            
        # Get active Canvas instance configuration
        canvas_config = settings.get_canvas_instance_config()
        if not canvas_config or not canvas_config.client_id or not canvas_config.private_key:
            logger.warning("LTI configuration incomplete - some features may not work")
            return ToolConfDict({})
            
        config = {
            canvas_config.client_id: {
                "client_id": canvas_config.client_id,
                "auth_login_url": f"{canvas_config.base_url}/api/lti/authorize_redirect",
                "auth_token_url": f"{canvas_config.base_url}/login/oauth2/token",
                "key_set_url": f"{canvas_config.base_url}/api/lti/security/jwks",
                "private_key_file": None,  # We use the private_key directly
                "private_key": canvas_config.private_key,
                "deployment_ids": ["1"]  # Default deployment ID for Canvas
            }
        }
        
        return ToolConfDict(config)
        
    def _create_registrations(self) -> Dict[str, Registration]:
        """Create LTI registrations for configured Canvas instances"""
        if not PYLTI_AVAILABLE:
            return {}
            
        registrations = {}
        
        # Get all configured Canvas instances
        canvas_instances = settings.get_all_canvas_instances()
        
        for instance_name, canvas_config in canvas_instances.items():
            if canvas_config.client_id and canvas_config.private_key:
                try:
                    registration = Registration()
                    registration.set_auth_login_url(f"{canvas_config.base_url}/api/lti/authorize_redirect")
                    registration.set_auth_token_url(f"{canvas_config.base_url}/login/oauth2/token")
                    registration.set_key_set_url(f"{canvas_config.base_url}/api/lti/security/jwks")
                    registration.set_client_id(canvas_config.client_id)
                    registration.set_issuer(canvas_config.base_url)
                    
                    registrations[instance_name] = registration
                    logger.info(f"Created LTI registration for Canvas instance '{instance_name}'")
                    
                except Exception as e:
                    logger.error(f"Failed to create LTI registration for {instance_name}: {e}")
                    
        return registrations

    def get_active_registration(self) -> Optional[Registration]:
        """Get registration for the active Canvas instance"""
        active_instance = settings.canvas_active_instance
        return self.registrations.get(active_instance)

    def validate_lti_launch(self, request: Request, id_token: str) -> Dict[str, Any]:
        """
        Validate LTI 1.3 launch request
        """
        try:
            if not PYLTI_AVAILABLE:
                logger.warning("PyLTI1p3 not available - using mock validation")
                return self._mock_lti_validation()
                
            # Get active Canvas configuration
            canvas_config = settings.get_canvas_instance_config()
            if not canvas_config:
                raise LTIValidationError("No active Canvas instance configured")
                
            # Validate the LTI launch using PyLTI1p3
            message_launch = MessageLaunch(request, self.tool_config)
            message_launch.validate_nonce()
            message_launch.validate_registration()
            
            # Extract launch data
            launch_data = message_launch.get_launch_data()
            
            # Validate Canvas instance
            issuer = launch_data.get('iss', '')
            if not self._validate_canvas_issuer(issuer, canvas_config.base_url):
                raise LTIValidationError(f"Invalid Canvas issuer: {issuer}")
                
            return launch_data
            
        except Exception as e:
            logger.error(f"LTI validation failed: {str(e)}")
            raise LTIValidationError(f"LTI validation failed: {str(e)}")

    def _validate_canvas_issuer(self, issuer: str, expected_canvas_url: str) -> bool:
        """Validate that the issuer matches the expected Canvas instance"""
        try:
            # Normalize URLs for comparison
            issuer_clean = issuer.rstrip('/')
            expected_clean = expected_canvas_url.rstrip('/')
            
            return issuer_clean == expected_clean
            
        except Exception as e:
            logger.error(f"Error validating Canvas issuer: {e}")
            return False

    def _mock_lti_validation(self) -> Dict[str, Any]:
        """Mock LTI validation for development without PyLTI1p3"""
        canvas_config = settings.get_canvas_instance_config()
        
        return {
            "iss": canvas_config.base_url if canvas_config else "https://canvas.example.com",
            "aud": canvas_config.client_id if canvas_config else "test_client_id",
            "sub": "test_user_123",
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "email": "test.user@example.com",
            "exp": 9999999999,
            "iat": 1600000000,
            "nonce": "test_nonce",
            "https://purl.imsglobal.org/spec/lti/claim/roles": [
                "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"
            ],
            "https://purl.imsglobal.org/spec/lti/claim/context": {
                "id": "test_course_123",
                "title": "Test Course",
                "type": ["http://purl.imsglobal.org/vocab/lis/v2/course#CourseOffering"]
            },
            "custom_canvas_course_id": "123",
            "custom_canvas_user_id": "456"
        }

    def create_deep_link(self, request: Request, content_items: List[Dict[str, Any]]) -> str:
        """
        Create Canvas Deep Link response
        """
        try:
            if not PYLTI_AVAILABLE:
                logger.warning("PyLTI1p3 not available - cannot create deep link")
                return ""
                
            deep_link = DeepLink(request, self.tool_config)
            
            for item in content_items:
                deep_link.add_resource_link(
                    url=item.get('url', ''),
                    title=item.get('title', ''),
                    text=item.get('text', '')
                )
                
            return deep_link.get_response_jwt()
            
        except Exception as e:
            logger.error(f"Deep link creation failed: {str(e)}")
            return ""

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get JSON Web Key Set for LTI 1.3 authentication
        """
        try:
            # Get active Canvas configuration
            canvas_config = settings.get_canvas_instance_config()
            if not canvas_config or not canvas_config.private_key:
                logger.warning("No private key available for JWKS generation")
                return {"keys": []}
                
            # In a real implementation, you would generate the JWK from the private key
            # For now, return a placeholder structure
            return {
                "keys": [
                    {
                        "kty": "RSA",
                        "kid": f"canvas_{settings.canvas_active_instance}",
                        "use": "sig",
                        "alg": "RS256",
                        "n": "placeholder_modulus",
                        "e": "AQAB"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"JWKS generation failed: {str(e)}")
            return {"keys": []}

    def switch_canvas_instance(self, instance_name: str) -> bool:
        """
        Switch to a different Canvas instance (for testing/multi-tenancy)
        """
        try:
            canvas_config = settings.get_canvas_instance_config(instance_name)
            if not canvas_config:
                logger.error(f"Canvas instance '{instance_name}' not found")
                return False
                
            # Update active instance
            settings.canvas_active_instance = instance_name
            
            # Recreate configurations
            self.tool_config = self._create_tool_config()
            self.registrations = self._create_registrations()
            
            logger.info(f"Switched to Canvas instance: {instance_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch Canvas instance to {instance_name}: {e}")
            return False

    def get_instance_info(self) -> Dict[str, Any]:
        """Get information about the current Canvas instance configuration"""
        canvas_config = settings.get_canvas_instance_config()
        
        return {
            "active_instance": settings.canvas_active_instance,
            "base_url": canvas_config.base_url if canvas_config else None,
            "client_id": canvas_config.client_id if canvas_config else None,
            "configured": bool(canvas_config and canvas_config.client_id and canvas_config.private_key),
            "description": canvas_config.description if canvas_config else "",
            "available_instances": list(settings.get_all_canvas_instances().keys())
        }


# Global LTI service instance
lti_service = LTIService() 