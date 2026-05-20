# api_config.py
import os
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# API Endpoints
OPTIMIZATION_TRIGGER_ENDPOINT = 'https://api.bloomberg.com/enterprise/portfolio/optimization/executions'
RESULTS_RETRIEVAL_ENDPOINT = 'https://api.bloomberg.com/enterprise/portfolio/optimization/executions/'
WORKFLOWS_PATH = 'https://api.bloomberg.com/enterprise/workflow/workflows'
WORKFLOW_RUNS_PATH = 'https://api.bloomberg.com/enterprise/workflow/workflow-runs'
CATALOG_PATH = 'https://api.bloomberg.com/enterprise/portfolio/report/info'
REPORT_PATH = 'https://api.bloomberg.com/enterprise/portfolio/report/data'

# Connection Testing Path
CONNECTION_TEST_PATH = 'https://api.bloomberg.com/enterprise/portfolio/optimization/tasks'

# Authentication config path
AUTH_CONFIG_PATH = 'config/port_v2_config.json'  # Adjust this path as needed

# Time between response polling
WAIT_TIME_SECONDS = 10

class AuthManager:
    """
    Manages authentication for Bloomberg API requests.
    
    This class provides methods to obtain valid authorization headers,
    handling token refresh as needed.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize AuthManager with configuration.
        
        Args:
            config_path: Path to authentication configuration file.
                         If None, will look for environment variables.
        """
        self.logger = logging.getLogger(__name__)
        self.oauth_client = None
        
        if config_path:
            self._initialize_from_file(config_path)
        else:
            self._initialize_from_env()
    
    def _initialize_from_file(self, config_path: str):
        """Initialize auth client from config file."""
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Authentication config file not found: {config_path}")
            
        try:
            with open(config_path, "r") as config_file:
                config = json.load(config_file)
                
            # Check if required credentials exist
            if not config.get('client_id') or not config.get('client_secret'):
                raise ValueError(
                    "Required credentials (client_id, client_secret) not found in config file"
                )
                
            # Import Bloomberg OAuth client
            try:
                from bloomberg.enterprise.oauth import (OAuthClient, EnvTier,
                    OAuthDeviceModeConfig, OAuthServerModeConfig
                )

                from bloomberg.enterprise.oauth.oauth_flows.oauth_user_mode import UserModeOauth
                from bloomberg.enterprise.oauth.utils import _oauth_store

                # _oauth_store.purge_tokens(
                #     config.get('client_id'), 
                #     EnvTier.PROD
                #     )
                
                self.oauth_client = OAuthClient(
                    client_id=config.get('client_id'),
                    #env=EnvTier.PROD,
                    config=OAuthDeviceModeConfig(
                        client_secret=config.get('client_secret')
                    )
                )
                self.logger.info("Auth client initialized from config file")
            except ImportError:
                raise ImportError(
                    "Bloomberg authentication libraries not available. "
                    "Ensure the bloomberg.enterprise.oauth package is installed."
                )
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in config file: {config_path}")
        except Exception as e:
            self.logger.error(f"Error initializing auth from file: {e}")
            raise

    def _initialize_from_env(self):
        """Initialize auth client from environment variables."""
        client_id = os.environ.get("CLIENT_ID_USER_MODE_4571")
        client_secret = os.environ.get("CLIENT_SECRET_USER_MODE_4571")
        
        if not client_id or not client_secret:
            raise ValueError(
                "Bloomberg API credentials not found in environment variables. "
                "Set CLIENT_ID_USER_MODE_4571 and CLIENT_SECRET_USER_MODE_4571 environment variables."
            )
            
        try:
            from bloomberg.enterprise.oauth import (OAuthClient, EnvTier,
                OAuthDeviceModeConfig, OAuthServerModeConfig
            )

            from bloomberg.enterprise.oauth.oauth_flows.oauth_user_mode import UserModeOauth
            from bloomberg.enterprise.oauth.utils import _oauth_store
            
            # _oauth_store.purge_tokens(client_id, EnvTier.PROD)

            self.oauth_client = OAuthClient(
                client_id=client_id,
                #env=EnvTier.PROD,
                config=OAuthDeviceModeConfig(
                    client_secret=client_secret
                )
            )
            self.logger.info("Auth client initialized from environment variables")
        except ImportError:
            raise ImportError(
                "Bloomberg authentication libraries not available. "
                "Ensure the bloomberg.enterprise.oauth package is installed."
            )
        except Exception as e:
            self.logger.error(f"Error initializing auth from file: {e}")
            raise
    
    def get_authorization_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests.
        
        Returns:
            Dictionary containing authorization headers
            
        Raises:
            ValueError: If authentication credentials are not available
            RuntimeError: If token generation fails
        """
        if not self.oauth_client:
            raise ValueError(
                "Bloomberg API authentication client not initialized. "
                "Check that credentials are provided either through config file or environment variables."
            )
        
        try:
            token = self.oauth_client.generate_or_refresh_token()
            self.logger.debug("Generated authorization token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            # Log the error for debugging
            self.logger.error(f"Error generating authentication token: {e}")
            # But also raise an exception to prevent proceeding with invalid auth
            raise RuntimeError(f"Failed to generate authentication token: {e}")
        
    

    def test_connection(self, test_url: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Test the API connection and return detailed results
        
        Args:
            test_url: URL to use for connection testing. If None, uses a default endpoint.
            
        Returns:
            Tuple containing:
                - bool: True if connection was successful, False otherwise
                - Optional[Dict]: Response details if available, None on exception
        """
        if test_url is None:
            test_url = CONNECTION_TEST_PATH
        
        try:
            headers = self.get_authorization_headers()
            response = requests.get(test_url, headers=headers, timeout=10)
            
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"text": response.text[:1000]}
                
            result = {
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers)
            }
            
            success = response.status_code == 200
            return success, result
                
        except requests.RequestException as e:
            logger = logging.getLogger(__name__)
            logger.error(f"API connection test failed with exception: {e}")
            return False, None



# Create a default instance with the config file
try:
    # First check if the config file exists
    if os.path.exists(AUTH_CONFIG_PATH):
        auth_manager = AuthManager(config_path=AUTH_CONFIG_PATH)
        logger = logging.getLogger(__name__)
        logger.info(f"Initialized AuthManager with config file: {AUTH_CONFIG_PATH}")
    else:
        # Fall back to environment variables if file doesn't exist
        logger = logging.getLogger(__name__)
        logger.warning(f"Config file {AUTH_CONFIG_PATH} not found, trying environment variables")
        auth_manager = AuthManager()
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize default AuthManager: {e}")
    auth_manager = None

def get_authorization_headers() -> Dict[str, str]:
    """
    Get authorization headers for API requests.
    
    Returns:
        Dictionary containing authorization headers
        
    Raises:
        RuntimeError: If authentication is not properly configured
    """
    if auth_manager is None:
        raise RuntimeError(
            "Authentication manager not properly initialized. "
            "Ensure proper credentials are provided."
        )
    return auth_manager.get_authorization_headers()


# Add a standalone wrapper function to test connection for convenience
def test_connection(test_url: str = None) -> bool:
    """
    Test the API connection using the default authentication manager.
    
    Args:
        test_url: URL to use for connection testing. If None, uses a default endpoint.
        
    Returns:
        bool: True if connection was successful, False otherwise
        
    Raises:
        RuntimeError: If authentication is not properly configured
    """
    if auth_manager is None:
        raise RuntimeError(
            "Authentication manager not properly initialized. "
            "Ensure proper credentials are provided."
        )
    return auth_manager.test_connection(test_url)