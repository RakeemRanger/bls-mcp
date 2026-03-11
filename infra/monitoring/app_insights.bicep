param location string = resourceGroup().location
param app_insights_name string
param log_analytics_workspace_name string

// Log Analytics Workspace for Application Insights
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: log_analytics_workspace_name
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: 1  // 1GB per day free tier limit
    }
  }
}

// Application Insights resource
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: app_insights_name
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    RetentionInDays: 30
  }
}

output app_insights_connection_string string = applicationInsights.properties.ConnectionString
output app_insights_instrumentation_key string = applicationInsights.properties.InstrumentationKey
output app_insights_id string = applicationInsights.id
output log_analytics_workspace_id string = logAnalyticsWorkspace.id
