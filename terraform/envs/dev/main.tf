terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

data "azurerm_subscription" "current" {}

# ── Resource Group ────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# ── Identity ──────────────────────────────────────────────────────────────────
module "identity" {
  source              = "../../modules/identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  func_app_msi_name   = var.func_app_user_assigned_msi_name
  openai_msi_name     = var.openai_account_msi_name
  search_msi_name     = var.azure_ai_search_msi_name
}

# ── Monitoring ────────────────────────────────────────────────────────────────
module "monitoring" {
  source                       = "../../modules/monitoring"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  app_insights_name            = var.app_insights_name
  log_analytics_workspace_name = var.log_analytics_workspace_name
}

# ── OpenAI ────────────────────────────────────────────────────────────────────
module "openai" {
  source                = "../../modules/openai"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  openai_account_name   = var.openai_account_name
  openai_account_msi_id = module.identity.openai_msi_id
  model_deployment_name = var.model_deployment_name
  model_name            = var.model_name
  model_version         = var.model_version
  deployment_capacity   = var.deployment_capacity
}

# ── AI Search ─────────────────────────────────────────────────────────────────
module "search" {
  source              = "../../modules/search"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  search_name         = var.azure_ai_search_name
  search_msi_id       = module.identity.search_msi_id
}

# ── Function App ──────────────────────────────────────────────────────────────
module "function_app" {
  source                         = "../../modules/function_app"
  location                       = azurerm_resource_group.main.location
  resource_group_name            = azurerm_resource_group.main.name
  func_app_name                  = var.func_app_name
  func_app_plan_name             = var.func_app_plan_name
  func_app_msi_id                = module.identity.func_app_msi_id
  func_app_msi_client_id         = module.identity.func_app_msi_client_id
  environment_name               = var.environment_name
  azure_search_endpoint          = module.search.search_endpoint
  openai_endpoint                = module.openai.openai_endpoint
  model_deployment_name          = var.model_deployment_name
  app_insights_connection_string = module.monitoring.app_insights_connection_string
  subscription_id                = data.azurerm_subscription.current.subscription_id
}

# ── RBAC ──────────────────────────────────────────────────────────────────────
module "rbac" {
  source                    = "../../modules/rbac"
  resource_group_id         = azurerm_resource_group.main.id
  subscription_id           = data.azurerm_subscription.current.subscription_id
  func_app_msi_principal_id = module.identity.func_app_msi_principal_id

  depends_on = [module.function_app]
}
