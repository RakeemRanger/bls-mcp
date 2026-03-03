param location string = resourceGroup().location
param log_analytics_name string
param log_analytics_msi_id string
param insight_name string


resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: log_analytics_name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${log_analytics_msi_id}': {}
    }
  }
  properties: {
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    features: {
      disableLocalAuth: true
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}


resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  kind: 'web'
  name: insight_name
  location: location
  properties: {
    WorkspaceResourceId: logAnalyticsWorkspace.id
    Application_Type: 'web'
    DisableLocalAuth: true
    RetentionInDays: 30
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output app_insights_conn_string string =  appInsights.properties.ConnectionString
