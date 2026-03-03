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
param log_analytics_name string
param log_analytics_msi_name string
param insight_name string
param sto_acount_name string
param search_name string

// Storage role params
param stoBlobDataOwnerRoleName string
param stoBlobDataOwnerRoleId string
param stoTableDataContribRoleName string
param stoTableDataContribRoleId string
param stoQueueDataContribRoleName string
param stoQueueDataContribRoleId string
param stoFileDataPrivContribRoleName string
param stoFileDataPrivContribRoleId string
var allStoAssignments = [
  {
    id: stoBlobDataOwnerRoleId
    roleName: stoBlobDataOwnerRoleName
  }
  {
    id: stoTableDataContribRoleId
    roleName: stoTableDataContribRoleName
  }
  {
    id: stoQueueDataContribRoleId
    roleName: stoQueueDataContribRoleName
  }
]
// Cognitive Services role params
param openAiUserRoleName string
param openAiUserRoleId string
param cognitiveServicesUserRoleName string
param cognitiveServicesUserRoleId string
var allCognitiveServiceRoles = [
  {
    id: openAiUserRoleId
    roleName: openAiUserRoleName
  }
  {
    id: cognitiveServicesUserRoleId
    roleName: cognitiveServicesUserRoleName
  }
]
// Monitoring role params
param monitoringMetricsPublisherRoleName string
param monitoringMetricsPublisherRoleId string

// AI Search role params
param indexDataContributorRoleName string
param indexDataContributorRoleId string
param indexDataReaderRoleName string
param indexDataReaderRoleId string
param indexServiceContributorRoleName string
param indexServiceContributorRoleId string
var allAiSearchRoles = [
  {
    id: indexDataContributorRoleId
    roleName: indexDataContributorRoleName
  }
  {
    id: indexDataReaderRoleId
    roleName: indexDataReaderRoleName
  }
  {
    id: indexServiceContributorRoleId
    roleName: indexServiceContributorRoleName
  }
]

resource resourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resource_group_name
  location: location
}

module funcAppUserAssignedMsi 'identity/user_assigned.bicep' = {
  scope: resourceGroup
  params: {
    msi_name: func_app_user_assigned_msi_name
    location: location
  }
}

module appInsightsUserAssignedMsi 'identity/user_assigned.bicep' = {
  scope: resourceGroup
  params: {
    msi_name: log_analytics_msi_name
    location: location
  }
}

module appInsigts 'observability/funcInsights.bicep' = {
  scope: resourceGroup
  params: {
    log_analytics_name: log_analytics_name
    location: location
    insight_name: insight_name
    log_analytics_msi_id: appInsightsUserAssignedMsi.outputs.msi_id
  }
}

module funcAppInsightsRoleAssignment 'rbac/appinsights_role_assignment.bicep' = {
  scope: resourceGroup
  params: {
    principal_id: funcAppUserAssignedMsi.outputs.msi_principal_id
    app_insights_name: insight_name
    assignment_display_name: monitoringMetricsPublisherRoleName
    role_definition_id: monitoringMetricsPublisherRoleId
    role_description: 'Grants ${monitoringMetricsPublisherRoleName} to Function App: ${func_app_name}'
  }
  dependsOn: [
    appInsigts
  ]
}

module storageAccount 'storage/func_app_sto.bicep' = {
  scope: resourceGroup
  params: {
    sto_account_name: sto_acount_name
    location: location
  }
}

module funcAppStoRoleAssignment 'rbac/storage_role_assignment.bicep' = [for assignment in allStoAssignments: {
  scope: resourceGroup
  params: {
    principal_id: funcAppUserAssignedMsi.outputs.msi_principal_id
    storage_account_name: sto_acount_name
    assignment_display_name: assignment.roleName
    role_definition_id: assignment.id
    role_description: 'Grants ${assignment.roleName} to Function App: ${func_app_name}'
  }
  dependsOn: [
    storageAccount
  ]
}
]

module openAiAccountUserAssignedMsi 'identity/user_assigned.bicep' = {
  scope: resourceGroup
  params: {
    msi_name: openai_account_msi_name
    location: location
  }
}


module openAiDeployment 'foundry/foundry.bicep' = {
  scope: resourceGroup
  params: {
    openai_account_msi_id: openAiAccountUserAssignedMsi.outputs.msi_id
    openai_account_name: openai_account_name
    model_deployment_name: 'gpt-4.1'
    deployment_capacity: 10
  }
}

module funcAppOpenAiRoleAssignment 'rbac/openai_role_assignment.bicep' = [for assignment in allCognitiveServiceRoles: {
  scope: resourceGroup
  params: {
    principal_id: funcAppUserAssignedMsi.outputs.msi_principal_id
    openai_account_name: openai_account_name
    assignment_display_name: assignment.roleName
    role_definition_id: assignment.id
    role_description: 'Grants ${assignment.roleName} to Function App ${func_app_name}'
  }
  dependsOn: [
    openAiDeployment
  ]
}
]

module azureAiSearch 'search/search.bicep' = {
  scope: resourceGroup
  params: {
    search_name: search_name
    location: location
  }
}

module funcAppSearchRoleAssignment 'rbac/search_role_assignment.bicep' = [for assignment in allAiSearchRoles: {
  scope: resourceGroup
  params: {
    principal_id: funcAppUserAssignedMsi.outputs.msi_principal_id
    search_name: search_name
    assignment_display_name: assignment.roleName
    role_definition_id: assignment.id
    role_description: 'Grants ${assignment.roleName} to Function App ${func_app_name}'
  }
  dependsOn: [
    azureAiSearch
  ]
}
]

module functionApp 'app/func_app.bicep' = {
  scope: resourceGroup
  params: {
    app_service_plan_name: func_app_plan_name
    func_app_msi_id: funcAppUserAssignedMsi.outputs.msi_id
    func_app_msi_client_id: funcAppUserAssignedMsi.outputs.msi_client_id
    func_app_name: func_app_name
    storage_account_name: sto_acount_name
    storage_account_key: storageAccount.outputs.sto_account_key
    location: location
  }
  dependsOn: [
    funcAppStoRoleAssignment
  ]
}


output funcAppEndpoint string = functionApp.outputs.func_app_endpoint
