param func_app_msi_principal_id string
param app_insights_id string

// Monitoring Metrics Publisher role (3913510d-42f4-4e42-8a64-420c390055eb)
// Allows publishing metrics to Application Insights
var monitoringMetricsPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb'

resource appInsightsMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(app_insights_id, func_app_msi_principal_id, monitoringMetricsPublisherRoleId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringMetricsPublisherRoleId)
    principalId: func_app_msi_principal_id
    principalType: 'ServicePrincipal'
  }
}
