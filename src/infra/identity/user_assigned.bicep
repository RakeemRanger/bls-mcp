param location string = resourceGroup().location
param msi_name string

resource userAssignedMsi 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  location: location
  name: msi_name
}

output msi_id string = userAssignedMsi.id
