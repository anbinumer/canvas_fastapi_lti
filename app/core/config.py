"""
Environment configuration for Railway deployment
"""

import os
from typing import Dict, Any


class EnvironmentConfig:
    """Environment-specific configuration for Railway deployment"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.config = self.get_environment_config()
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get configuration based on Railway environment"""
        
        configs = {
            'development': {
                'debug': True,
                'log_level': 'DEBUG',
                'canvas_api_timeout': 30,
                'max_concurrent_tasks': 5,
                'cache_ttl': 300,  # 5 minutes
                'session_timeout': 3600,  # 1 hour
                'allowed_canvas_instances': ['canvas.test.instructure.com']
            },
            'staging': {
                'debug': False,
                'log_level': 'INFO',
                'canvas_api_timeout': 60,
                'max_concurrent_tasks': 10,
                'cache_ttl': 1800,  # 30 minutes
                'session_timeout': 7200,  # 2 hours
                'allowed_canvas_instances': ['canvas.test.instructure.com', 'acu-test.instructure.com']
            },
            'production': {
                'debug': False,
                'log_level': 'WARNING',
                'canvas_api_timeout': 120,
                'max_concurrent_tasks': 25,
                'cache_ttl': 3600,  # 1 hour
                'session_timeout': 14400,  # 4 hours
                'allowed_canvas_instances': ['acu.instructure.com']
            }
        }
        
        return configs.get(self.environment, configs['development'])


# Global configuration instance
config = EnvironmentConfig() 