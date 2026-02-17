# BLS MCP Server — Architecture

## Overview

The BLS MCP Server exposes Bureau of Labor Statistics data through the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP), hosted on Azure Functions. An LLM (Anthropic Claude) interprets natural language queries, calls BLS API tools via Semantic Kernel, and returns formatted answers.

```
┌──────────────┐     MCP/HTTP      ┌─────────────────────┐
│   VS Code    │ ─────────────────► │  Azure Functions    │
│  (MCP Client)│ ◄───────────────── │  (MCP Tool Trigger) │
└──────────────┘                    └────────┬────────────┘
                                             │
                                    ┌────────▼────────────┐
                                    │  Semantic Kernel     │
                                    │  + Anthropic Claude  │
                                    └────────┬────────────┘
                                             │ tool calls
                              ┌──────────────┼──────────────┐
                              ▼              ▼              ▼
                        ┌──────────┐  ┌──────────┐  ┌──────────┐
                        │ BLS API  │  │  Table    │  │  Time    │
                        │ (v1/v2)  │  │ Storage   │  │  Plugin  │
                        └──────────┘  │  (cache)  │  └──────────┘
                                      └──────────┘
```

## Key Design Decisions

### 1. Flex Consumption Plan (FC1) — not Y1 Dynamic

**Choice:** Azure Functions Flex Consumption (FC1)
**Why:**
- Scale-to-zero billing (pay only when running)
- Better cold start performance than legacy Consumption (Y1)
- Native support for managed identity & blob-based deployment
- Microsoft's recommended plan for new function apps
- **Estimated cost:** ~$0-5/month at low traffic

### 2. Local BLS Search — not Azure AI Search

**Choice:** In-memory keyword matching over the `BLS_SERIES` dictionary
**Rejected:** Azure AI Search ($75+/month minimum)
**Why:**
- Our catalog is ~36 national series + on-demand state/county LAUS data
- Simple keyword matching is sufficient at this scale
- The LLM (Claude) handles ambiguity and intent mapping
- Cost savings: **$0 vs $75+/month**

### 3. Azure Table Storage — persistent BLS cache

**Choice:** Azure Table Storage for caching fetched BLS data
**Rejected:** Cosmos DB ($25+/month), Redis Cache ($15+/month)
**Why:**
- BLS data is time-series with natural partition key (series_id) and row key (year+period)
- Read-heavy workload with infrequent writes (BLS publishes monthly/quarterly)
- **Estimated cost:** ~$0.05/month (pennies)
- Table Storage is included in the Storage Account already required by Functions

### 4. Anthropic Claude via Semantic Kernel

**Choice:** Semantic Kernel orchestration with Anthropic Claude (Sonnet)
**Why:**
- Semantic Kernel provides structured tool calling with `@kernel_function` decorators
- `FunctionChoiceBehavior.Auto()` lets Claude decide which BLS tools to invoke
- Per-session chat history enables multi-turn conversations
- Plugin architecture keeps BLS tools decoupled from the kernel

### 5. BLS API v1/v2 Auto-Selection

**Choice:** Auto-detect and use v2 API when `BLS_API_KEY` is set
**Why:**
- v1 (no key): 25 series per request, 25 requests/day — good for dev
- v2 (with key): 50 series per request, 500 requests/day — needed for prod
- Free API key from [BLS registration](https://data.bls.gov/registrationEngine/)
- Client auto-selects URL and batch size based on env var

## Data Layers

### National Series (~36 pre-defined)
| Category | Examples |
|----------|----------|
| Unemployment | Rate, count, labor force participation |
| CPI | All items, food, energy, shelter, medical |
| Employment | Nonfarm payrolls, private sector |
| Wages | Average hourly/weekly earnings |
| JOLTS | Job openings, hires, separations, quits |
| PPI | All commodities, final demand |

### State-Level LAUS
- All 50 states + DC + Puerto Rico
- Series format: `LASS{FIPS}00000000000{measure}`
- Measures: unemployment rate (03), unemployment count (04), employment (05), labor force (06)
- Resolved by state name, abbreviation, or FIPS code

### County-Level LAUS
- Series format: `LAUCN{5-digit-FIPS}00000000{measure}`
- Same measures as state level
- Requires 5-digit county FIPS code

## Infrastructure

### Azure Resources (per environment)

| Resource | SKU | Purpose | Est. Cost |
|----------|-----|---------|-----------|
| Function App | Flex Consumption (FC1) | Host MCP server | ~$0-5/mo |
| Storage Account | Standard LRS | Functions runtime + Table cache | ~$1/mo |
| App Insights | Free tier (5 GB/mo) | Monitoring & diagnostics | $0 |
| Log Analytics | Free tier (5 GB/mo) | Centralized logging | $0 |
| User Assigned Identity | — | RBAC for storage/insights | $0 |

**Total estimated cost: ~$1-6/month**

### Security
- **Managed Identity:** User-assigned identity for storage/insights access (no connection strings)
- **Shared Key Disabled:** Storage account uses RBAC-only authentication
- **TLS 1.2:** Minimum TLS version enforced
- **App Insights Local Auth Disabled:** AAD-only authentication
- **Secrets:** `ANTHROPIC_API_KEY` and `BLS_API_KEY` passed as secure parameters, stored as app settings

### CI/CD (GitHub Actions)

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `deploy-infra.yml` | Push to `infra/**` on main/dev | Deploys Bicep to create/update Azure resources |
| `deploy-app.yml` | Push to `src/**` on main/dev | Builds Python deps, deploys function app code |

Both workflows use **OIDC federated credentials** (no stored secrets for Azure auth).

**Branch → Environment mapping:**
- `dev` branch → `dev` environment
- `main` branch → `prod` environment

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal / app registration client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `BLS_API_KEY` | BLS API registration key (optional) |

## Project Structure

```
bls-mcp/
├── .github/workflows/
│   ├── deploy-infra.yml      # Infrastructure deployment
│   └── deploy-app.yml        # Function app deployment
├── docs/
│   └── architecture.md       # This file
├── infra/
│   ├── app/
│   │   ├── api.bicep          # Function App module (Flex Consumption)
│   │   └── rbac.bicep         # RBAC role assignments
│   ├── abbreviations.json     # Resource naming conventions
│   ├── main.bicep             # Orchestrator (subscription-scoped)
│   └── main.parameters.json   # Parameter template
├── src/
│   ├── core/
│   │   ├── lib/
│   │   │   ├── anthropic_details.py  # Anthropic API wrapper
│   │   │   └── bls_client.py         # BLS API client + cache + FIPS
│   │   ├── tools/
│   │   │   └── bls_tools.py          # Semantic Kernel BLS plugin
│   │   └── kernel.py                 # BLSKernel orchestrator
│   ├── function_app.py               # Azure Functions entry point
│   ├── host.json                     # Functions host config + MCP extension
│   ├── local.settings.json           # Local dev settings (git-ignored)
│   └── requirements.txt              # Python dependencies
├── .gitignore
└── README.md
```

## MCP Endpoint

- **Local:** `http://localhost:7071/runtime/webhooks/mcp`
- **Deployed:** `https://<func-app-name>.azurewebsites.net/runtime/webhooks/mcp`

The `/runtime/webhooks/mcp` path is fixed by the Azure Functions MCP extension and cannot be changed.

## Security Roadmap

### Phase 1 — Deploy (v1, Current)

No auth. The server is accessible via the Function App's default URL.

**Rationale:** BLS data is publicly available, the server is low-traffic, and the priority is getting a working deployment. Auth adds complexity with zero benefit at this stage.

```
Client (VS Code) ──► Azure Function App (MCP)
```

### Phase 2 — Authentication (v2)

Add **Microsoft Entra ID (EasyAuth)** on the Function App.

**What it does:**
- Function App rejects any request without a valid Entra-issued JWT
- Zero code changes — configured entirely via Function App settings / Bicep
- Clients authenticate via standard OAuth 2.0 authorization code flow

**What it doesn't do:**
- No rate limiting, no WAF, no DDoS protection

```
Client ──► Entra ID (get token) ──► Azure Function App (validates JWT)
```

### Phase 3 — API Gateway + Edge Protection (v3)

Add **Azure API Management (APIM)** and **Azure Front Door** in front of the Function App. Remove EasyAuth (APIM takes over JWT validation).

```
Internet
   │
   ▼
┌──────────────────────────┐
│   Azure Front Door        │  DDoS (L3/L4/L7), WAF, geo-filtering
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   Azure API Management    │  JWT validation, rate limiting,
│                          │  subscription keys, analytics
└──────────┬───────────────┘
           │  (private endpoint / VNet)
           ▼
┌──────────────────────────┐
│   Function App (MCP)      │  Network-locked: accepts traffic
│                          │  only from APIM
└──────────────────────────┘
```

**Layer responsibilities:**

| Layer | DDoS | WAF | Auth (JWT) | Rate Limit | Analytics | Network Lock |
|-------|------|-----|------------|------------|-----------|-------------|
| Front Door | ✅ | ✅ | — | — | — | `X-Azure-FDID` header validation |
| APIM | — | — | ✅ `validate-jwt` | ✅ | ✅ | Only accepts Front Door traffic |
| Function App | — | — | — | — | — | Only accepts APIM traffic |

**Key design decisions:**
- **EasyAuth removed** — APIM's `validate-jwt` inbound policy handles token validation, making EasyAuth redundant
- **Network lockdown is critical** — Without it, someone could bypass APIM and hit the Function directly, defeating the auth layer
- **Front Door → APIM** trust is enforced via `X-Azure-FDID` header validation in APIM policy
- **APIM → Function App** trust is enforced via VNet integration + private endpoints (or access restrictions to APIM IPs)

**Estimated additional cost (Phase 3):**

| Resource | SKU | Est. Cost |
|----------|-----|-----------|
| Front Door | Standard | ~$35/mo + per-request |
| API Management | Consumption v2 | ~$3.50 per million calls |

## Future Considerations

- **Custom Domain:** Map a friendly URL (e.g., `bls.yourdomain.com`) via Azure Front Door
- **VNet Integration:** Add private networking for APIM → Function App communication (Phase 3)
- **Azure AI Search:** Consider if the series catalog grows significantly (100+ series)
- **Cosmos DB:** Migrate from Table Storage if query patterns become complex
- **Dynamic Client Registration:** Support MCP-spec OAuth with RFC 7591 for third-party clients
- **Multi-region:** Deploy Front Door with multiple backend pools for HA
