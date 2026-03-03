using 'main.bicep'

//Naming Schema
var appCfg = loadJsonContent('dev-config.json').config

//Naming Pre
var naming_prefix = '${appCfg.project.namingPrefix}${appCfg.project.location}-'
param location = appCfg.project.location
param resource_group_name = '${naming_prefix}rg'
param func_app_name = '${naming_prefix}func-app'
param func_app_plan_name = '${naming_prefix}app-plan'
param func_app_user_assigned_msi_name = '${naming_prefix}func-app-msi'
param openai_account_name = '${naming_prefix}foundry-acc'
param openai_account_msi_name = '${naming_prefix}foundry-acc-msi'
param model_deployment_name = '${naming_prefix}model-deployment'
param log_analytics_name = '${naming_prefix}log-workspace'
param log_analytics_msi_name = '${naming_prefix}log-workspace-msi'
param insight_name = '${naming_prefix}app-insights'
param search_name = '${naming_prefix}search'
param sto_acount_name = uniqueString('devblssto${location}')

// Azure role definitions - load from JSON
var azureRoleCfg = loadJsonContent('appRoleDefinitions.json')

// Parameters to pass to main.bicep
// Storage role params
param stoBlobDataOwnerRoleName = azureRoleCfg.storage.blobDataOwner.name
param stoBlobDataOwnerRoleId = azureRoleCfg.storage.blobDataOwner.id
param stoTableDataContribRoleName = azureRoleCfg.storage.tableDataContributor.name
param stoTableDataContribRoleId = azureRoleCfg.storage.tableDataContributor.id
param stoQueueDataContribRoleName = azureRoleCfg.storage.queueDataContributor.name
param stoQueueDataContribRoleId = azureRoleCfg.storage.queueDataContributor.id
param stoFileDataPrivContribRoleName = azureRoleCfg.storage.fileDataPrivilegedContributor.name
param stoFileDataPrivContribRoleId = azureRoleCfg.storage.fileDataPrivilegedContributor.id

// Cognitive Services role params
param openAiUserRoleName = azureRoleCfg.cognitiveServices.openaiUser.name
param openAiUserRoleId = azureRoleCfg.cognitiveServices.openaiUser.id
param cognitiveServicesUserRoleName = azureRoleCfg.cognitiveServices.user.name
param cognitiveServicesUserRoleId = azureRoleCfg.cognitiveServices.user.id

// Monitoring role params
param monitoringMetricsPublisherRoleName = azureRoleCfg.monitoring.metricsPublisher.name
param monitoringMetricsPublisherRoleId = azureRoleCfg.monitoring.metricsPublisher.id

// AI Search role params
param indexDataContributorRoleName = azureRoleCfg.aiSearch.indexDataContributor.name
param indexDataContributorRoleId = azureRoleCfg.aiSearch.indexDataContributor.id
param indexDataReaderRoleName = azureRoleCfg.aiSearch.indexDataReader.name
param indexDataReaderRoleId = azureRoleCfg.aiSearch.indexDataReader.id
param indexServiceContributorRoleName = azureRoleCfg.aiSearch.serviceContributor.name
param indexServiceContributorRoleId = azureRoleCfg.aiSearch.serviceContributor.id
