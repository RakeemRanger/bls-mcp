# MSI Authentication Migration Guide

## 🎯 Summary of Changes

The BLS MCP Server now uses **Managed Identity (MSI)** authentication instead of API keys for Azure AI Search. This provides better security and eliminates secrets management.

## What Changed

### Before (API Key Authentication)
```python
# Required environment variables
AZURE_SEARCH_ENDPOINT = "https://..."
AZURE_SEARCH_API_KEY = "secret-key-here"

# Code usage
from azure.core.credentials import AzureKeyCredential

client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
)
```

### After (MSI Authentication)
```python
# Required environment variable (endpoint only)
AZURE_SEARCH_ENDPOINT = "https://..."

# Code usage
from azure.identity.aio import DefaultAzureCredential

client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    credential=DefaultAzureCredential()
)
```

## Files Modified

### 1. **vector_store_manager.py**
- ✅ Removed `AZURE_SEARCH_API_KEY` environment variable
- ✅ Changed from `AzureKeyCredential` to `DefaultAzureCredential`
- ✅ Updated all SearchClient instantiations (4 locations)
- ✅ Updated validation and error messages

### 2. **requirements.txt**
- ✅ Added `azure-identity` (already present)
- ✅ Kept `azure-search-documents>=11.4.0`

### 3. **Bicep Infrastructure**

**main.bicep:**
- ✅ Added RBAC role assignments:
  - `Search Index Data Contributor` (8ebe5a00...)
  - `Search Service Contributor` (7ca78c08...)
- ✅ Added `search_endpoint` output
- ✅ Added dependency on Azure Search for Function App

**identity/user_assigned.bicep:**
- ✅ Added `msi_principal_id` output
- ✅ Added `msi_client_id` output

**app/func_app.bicep:**
- ✅ Added `AZURE_SEARCH_ENDPOINT` app setting
- ✅ Added `AZURE_CLIENT_ID` app setting
- ✅ Added `func_app_msi_client_id` parameter

**azureSearch/azureAiSearch.bicep:**
- ✅ Already had `disableLocalAuth: true` (MSI only)
- ✅ Already configured for Entra ID authentication

### 4. **Deployment Configuration**
- ❌ Deleted: `dev_main.bicepparam`, `dev-config.json`
- ❌ Deleted: `prod_main.bicepparam`, `prod-config.json`
- ✅ Created: Single `main.bicepparam` for all environments
- ✅ Created: `deploy.sh` - Automated deployment script
- ✅ Created: `azure.yaml` - Azure Developer CLI config

### 5. **Documentation**
- ✅ Created: `DEPLOYMENT.md` - Complete deployment guide
- ✅ Created: `QUICKSTART.md` - 2-step quick start
- ✅ Created: `MSI_MIGRATION.md` - This file

## Environment Variables

### Production (Azure Function App)
These are set automatically by Bicep:

| Variable | Value | Source |
|----------|-------|--------|
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | Bicep output |
| `AZURE_CLIENT_ID` | Function App MSI Client ID | Bicep output |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID | Bicep builtin |

### Local Development
For testing locally with your Azure credentials:

```bash
# Authenticate with Azure CLI
az login

# Set search endpoint
export AZURE_SEARCH_ENDPOINT="https://your-search.search.windows.net"

# DefaultAzureCredential will use your Azure CLI credentials
python src/function_app.py
```

## RBAC Roles

The Function App's Managed Identity is automatically assigned these roles:

### Search Index Data Contributor
- **Role ID**: `8ebe5a00-799e-43f5-93ac-243d3dce84a7`
- **Permissions**: Read and write search index data
- **Scope**: Resource Group
- **Why**: Allows indexing BLS data and querying for RAG

### Search Service Contributor
- **Role ID**: `7ca78c08-252a-4471-8644-bb5ff32d4ba0`
- **Permissions**: Manage search service and indexes
- **Scope**: Resource Group
- **Why**: Allows creating/updating indexes during initialization

## Authentication Flow

```
┌──────────────────────────────────────────────────────────┐
│ 1. Function App starts                                   │
│    - Has User-Assigned MSI configured                    │
│    - AZURE_CLIENT_ID env var set                         │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 2. vector_store_manager.py imports DefaultAzureCredential │
│    - Detects MSI from AZURE_CLIENT_ID                    │
│    - No API key needed                                   │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 3. SearchClient gets OAuth token from Entra ID          │
│    - Uses MSI credentials                                │
│    - Token automatically refreshed                       │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 4. Azure AI Search validates token                      │
│    - Checks RBAC permissions                             │
│    - Grants access (no API key check)                    │
└──────────────────────────────────────────────────────────┘
```

## Security Benefits

### ✅ Before (API Keys)
- ❌ Keys stored in environment variables
- ❌ Keys in configuration files
- ❌ Key rotation required
- ❌ Keys could leak in logs/code
- ❌ Manual secret management

### ✅ After (MSI)
- ✅ No secrets to manage
- ✅ Automatic token rotation
- ✅ RBAC-based permissions
- ✅ Audit trail in Azure AD logs
- ✅ Zero-trust security model
- ✅ Can't accidentally commit keys

## Migration Steps (If Updating Existing Deployment)

### 1. Update Code
```bash
git pull  # Get latest code with MSI support
```

### 2. Redeploy Infrastructure
```bash
./deploy.sh
```

This will:
- Update Function App configuration
- Add RBAC role assignments
- Configure app settings with MSI Client ID
- Remove any API key references

### 3. Remove Old Secrets
```bash
# Remove from local environment
unset AZURE_SEARCH_API_KEY

# Remove from Function App settings (if any)
az functionapp config appsettings delete \
    -g <resource-group> \
    -n <function-app-name> \
    --setting-names AZURE_SEARCH_API_KEY
```

### 4. Verify
```bash
# Test locally
az login
python test_rag.py

# Test deployed function
curl "$FUNC_URL/api/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "What is California unemployment?"}'
```

## Troubleshooting

### Issue: "AuthenticationError: Authentication failed"

**Cause**: MSI not configured or RBAC roles not assigned

**Solution**:
```bash
# Check MSI is enabled
az functionapp identity show \
    -g <resource-group> \
    -n <function-app-name>

# Check role assignments
az role assignment list \
    --assignee <msi-principal-id>
```

### Issue: "DefaultAzureCredential failed to retrieve a token"

**Local Development:**
```bash
# Ensure you're logged in
az login
az account show
```

**Azure Function:**
```bash
# Verify MSI is assigned
az functionapp identity show -g <rg> -n <func>

# Verify AZURE_CLIENT_ID is set
az functionapp config appsettings list -g <rg> -n <func>
```

### Issue: "Search service returned an error: Unauthorized"

**Cause**: RBAC roles not assigned yet (propagation delay)

**Solution**:
```bash
# Role assignments can take up to 5 minutes to propagate
# Wait and retry, or manually assign:

az role assignment create \
    --assignee <msi-principal-id> \
    --role "Search Index Data Contributor" \
    --scope <search-resource-id>
```

## Testing MSI Authentication

### Test Script
```python
import os
import asyncio
from azure.search.documents.aio import SearchClient
from azure.identity.aio import DefaultAzureCredential

async def test_msi():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    async with SearchClient(
        endpoint=endpoint,
        index_name="bls-timeseries-data",
        credential=DefaultAzureCredential()
    ) as client:
        # If this succeeds, MSI is working!
        result = await client.search("California unemployment")
        print("✅ MSI authentication successful")
        return True

asyncio.run(test_msi())
```

## Rollback (Emergency)

If you need to rollback to API key authentication:

1. **Generate API key** in Azure Portal:
   - Azure AI Search → Settings → Keys
   - Copy Admin Key

2. **Update vector_store_manager.py**:
   ```python
   # Revert to AzureKeyCredential
   from azure.core.credentials import AzureKeyCredential
   
   client = SearchClient(
       endpoint=AZURE_SEARCH_ENDPOINT,
       credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))
   )
   ```

3. **Set API key**:
   ```bash
   export AZURE_SEARCH_API_KEY="<admin-key>"
   ```

4. **Enable local auth** on Azure AI Search:
   ```bash
   az search service update \
       -g <resource-group> \
       -n <search-name> \
       --disable-local-auth false
   ```

## References

- [Azure Identity Documentation](https://learn.microsoft.com/azure/developer/python/sdk/authentication-overview)
- [DefaultAzureCredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
- [Azure AI Search RBAC](https://learn.microsoft.com/azure/search/search-security-rbac)
- [Managed Identity Overview](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview)

## Support

Questions? Issues?
1. Check `DEPLOYMENT.md` for deployment troubleshooting
2. Review Azure Portal → Function App → Identity settings
3. Verify RBAC role assignments in Azure Portal
4. Check Application Insights logs for authentication errors
