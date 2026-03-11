resource "azurerm_user_assigned_identity" "func_app" {
  name                = var.func_app_msi_name
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_user_assigned_identity" "openai" {
  name                = var.openai_msi_name
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_user_assigned_identity" "search" {
  name                = var.search_msi_name
  location            = var.location
  resource_group_name = var.resource_group_name
}
