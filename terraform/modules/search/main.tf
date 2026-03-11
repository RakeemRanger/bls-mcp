resource "azurerm_search_service" "main" {
  name                = var.search_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "basic"
  replica_count       = 1
  semantic_search_sku = "free"

  local_authentication_enabled  = true
  public_network_access_enabled = true

  identity {
    type         = "UserAssigned"
    identity_ids = [var.search_msi_id]
  }
}
