output "func_app_msi_id" {
  description = "Resource ID of the Function App managed identity"
  value       = azurerm_user_assigned_identity.func_app.id
}

output "func_app_msi_principal_id" {
  description = "Principal ID of the Function App managed identity"
  value       = azurerm_user_assigned_identity.func_app.principal_id
}

output "func_app_msi_client_id" {
  description = "Client ID of the Function App managed identity"
  value       = azurerm_user_assigned_identity.func_app.client_id
}

output "openai_msi_id" {
  description = "Resource ID of the OpenAI managed identity"
  value       = azurerm_user_assigned_identity.openai.id
}

output "search_msi_id" {
  description = "Resource ID of the AI Search managed identity"
  value       = azurerm_user_assigned_identity.search.id
}
