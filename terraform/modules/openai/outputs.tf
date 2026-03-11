output "openai_account_id" {
  description = "Resource ID of the OpenAI Cognitive Services account"
  value       = azurerm_cognitive_account.openai.id
}

output "openai_endpoint" {
  description = "OpenAI account endpoint URL"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "deployment_name" {
  description = "Name of the model deployment"
  value       = azurerm_cognitive_deployment.model.name
}
