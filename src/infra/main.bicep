targetScope = 'subscription'

@description('location of resource group')
param location string

var resource_name_prefix = 'bls-proj-${location}-'
var resource_group_name = '${resource_name_prefix}rg'
var func_app_name = '${resource_name_prefix}func-app'
var func_app_plan_name = '${resource_name_prefix}app-plan'
var func_app_user_assigned_msi_name = '${resource_name_prefix}func-app-msi'

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

module functionApp 'app/func_app.bicep' = {
  scope: resourceGroup
  name: 'functionApp'
  params: {
    app_service_plan_name: func_app_plan_name
    func_app_name: func_app_name
    func_app_msi_id: funcUserAssignedMsi.outputs.msi_id
  }
}

output func_app_url string = functionApp.outputs.func_app_endpoint
