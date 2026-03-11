resource "azurerm_cognitive_account" "openai" {
  name                = var.openai_account_name
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name         = var.openai_account_name
  local_auth_enabled            = false
  public_network_access_enabled = true

  identity {
    type         = "UserAssigned"
    identity_ids = [var.openai_account_msi_id]
  }
}

resource "azurerm_cognitive_deployment" "model" {
  name                 = var.model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }

  sku {
    name     = "Standard"
    capacity = var.deployment_capacity
  }
}
