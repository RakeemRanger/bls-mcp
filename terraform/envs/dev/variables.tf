variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "northeurope"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "func_app_name" {
  description = "Name of the Azure Function App"
  type        = string
}

variable "func_app_plan_name" {
  description = "Name of the App Service Plan for the Function App"
  type        = string
}

variable "func_app_user_assigned_msi_name" {
  description = "Name of the user-assigned managed identity for the Function App"
  type        = string
}

variable "openai_account_name" {
  description = "Name of the Azure OpenAI Cognitive Services account"
  type        = string
}

variable "openai_account_msi_name" {
  description = "Name of the user-assigned managed identity for the OpenAI account"
  type        = string
}

variable "model_deployment_name" {
  description = "Name of the model deployment inside the OpenAI account"
  type        = string
  default     = "gpt-4o"
}

variable "model_name" {
  description = "OpenAI model name"
  type        = string
  default     = "gpt-4o"
}

variable "model_version" {
  description = "OpenAI model version"
  type        = string
  default     = "2024-08-06"
}

variable "deployment_capacity" {
  description = "Capacity (thousands of tokens per minute) for the model deployment"
  type        = number
  default     = 10
}

variable "environment_name" {
  description = "Environment name tag passed to the Function App (dev/prod)"
  type        = string
  default     = "dev"
}

variable "azure_ai_search_name" {
  description = "Name of the Azure AI Search service"
  type        = string
}

variable "azure_ai_search_msi_name" {
  description = "Name of the user-assigned managed identity for Azure AI Search"
  type        = string
}

variable "app_insights_name" {
  description = "Name of the Application Insights component"
  type        = string
}

variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics workspace backing Application Insights"
  type        = string
}
