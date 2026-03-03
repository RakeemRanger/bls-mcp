// Role assignment for Application Insights
// Module scope: resourceGroup
// Assigns role to an existing or newly created App Insights component

@description('Principal ID (MSI) for the role assignment')
param principal_id string

@description('Application Insights component name to assign role to')
param app_insights_name string

@description('Display name for the role assignment')
param assignment_display_name string

@description('Azure role definition ID (full resource ID format)')
param role_definition_id string

@description('Description of the role assignment')
param role_description string

// Reference the existing App Insights component in this resource group
resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: app_insights_name
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(principal_id, appInsights.id, assignment_display_name, role_definition_id)
  scope: appInsights
  properties: {
    principalId: principal_id
    principalType: 'ServicePrincipal'
    roleDefinitionId: role_definition_id
    description: role_description
  }
}
