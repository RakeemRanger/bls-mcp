locals {
  search_index_data_contributor_role_id = "8ebe5a00-799e-43f5-93ac-243d3dce84a7"
  search_service_contributor_role_id    = "7ca78c08-252a-4471-8644-bb5ff32d4ba0"
  monitoring_metrics_publisher_role_id  = "3913510d-42f4-4e42-8a64-420c390055eb"
}

# Grant Function App MSI: Search Index Data Contributor
resource "azurerm_role_assignment" "search_index_data_contributor" {
  scope              = var.resource_group_id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${local.search_index_data_contributor_role_id}"
  principal_id       = var.func_app_msi_principal_id
  principal_type     = "ServicePrincipal"
}

# Grant Function App MSI: Search Service Contributor
resource "azurerm_role_assignment" "search_service_contributor" {
  scope              = var.resource_group_id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${local.search_service_contributor_role_id}"
  principal_id       = var.func_app_msi_principal_id
  principal_type     = "ServicePrincipal"
}

# Grant Function App MSI: Monitoring Metrics Publisher
resource "azurerm_role_assignment" "monitoring_metrics_publisher" {
  scope              = var.resource_group_id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${local.monitoring_metrics_publisher_role_id}"
  principal_id       = var.func_app_msi_principal_id
  principal_type     = "ServicePrincipal"
}
