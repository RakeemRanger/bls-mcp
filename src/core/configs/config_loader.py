"""
Azure Config Loader - Dynamically fetch deployment configurations from Azure
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.web import WebSiteManagementClient


class AzureConfigLoader:
    """
    Loads deployment configuration by querying Azure resources
    """
    
    def __init__(self, environment: str = 'dev', subscription_id: Optional[str] = None):
        """
        Initialize config loader
        
        Args:
            environment: Environment name (dev/prod)
            subscription_id: Azure subscription ID (defaults to env var)
        """
        self.environment = environment
        
        # Load resource group ID from env var or configs.json
        self.resource_group_id = os.getenv('AZURE_RESOURCE_GROUP_ID') or self._load_rg_id()
        
        if not self.resource_group_id:
            raise ValueError(
                f"No resource group ID configured. Set AZURE_RESOURCE_GROUP_ID env var or "
                f"deploy infrastructure for '{environment}' environment."
            )
        
        # Extract subscription ID and RG name from resource ID
        # Format: /subscriptions/{sub-id}/resourceGroups/{rg-name}
        parts = self.resource_group_id.split('/')
        self.subscription_id = subscription_id or parts[2] if len(parts) > 2 else os.getenv('AZURE_SUBSCRIPTION_ID')
        self.resource_group_name = parts[-1]
        
        if not self.subscription_id:
            raise ValueError("Could not determine subscription ID from resource group ID")
        
        # Initialize Azure credential
        self.credential = DefaultAzureCredential()
    
    def _load_rg_id(self) -> str:
        """Load resource group ID from configs.json"""
        try:
            config_path = Path(__file__).parent / 'configs.json'
            with open(config_path, 'r') as f:
                configs = json.load(f)
            return configs.get(self.environment, {}).get('resource_group_id', '')
        except FileNotFoundError:
            return ''
        except json.JSONDecodeError:
            return ''
    
    def get_config(self) -> Dict[str, str]:
        """
        Query Azure and build full configuration
        
        Returns:
            Dictionary with all deployment configuration
        """
        config = {
            'resource_group_id': self.resource_group_id,
            'resource_group_name': self.resource_group_name,
            'subscription_id': self.subscription_id,
            'environment': self.environment
        }
        
        # Initialize Azure clients
        resource_client = ResourceManagementClient(self.credential, self.subscription_id)
        
        # List all resources in the resource group
        resources = list(resource_client.resources.list_by_resource_group(
            self.resource_group_name
        ))
        
        # Find OpenAI account
        openai_accounts = [r for r in resources if r.type == 'Microsoft.CognitiveServices/accounts']
        if openai_accounts:
            openai = openai_accounts[0]
            config['openai_account_name'] = openai.name
            config['openai_account_id'] = openai.id
            
            # Get OpenAI endpoint
            cog_client = CognitiveServicesManagementClient(self.credential, self.subscription_id)
            account_details = cog_client.accounts.get(self.resource_group_name, openai.name)
            config['openai_endpoint'] = account_details.properties.endpoint
            
            # Get model deployments
            deployments = list(cog_client.deployments.list(
                self.resource_group_name,
                openai.name
            ))
            if deployments:
                config['model_deployment_name'] = deployments[0].name
                config['model_name'] = deployments[0].properties.model.name
        
        # Find Function App
        func_apps = [r for r in resources if r.type == 'Microsoft.Web/sites']
        if func_apps:
            func_app = func_apps[0]
            config['func_app_name'] = func_app.name
            config['func_app_id'] = func_app.id
            
            # Get Function App details
            web_client = WebSiteManagementClient(self.credential, self.subscription_id)
            app_details = web_client.web_apps.get(self.resource_group_name, func_app.name)
            config['func_app_url'] = f"https://{app_details.default_host_name}"
            config['location'] = app_details.location
        
        return config
    
    def get_openai_endpoint(self) -> str:
        """Get OpenAI endpoint (convenience method)"""
        return self.get_config().get('openai_endpoint', '')
    
    def get_model_deployment(self) -> str:
        """Get model deployment name (convenience method)"""
        return self.get_config().get('model_deployment_name', '')


def update_configs_from_azure(environment: str = 'dev'):
    """
    Utility function to query Azure and print config
    Can be run manually to refresh configuration
    
    Usage:
        python -m core.configs.config_loader dev
    """
    try:
        loader = AzureConfigLoader(environment=environment)
        config = loader.get_config()
        
        print(f"\n=== {environment.upper()} Environment Configuration ===")
        for key, value in config.items():
            print(f"{key}: {value}")
        
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


if __name__ == '__main__':
    import sys
    env = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    update_configs_from_azure(env)
