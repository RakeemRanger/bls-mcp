param storageAccountName string
param appInsightsName string
param keyVaultName string
param managedIdentityPrincipalId string
param userIdentityPrincipalId string = ''
param allowUserIdentityPrincipal bool = false
param enableBlob bool = true
param enableQueue bool = false
param enableTable bool = false

// Role Definition IDs
var storageRoleDefinitionId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'   // Storage Blob Data Owner
var queueRoleDefinitionId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'     // Storage Queue Data Contributor
var tableRoleDefinitionId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'     // Storage Table Data Contributor
var monitoringRoleDefinitionId = '3913510d-42f4-4e42-8a64-420c390055eb' // Monitoring Metrics Publisher
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'        // Key Vault Secrets User

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' existing = {
  name: storageAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: appInsightsName
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// ── Blob Role Assignments ───────────────────────────────────────────────────
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableBlob) {
  name: guid(storageAccount.id, managedIdentityPrincipalId, storageRoleDefinitionId)
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageRoleDefinitionId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource storageRoleAssignment_User 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableBlob && allowUserIdentityPrincipal && !empty(userIdentityPrincipalId)) {
  name: guid(storageAccount.id, userIdentityPrincipalId, storageRoleDefinitionId)
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageRoleDefinitionId)
    principalId: userIdentityPrincipalId
    principalType: 'User'
  }
}

// ── Queue Role Assignments ──────────────────────────────────────────────────
resource queueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableQueue) {
  name: guid(storageAccount.id, managedIdentityPrincipalId, queueRoleDefinitionId)
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', queueRoleDefinitionId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource queueRoleAssignment_User 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableQueue && allowUserIdentityPrincipal && !empty(userIdentityPrincipalId)) {
  name: guid(storageAccount.id, userIdentityPrincipalId, queueRoleDefinitionId)
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', queueRoleDefinitionId)
    principalId: userIdentityPrincipalId
    principalType: 'User'
  }
}

// ── Table Role Assignments ──────────────────────────────────────────────────
resource tableRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableTable) {
  name: guid(storageAccount.id, managedIdentityPrincipalId, tableRoleDefinitionId)
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', tableRoleDefinitionId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource tableRoleAssignment_User 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableTable && allowUserIdentityPrincipal && !empty(userIdentityPrincipalId)) {
  name: guid(storageAccount.id, userIdentityPrincipalId, tableRoleDefinitionId)
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', tableRoleDefinitionId)
    principalId: userIdentityPrincipalId
    principalType: 'User'
  }
}

// ── App Insights Role Assignments ───────────────────────────────────────────
resource appInsightsRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(applicationInsights.id, managedIdentityPrincipalId, monitoringRoleDefinitionId)
  scope: applicationInsights
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', monitoringRoleDefinitionId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource appInsightsRoleAssignment_User 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowUserIdentityPrincipal && !empty(userIdentityPrincipalId)) {
  name: guid(applicationInsights.id, userIdentityPrincipalId, monitoringRoleDefinitionId)
  scope: applicationInsights
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', monitoringRoleDefinitionId)
    principalId: userIdentityPrincipalId
    principalType: 'User'
  }
}

// ── Key Vault Role Assignments ──────────────────────────────────────────────
resource kvSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, managedIdentityPrincipalId, kvSecretsUserRoleId)
  scope: kv
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource kvSecretsUserRole_User 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowUserIdentityPrincipal && !empty(userIdentityPrincipalId)) {
  name: guid(kv.id, userIdentityPrincipalId, kvSecretsUserRoleId)
  scope: kv
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: userIdentityPrincipalId
    principalType: 'User'
  }
}
