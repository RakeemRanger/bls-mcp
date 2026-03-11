variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "func_app_name" {
  description = "Name of the Function App"
  type        = string
}

variable "func_app_plan_name" {
  description = "Name of the App Service Plan"
  type        = string
}

variable "func_app_msi_id" {
  description = "Resource ID of the Function App user-assigned MSI"
  type        = string
}

variable "func_app_msi_client_id" {
  description = "Client ID of the Function App user-assigned MSI"
  type        = string
}

variable "environment_name" {
  description = "Environment name (dev/prod)"
  type        = string
  default     = "dev"
}

variable "azure_search_endpoint" {
  description = "Azure AI Search endpoint URL"
  type        = string
}

variable "openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  type        = string
}

variable "model_deployment_name" {
  description = "Name of the model deployment"
  type        = string
}

variable "app_insights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}
