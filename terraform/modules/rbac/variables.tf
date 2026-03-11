variable "resource_group_id" {
  description = "Resource ID of the resource group (used as RBAC scope)"
  type        = string
}

variable "subscription_id" {
  description = "Azure subscription ID (used to build role definition IDs)"
  type        = string
}

variable "func_app_msi_principal_id" {
  description = "Principal ID of the Function App user-assigned MSI"
  type        = string
}
