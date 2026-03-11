# BLS MCP Server - Deployment Guide

## Overview

This guide covers end-to-end deployment of the BLS MCP Server to Azure with Managed Identity authentication (no API keys required).

## Architecture

```
┌─────────────────┐
│  Function App   │
│  (Python 3.11)  │
│                 │
│  MSI Enabled ✓  │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌────────────────┐   ┌──────────────┐
│ Azure AI Search│   │ Azure OpenAI │
│                │   │   (Foundry)  │
│ MSI Auth ✓    │   │              │
│ No API keys   │   │ MSI Auth ✓   │
└────────────────┘   └──────────────┘
```

## Prerequisites

1. **Azure CLI**
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   az login
   ```

2. **Azure Functions Core Tools**
   ```bash
   npm install -g azure-functions-core-tools@4
   ```

3. **Python 3.11+**
   ```bash
   python3 --version
   ```

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

```bash
# From project root
./deploy.sh
```

This script:
- ✅ Deploys Bicep infrastructure
- ✅ Creates Azure AI Search with MSI
- ✅ Creates Azure OpenAI (Foundry) 
- ✅ Configures Function App with MSI
- ✅ Sets up RBAC role assignments
- ✅ Deploys function code

### Option 2: Manual Deployment

#### 1. Deploy Infrastructure

```bash
cd src/infra

# Deploy to Azure subscription
az deployment sub create \
    --location swedencentral \
    --template-file main.bicep \
    --parameters main.bicepparam
```

#### 2. Deploy Function Code

```bash
# Get function app name from deployment output
FUNC_APP_NAME="<your-function-app-name>"

# Deploy from project root
func azure functionapp publish $FUNC_APP_NAME --python
```

## Configuration

### Environment Variables (Set Automatically)

The Function App is configured with these settings via Bicep:

| Variable | Description | Set By |
|----------|-------------|--------|
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | Bicep |
| `AZURE_CLIENT_ID` | MSI Client ID | Bicep |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID | Bicep |
| `FUNCTIONS_WORKER_RUNTIME` | Python runtime | Bicep |

### Authentication Flow

```
Function App (MSI)
    ↓ (uses DefaultAzureCredential)
    ↓
Azure AI Search (accepts MSI)
    ↓ (RBAC roles assigned)
    ↓
✅ Access granted (no API keys!)
```

**RBAC Roles Assigned:**
- `Search Index Data Contributor` - Read/write index data
- `Search Service Contributor` - Manage indexes

## Post-Deployment Steps

### 1. Initialize Data

Run the initialization script to populate Azure AI Search:

```bash
# Option A: From local machine (requires AZURE_SEARCH_ENDPOINT)
export AZURE_SEARCH_ENDPOINT="https://<search-name>.search.windows.net"
python scripts/initialize_data.py --start-year 2020

# Option B: From Azure Portal via Function App Console
# Navigate to: Function App > Console
# Run: python scripts/initialize_data.py --start-year 2020
```

### 2. Verify Deployment

```bash
# Test function endpoint
FUNC_URL="<function-app-url>"
curl "$FUNC_URL/api/health"

# Expected response:
# {"status": "healthy", "timestamp": "2026-02-27T16:00:00Z"}
```

### 3. Test RAG System

```python
# Test from Python
import requests

response = requests.post(
    f"{FUNC_URL}/api/query",
    json={"query": "What is the unemployment rate in California?"}
)
print(response.json())
```

## Infrastructure Components

### Resources Created

| Resource | Type | Purpose |
|----------|------|---------|
| Resource Group | `Microsoft.Resources/resourceGroups` | Container for all resources |
| Function App | `Microsoft.Web/sites` | Hosts BLS MCP Server |
| App Service Plan | `Microsoft.Web/serverfarms` | Consumption plan (Y1) |
| Storage Account | `Microsoft.Storage/storageAccounts` | Function storage |
| Azure AI Search | `Microsoft.Search/searchServices` | Vector store for RAG |
| Azure OpenAI | `Microsoft.CognitiveServices/accounts` | LLM (Foundry) |
| Managed Identities | `Microsoft.ManagedIdentity/userAssignedIdentities` | MSI for each service |

### Cost Estimate (Monthly)

| Service | Tier | Estimated Cost |
|---------|------|----------------|
| Functions | Consumption (Y1) | ~$0-10 |
| Azure AI Search | Basic | ~$75 |
| Azure OpenAI | Pay-as-you-go | Variable |
| Storage | Standard LRS | ~$1 |
| **Total** | | **~$76-100/month** |

## Updating the Deployment

### Update Infrastructure

```bash
cd src/infra
az deployment sub create \
    --location swedencentral \
    --template-file main.bicep \
    --parameters main.bicepparam
```

### Update Function Code Only

```bash
func azure functionapp publish $FUNC_APP_NAME --python
```

## Monitoring

### View Logs

```bash
# Stream logs in real-time
func azure functionapp logstream $FUNC_APP_NAME
```

### Application Insights (Optional)

Uncomment in `requirements.txt`:
```python
azure-monitor-opentelemetry
```

Then redeploy the function.

## Troubleshooting

### Issue: "Authentication failed"

**Cause:** MSI not properly configured or RBAC roles not assigned

**Solution:**
```bash
# Verify MSI is enabled
az functionapp identity show -n $FUNC_APP_NAME -g $RESOURCE_GROUP

# Check role assignments
az role assignment list \
    --assignee <principal-id> \
    --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>
```

### Issue: "Index not found"

**Cause:** Data not initialized

**Solution:**
```bash
# Run initialization script
python scripts/initialize_data.py --start-year 2020
```

### Issue: "Module not found"

**Cause:** Dependencies not installed

**Solution:**
```bash
# Install locally
pip install -r src/requirements.txt

# Redeploy
func azure functionapp publish $FUNC_APP_NAME --python
```

## Security Best Practices

✅ **Implemented:**
- Managed Identity (no API keys in code)
- `disableLocalAuth: true` on Azure AI Search
- RBAC-based access control
- TLS 1.2 minimum
- HTTPS only

⚠️ **Recommended:**
- Enable Application Insights
- Set up Azure Monitor alerts
- Configure diagnostic logs
- Implement rate limiting
- Use Azure Key Vault for secrets (if needed)

## Local Development

For local testing with MSI:

```bash
# Login to Azure
az login

# Set environment variables
export AZURE_SEARCH_ENDPOINT="https://<search-name>.search.windows.net"
export AZURE_SUBSCRIPTION_ID="<your-subscription-id>"

# Use DefaultAzureCredential (will use your local Azure CLI credentials)
python src/function_app.py
```

## Cleanup

To delete all resources:

```bash
# Delete resource group (removes everything)
az group delete -n <resource-group-name> --yes
```

## Support

- BLS API Documentation: https://www.bls.gov/developers/
- Azure Functions: https://docs.microsoft.com/azure/azure-functions/
- Azure AI Search: https://docs.microsoft.com/azure/search/
- Semantic Kernel: https://github.com/microsoft/semantic-kernel

## License

MIT License - see LICENSE file for details
