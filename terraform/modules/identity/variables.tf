variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "func_app_msi_name" {
  description = "Name of the Function App user-assigned managed identity"
  type        = string
}

variable "openai_msi_name" {
  description = "Name of the OpenAI account user-assigned managed identity"
  type        = string
}

variable "search_msi_name" {
  description = "Name of the AI Search user-assigned managed identity"
  type        = string
}
