using 'main.bicep'

var cfg = loadJsonContent('prod-config.json').config
var naming_prefix = '${cfg.project.namingPrefix}${cfg.project.location}-'

param location = cfg.project.location
param resource_group_name = '${naming_prefix}rg'
param func_app_name = '${naming_prefix}func-app'
param func_app_plan_name = '${naming_prefix}app-plan'
param func_app_user_assigned_msi_name = '${naming_prefix}func-app-msi'
