using 'main.bicep'

// Project naming configuration
var project_name = 'bls-mcp'
var location_name = 'swedencentral'
var naming_prefix = '${project_name}-${location_name}-'

// Resource parameters
param location = location_name
param resource_group_name = '${naming_prefix}rg'
param func_app_name = '${naming_prefix}func'
param func_app_plan_name = '${naming_prefix}func-app-plan'
param func_app_user_assigned_msi_name = '${naming_prefix}func-msi'
param openai_account_name = '${naming_prefix}openai'
param openai_account_msi_name = '${naming_prefix}openai-msi'
param model_deployment_name = 'gpt-4.1'
param environment_name = 'dev'
param azure_ai_search_name = '${naming_prefix}search'
param azure_ai_search_msi_name = '${naming_prefix}search-msi'
param azure_ai_search_sku = 'standard'
param app_insights_name = '${naming_prefix}appinsights'
param log_analytics_workspace_name = '${naming_prefix}logs'
