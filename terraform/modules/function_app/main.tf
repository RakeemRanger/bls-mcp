resource "random_id" "storage_suffix" {
  keepers = {
    resource_group_name = var.resource_group_name
  }
  byte_length = 6
}

resource "azurerm_storage_account" "func_app" {
  name                     = "blsstorage${random_id.storage_suffix.hex}"
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"
}

resource "azurerm_service_plan" "func_app" {
  name                = var.func_app_plan_name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "main" {
  name                = var.func_app_name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.func_app.id

  storage_account_name       = azurerm_storage_account.func_app.name
  storage_account_access_key = azurerm_storage_account.func_app.primary_access_key

  public_network_access_enabled = true
  https_only                    = true

  site_config {
    minimum_tls_version = "1.2"

    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["*"]
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME            = "python"
    FUNCTIONS_EXTENSION_VERSION         = "~4"
    WEBSITE_CONTENTSHARE                = lower(var.func_app_name)

    ENVIRONMENT                         = var.environment_name
    AZURE_AI_INFERENCE_ENDPOINT         = var.openai_endpoint
    MODEL_DEPLOYMENT_NAME               = var.model_deployment_name
    AZURE_SUBSCRIPTION_ID               = var.subscription_id
    AZURE_SEARCH_ENDPOINT               = var.azure_search_endpoint
    AZURE_CLIENT_ID                     = var.func_app_msi_client_id
    BLS_DATA_RETRIEVAL_URL              = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    APPLICATIONINSIGHTS_AUTHENTICATION_STRING  = "Authorization=AAD;ClientId=${var.func_app_msi_client_id}"
    APPLICATIONINSIGHTS_CONNECTION_STRING      = var.app_insights_connection_string
    ApplicationInsightsAgent_EXTENSION_VERSION = "~3"
    InstrumentationEngine_EXTENSION_VERSION    = "disabled"
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [var.func_app_msi_id]
  }

  auth_settings_v2 {
    auth_enabled           = false
    unauthenticated_action = "AllowAnonymous"

    login {}
  }
}
