# BLS MCP Server

Model Context Protocol (MCP) server for accessing and analyzing Bureau of Labor Statistics data through AI-powered RAG (Retrieval-Augmented Generation) pipeline. Enables LLMs to query, interpret, and predict BLS economic indicators with contextual analysis.

## 🎯 Overview

Serverless MCP implementation that indexes Bureau of Labor Statistics time series data (unemployment, employment, labor force) from bls.gov and provides intelligent analysis through Semantic Kernel orchestration with Azure AI Search vector storage.

## ✨ Features

- ✅ **RAG Pipeline**: Three-layer retrieval → augmentation → generation
- ✅ **Predictive Analysis**: Historical trend-based forecasting
- ✅ **Semantic Search**: Azure AI Search with vector embeddings
- ✅ **Auto-Updates**: Monthly timer trigger for new BLS data
- ✅ **MSI Authentication**: No API keys, Managed Identity only
- ✅ **RBAC Security**: Least privilege access control
- ✅ **Complete Coverage**: All US states, DC, Puerto Rico

## 🏗️ Architecture

```
User Query
    ↓
Azure Function App (Python 3.11)
    ↓
Semantic Kernel
    ↓
RAG Pipeline
    ├─→ Azure AI Search (metadata) ──→ Find series
    ├─→ Azure AI Search (data) ─────→ Get values
    └─→ Azure OpenAI ──────────────→ Generate answer
    ↓
Response (with predictions & trends)
```

**Components**:
- **Hosting**: Azure Functions (Consumption Plan Y1)
- **Authentication**: Managed Identity (MSI) - no API keys
- **AI Orchestration**: Semantic Kernel
- **Vector Store**: Azure AI Search (Basic tier)
- **LLM**: Azure OpenAI (Foundry, GPT-4o)
- **Data Source**: Bureau of Labor Statistics API
- **IaC**: Bicep with RBAC role assignments

## 🚀 Quick Start

### Prerequisites
```bash
# Azure CLI
az --version

# Azure Functions Core Tools
func --version

# Python 3.11+
python3 --version
```

### Deploy (2 Steps)

#### 1. Deploy Infrastructure & Code
```bash
./deploy.sh
```

#### 2. Initialize Data
```bash
python scripts/initialize_data.py --start-year 2020
```

**That's it!** 🎉

### Test
```bash
# Get function URL from deployment output
FUNC_URL="<your-function-url>"

# Query unemployment data
curl -X POST "$FUNC_URL/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is California unemployment rate?"}'

# Predictive query
curl -X POST "$FUNC_URL/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Will California unemployment increase next month?"}'
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 2-minute deployment guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment documentation
- **[MSI_MIGRATION.md](MSI_MIGRATION.md)** - MSI authentication details & troubleshooting  
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture deep dive
- **[RAG_IMPLEMENTATION.md](RAG_IMPLEMENTATION.md)** - RAG pipeline details
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Pre-deployment validation

## 🔐 Security

- ✅ **No API Keys**: Managed Identity (MSI) only
- ✅ **RBAC**: Function App → Azure AI Search (least privilege)
- ✅ **Entra ID Auth**: disableLocalAuth enabled on search
- ✅ **TLS 1.2+**: Enforced on all services
- ✅ **Audit Logs**: Full Entra ID audit trail

### RBAC Roles Assigned
| Role | Purpose |
|------|---------|
| Search Index Data Contributor | Read/write search indexes |
| Search Service Contributor | Manage search service |

## 🛠️ Tech Stack

**Runtime & Hosting**:
- Python 3.11
- Azure Functions (Consumption Plan)
- Serverless execution

**AI/ML**:
- Semantic Kernel (LLM orchestration)
- Azure OpenAI (Foundry, GPT-4o)
- Azure AI Search (vector storage)

**Infrastructure**:
- Bicep (IaC)
- User-Assigned Managed Identities (3x)
- RBAC role assignments

**Data**:
- BLS.gov API (public data)
- Time series: 2020-present
- Monthly updates via timer trigger

## 📊 Cost Estimate

| Service | Tier | Monthly Cost |
|---------|------|--------------|
| Azure Functions | Y1 Consumption | ~$0-10 |
| Azure AI Search | Basic | ~$75 |
| Azure OpenAI | Pay-as-you-go | Variable |
| Storage | Standard LRS | ~$1 |
| **Total** | | **~$76-100** |

## 📁 Project Structure

```
bls-mcp/
├── deploy.sh                # Automated deployment script
├── azure.yaml               # Azure Developer CLI config
├── src/
│   ├── function_app.py      # Function app entry point
│   ├── requirements.txt     # Python dependencies
│   ├── core/
│   │   ├── kernel.py        # Semantic Kernel setup
│   │   ├── rag/             # RAG pipeline
│   │   │   ├── retrieval/   # Azure AI Search queries
│   │   │   ├── augmented/   # Context formatting
│   │   │   ├── generation/  # System prompts
│   │   │   └── data/        # Vector store manager
│   │   ├── tools/           # Kernel functions
│   │   │   └── bls_data_tool.py  # RAG integration
│   │   └── configs/
│   │       └── bls_series.json   # Series metadata
│   └── infra/               # Bicep IaC
│       ├── main.bicep       # Orchestrator
│       ├── main.bicepparam  # Parameters
│       ├── rbac/            # RBAC role assignments
│       ├── identity/        # Managed identities
│       ├── app/             # Function App
│       ├── azureSearch/     # Azure AI Search
│       └── foundry/         # Azure OpenAI
├── scripts/
│   └── initialize_data.py   # Bulk data loader
└── docs/
    ├── QUICKSTART.md
    ├── DEPLOYMENT.md
    ├── MSI_MIGRATION.md
    ├── ARCHITECTURE.md
    └── RAG_IMPLEMENTATION.md
```

## 🔧 Local Development

### Setup
```bash
# Clone repository
git clone <repo-url>
cd bls-mcp

# Create virtual environment
python3 -m venv blsvenv
source blsvenv/bin/activate

# Install dependencies
pip install -r src/requirements.txt
```

### Configure
```bash
# Authenticate with Azure (for MSI)
az login

# Set search endpoint
export AZURE_SEARCH_ENDPOINT="https://your-search.search.windows.net"
```

### Run Locally
```bash
cd src
func start
```

## 🧪 Testing

### Test RAG Pipeline
```bash
python test_rag.py
```

### Test Vector Store
```bash
python src/core/rag/data/vector_store_manager.py
```

### Test Kernel Integration
```python
from src.core.kernel import get_kernel

kernel = await get_kernel()
result = await kernel.invoke("What is California unemployment?")
print(result)
```

## 📈 Supported Queries

### Factual
- "What is the unemployment rate in California?"
- "Show me Texas employment numbers"
- "Compare Florida and New York unemployment"

### Predictive
- "Will California unemployment increase next month?"
- "Based on the trend, what will Texas employment be?"
- "Is unemployment in Florida seasonal?"

### Analytical
- "Which state has the highest unemployment?"
- "Show labor force trends for Nevada"
- "What's the pattern in Arizona employment?"

## 🔄 Data Updates

**Automatic**: Timer trigger runs monthly (1st of each month)
```python
@app.schedule(schedule="0 0 0 1 * *", ...)
async def monthly_update(timer: func.TimerRequest):
    # Fetches latest BLS data
    # Updates Azure AI Search indexes
```

**Manual**: Run initialization script
```bash
python scripts/initialize_data.py --start-year 2020
```

## 🐛 Troubleshooting

### Authentication Failed
```bash
# Verify MSI
az functionapp identity show -g <rg> -n <func>

# Check RBAC
az role assignment list --assignee <msi-principal-id>
```

### Index Not Found
```bash
# Initialize data
python scripts/initialize_data.py --start-year 2020
```

### Import Errors
```bash
# Install dependencies
pip install -r src/requirements.txt
```

See [MSI_MIGRATION.md](MSI_MIGRATION.md) for comprehensive troubleshooting.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📝 License

MIT License - see LICENSE file for details

## 🔗 Links

- [BLS API Documentation](https://www.bls.gov/developers/)
- [Azure Functions Python](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel)
- [Azure AI Search](https://docs.microsoft.com/azure/search/)
- [Managed Identities](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)

---

**Ready to deploy?** → [QUICKSTART.md](QUICKSTART.md) 🚀
│   │   └── kernel.py        # Semantic Kernel configuration
│   └── infra/               # Infrastructure definitions
│       ├── main.bicep       # Main deployment template
│       ├── app/             # Function app module
│       └── identity/        # Managed identity module
```