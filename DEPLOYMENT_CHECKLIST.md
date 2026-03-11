# Pre-Deployment Checklist

## ✅ Code & Configuration

- [x] **vector_store_manager.py** - MSI authentication implemented
- [x] **requirements.txt** - azure-identity included
- [x] **Bicep files** - All 7 files present and valid
- [x] **Parameter file** - Single main.bicepparam created
- [x] **Dev/prod configs** - Deleted (consolidated)
- [x] **RBAC module** - search_rbac.bicep created
- [x] **Deployment script** - deploy.sh created and executable

## ✅ Bicep Validation

```bash
cd src/infra
az bicep build --file main.bicep
```
**Status**: ✅ Compilation successful

## ✅ Infrastructure Components

### Modules
- [x] `main.bicep` - Orchestrator
- [x] `identity/user_assigned.bicep` - MSI with outputs
- [x] `app/func_app.bicep` - Function App with settings
- [x] `azureSearch/azureAiSearch.bicep` - Search with MSI
- [x] `foundry/foundry.bicep` - Azure OpenAI
- [x] `rbac/search_rbac.bicep` - Role assignments

### Outputs
- [x] `search_endpoint` - For function app config
- [x] `msi_principal_id` - For RBAC
- [x] `msi_client_id` - For DefaultAzureCredential

### RBAC Roles
- [x] Search Index Data Contributor (8ebe5a00...)
- [x] Search Service Contributor (7ca78c08...)

## ✅ Documentation

- [x] **QUICKSTART.md** (2.2K) - 2-step deployment
- [x] **DEPLOYMENT.md** (7.1K) - Comprehensive guide
- [x] **MSI_MIGRATION.md** (11K) - Migration & troubleshooting
- [x] **E2E_SUMMARY.md** (8.2K) - What was done
- [x] **azure.yaml** (407) - Azure Developer CLI config
- [x] **deploy.sh** (2.0K, executable) - Deployment automation

## ✅ Security Features

- [x] **No API keys** - MSI only
- [x] **disableLocalAuth: true** - On Azure AI Search
- [x] **RBAC** - Least privilege roles
- [x] **TLS 1.2+** - Enforced
- [x] **Audit trail** - Via Entra ID logs

## 🎯 Ready to Deploy

### Prerequisites
```bash
# 1. Azure CLI installed
az --version

# 2. Logged in
az login
az account show

# 3. Azure Functions Core Tools
func --version

# 4. Python 3.11+
python3 --version
```

### Deploy Command
```bash
./deploy.sh
```

### Post-Deployment
```bash
# Initialize data
python scripts/initialize_data.py --start-year 2020

# Test
curl "$FUNC_URL/api/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "What is California unemployment?"}'
```

## 📊 Infrastructure to be Created

| Resource | SKU/Tier | Purpose |
|----------|----------|---------|
| Resource Group | N/A | Container |
| Function App | Consumption (Y1) | BLS MCP Server |
| Storage Account | Standard LRS | Function storage |
| Azure AI Search | Basic | Vector store |
| Azure OpenAI | Foundry | LLM (gpt-4o) |
| MSI (3x) | User-Assigned | Authentication |
| RBAC (2x) | Role Assignments | Search access |

**Estimated Cost**: ~$76-100/month

## 🔍 Validation Tests

### Test 1: Bicep Compilation
```bash
cd src/infra
az bicep build --file main.bicep --stdout > /dev/null
echo $?  # Should be 0
```
✅ **PASSED**

### Test 2: Python Imports
```bash
python3 -c "from src.core.rag.data.vector_store_manager import upsert_data_batch; print('OK')"
```
✅ **Expected**: OK

### Test 3: Deployment Script
```bash
[[ -x deploy.sh ]] && echo "Executable" || echo "Not executable"
```
✅ **PASSED**: Executable

### Test 4: Parameter File
```bash
grep -q "location.*=.*swedencentral" src/infra/main.bicepparam && echo "OK"
```
✅ **PASSED**

## ⚠️ Known Items

### Optional (Post-Deployment)
- [ ] Update README.md with MSI deployment instructions
- [ ] Enable Application Insights (uncomment in requirements.txt)
- [ ] Set up Azure Monitor alerts
- [ ] Configure cost alerts

### Not Blocking Deployment
- [ ] Update old documentation (RAG_IMPLEMENTATION.md, etc.) - New docs supersede

## 🚀 Go/No-Go Decision

**Status**: ✅ **GO - Ready for Deployment**

All critical components are in place:
- Code updated for MSI ✅
- Bicep validated ✅
- RBAC configured ✅
- Documentation complete ✅
- Deployment automation ready ✅

**Next Step**: Run `./deploy.sh`

---

**Deployment Guide**: See [QUICKSTART.md](QUICKSTART.md) or [DEPLOYMENT.md](DEPLOYMENT.md)
