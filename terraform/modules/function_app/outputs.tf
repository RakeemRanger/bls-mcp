output "func_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.main.name
}

output "func_app_url" {
  description = "Function App HTTPS URL"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}
