variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "search_name" {
  description = "Name of the Azure AI Search service"
  type        = string
}

variable "search_msi_id" {
  description = "Resource ID of the user-assigned MSI for AI Search"
  type        = string
}
