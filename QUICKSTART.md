# BLS MCP Server - Quick Start

## 🚀 Deploy in 2 Steps

### 1. Deploy Infrastructure

```bash
./deploy.sh
```

### 2. Initialize Data

```bash
python scripts/initialize_data.py --start-year 2020
```

## ✅ What You Get

- **Azure Function App** (Python 3.11, Consumption Plan)
- **Azure AI Search** (Basic tier, MSI authentication)
- **Azure OpenAI** (Foundry, GPT-4o)
- **RAG Pipeline** (Retrieval → Augmentation → Generation)
- **Managed Identity** (No API keys!)
- **RBAC** (Least privilege access)

## 🔐 Security

- ✅ MSI Authentication (no secrets in code)
- ✅ Azure AI Search with `disableLocalAuth: true`
- ✅ RBAC role assignments
- ✅ TLS 1.2+ only

## 📊 Architecture

```
User Query
    ↓
Function App (MSI)
    ↓
Semantic Kernel
    ↓
RAG Pipeline
    ├─→ Azure AI Search (metadata) ──→ Find relevant series
    ├─→ Azure AI Search (data) ─────→ Get time series values
    └─→ Azure OpenAI ──────────────→ Generate response
    ↓
Formatted Answer
```

## 🧪 Test

```bash
# Get function URL from deployment output
FUNC_URL="<your-function-url>"

# Test query
curl -X POST "$FUNC_URL/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is California unemployment rate?"}'
```

## 📚 Full Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [RAG_IMPLEMENTATION.md](RAG_IMPLEMENTATION.md) - RAG details

## 💰 Cost Estimate

~$76-100/month for Basic tier with:
- Function App (Consumption): ~$0-10
- Azure AI Search (Basic): ~$75
- Storage: ~$1
- Azure OpenAI: Pay-as-you-go

## 🛠️ Requirements

- Azure CLI
- Azure Functions Core Tools
- Python 3.11+
- Active Azure subscription

## 📝 Features

✅ RAG pipeline with Azure AI Search  
✅ Semantic Kernel integration  
✅ Managed Identity (MSI) authentication  
✅ Predictive analysis capabilities  
✅ Two-stage retrieval (metadata → data)  
✅ Timer trigger for monthly updates  
✅ Query classification (factual vs predictive)  
✅ Automatic trend sorting  

---

**Ready to deploy?** Run `./deploy.sh` 🚀
