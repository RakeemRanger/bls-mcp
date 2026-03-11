targetScope = 'subscription'

@description('location of resource group')
param location string
param resource_group_name string
param func_app_name string
param func_app_plan_name string
param func_app_user_assigned_msi_name string
param openai_account_name string
param openai_account_msi_name string
param model_deployment_name string
param environment_name string = 'dev'
param azure_ai_search_name string
param azure_ai_search_msi_name string
@allowed(['basic', 'standard', 'standard2', 'standard3'])
param azure_ai_search_sku string = 'standard'
param app_insights_name string
param log_analytics_workspace_name string

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resource_group_name
  location: location
}

module funcUserAssignedMsi 'identity/user_assigned.bicep' = {
  scope: resourceGroup
  name: func_app_user_assigned_msi_name
  params: {
    msi_name: func_app_user_assigned_msi_name
  }
}

// Application Insights for monitoring
module appInsights 'monitoring/app_insights.bicep' = {
  scope: resourceGroup
  name: 'appInsights'
  params: {
    app_insights_name: app_insights_name
    log_analytics_workspace_name: log_analytics_workspace_name
  }
}

module functionApp 'app/func_app.bicep' = {
  scope: resourceGroup
  name: 'functionApp'
  params: {
    app_service_plan_name: func_app_plan_name
    func_app_name: func_app_name
    func_app_msi_id: funcUserAssignedMsi.outputs.msi_id
    func_app_msi_client_id: funcUserAssignedMsi.outputs.msi_client_id
    environment_name: environment_name
    azure_search_endpoint: azureAiSearch.outputs.search_endpoint
    app_insights_id: appInsights.outputs.app_insights_id
    app_insights_connection_string: appInsights.outputs.app_insights_connection_string
    openai_endpoint: openaiDeployment.outputs.openai_endpoint
    model_deployment_name: model_deployment_name
  }
}

module openaiAccountMSI 'identity/user_assigned.bicep' = {
  name: openai_account_msi_name
  scope: resourceGroup
  params: {
    msi_name: openai_account_msi_name
  }
}

module openaiDeployment 'foundry/foundry.bicep' = {
  name: 'openaiDeployment'
  scope: resourceGroup
  params: {
    openai_account_name: openai_account_name
    openai_account_msi_id: openaiAccountMSI.outputs.msi_id
    model_deployment_name: model_deployment_name
  }
}

module searchMSI 'identity/user_assigned.bicep' = {
  name: azure_ai_search_msi_name
  scope: resourceGroup
  params: {
    msi_name: azure_ai_search_name
  }
}

module azureAiSearch 'azureSearch/azureAiSearch.bicep' = {
  name: azure_ai_search_name
  scope: resourceGroup
  params: {
    search_name: azure_ai_search_name
    search_msi_id: searchMSI.outputs.msi_id
    search_sku: azure_ai_search_sku
  }
}

// RBAC: Grant Function App MSI access to Azure AI Search
module searchRbac 'rbac/search_rbac.bicep' = {
  name: 'searchRbac'
  scope: resourceGroup
  params: {
    func_app_msi_principal_id: funcUserAssignedMsi.outputs.msi_principal_id
    search_resource_id: azureAiSearch.outputs.search_resource_id
  }
  dependsOn: [
    functionApp
  ]
}

// RBAC: Grant Function App MSI access to Application Insights
module appInsightsRbac 'rbac/app_insights_rbac.bicep' = {
  name: 'appInsightsRbac'
  scope: resourceGroup
  params: {
    func_app_msi_principal_id: funcUserAssignedMsi.outputs.msi_principal_id
    app_insights_id: appInsights.outputs.app_insights_id
  }
  dependsOn: [
    functionApp
  ]
}


output resource_group_id string = resourceGroup.id
output openai_endpoint string = openaiDeployment.outputs.openai_endpoint
output func_app_name string = func_app_name
output func_app_url string = functionApp.outputs.func_app_endpoint
output search_resource_id string = azureAiSearch.outputs.search_resource_id
output search_endpoint string = azureAiSearch.outputs.search_endpoint
output app_insights_connection_string string = appInsights.outputs.app_insights_connection_string
