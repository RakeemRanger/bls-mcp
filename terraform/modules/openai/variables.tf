variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "openai_account_name" {
  description = "Name of the Azure OpenAI Cognitive Services account"
  type        = string
}

variable "openai_account_msi_id" {
  description = "Resource ID of the user-assigned MSI for the OpenAI account"
  type        = string
}

variable "model_deployment_name" {
  description = "Name of the model deployment"
  type        = string
}

variable "model_name" {
  description = "OpenAI model name"
  type        = string
  default     = "gpt-4.1"
}

variable "model_version" {
  description = "OpenAI model version"
  type        = string
  default     = "2025-04-14"
}

variable "deployment_capacity" {
  description = "Capacity (thousands of tokens per minute)"
  type        = number
  default     = 50
}
