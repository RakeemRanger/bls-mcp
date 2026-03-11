output "search_resource_id" {
  description = "Resource ID of the AI Search service"
  value       = azurerm_search_service.main.id
}

output "search_endpoint" {
  description = "AI Search endpoint URL"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_name" {
  description = "Name of the AI Search service"
  value       = azurerm_search_service.main.name
}
