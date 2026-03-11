output "resource_group_id" {
  description = "Resource group resource ID"
  value       = azurerm_resource_group.main.id
}

output "openai_endpoint" {
  description = "Azure OpenAI account endpoint"
  value       = module.openai.openai_endpoint
}

output "func_app_name" {
  description = "Function App name"
  value       = module.function_app.func_app_name
}

output "func_app_url" {
  description = "Function App HTTPS URL"
  value       = module.function_app.func_app_url
}

output "search_resource_id" {
  description = "Azure AI Search resource ID"
  value       = module.search.search_resource_id
}

output "search_endpoint" {
  description = "Azure AI Search endpoint URL"
  value       = module.search.search_endpoint
}

output "app_insights_connection_string" {
  description = "Application Insights connection string"
  value       = module.monitoring.app_insights_connection_string
  sensitive   = true
}
