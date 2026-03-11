# Mirrors the values from src/infra/main.bicepparam
# Update subscription_id to match your Azure subscription

subscription_id              = "615d2787-abd7-4934-bde1-b00d7839cee8"
location                     = "swedencentral"
resource_group_name          = "bls-mcp-swedencentral-rg"

func_app_name                    = "bls-mcp-swedencentral-func"
func_app_plan_name               = "bls-mcp-swedencentral-func-app-plan"
func_app_user_assigned_msi_name  = "bls-mcp-swedencentral-func-msi"

openai_account_name          = "bls-mcp-swedencentral-openai"
openai_account_msi_name      = "bls-mcp-swedencentral-openai-msi"
model_deployment_name        = "gpt-4.1"
model_name                   = "gpt-4.1"
model_version                = "2025-04-14"
deployment_capacity          = 50

environment_name             = "dev"

azure_ai_search_name         = "bls-mcp-swedencentral-search"
azure_ai_search_msi_name     = "bls-mcp-swedencentral-search-msi"

app_insights_name            = "bls-mcp-swedencentral-appinsights"
log_analytics_workspace_name = "bls-mcp-swedencentral-logs"
