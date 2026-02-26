using 'main.bicep'

var cfg = loadJsonContent('dev-config.json').config
var naming_prefix = '${cfg.project.namingPrefix}${cfg.project.location}-'

param location = cfg.project.location
param resource_group_name = '${naming_prefix}rg'
param func_app_name = '${naming_prefix}func-app'
param func_app_plan_name = '${naming_prefix}app-plan'
param func_app_user_assigned_msi_name = '${naming_prefix}func-app-msi'
param openai_account_name string = '${naming_prefix}foundry-acc'
param openai_account_msi_name string = '${naming_prefix}foundry-acc-msi'
param model_deployment_name string = '${naming_prefix}model-deployment'
