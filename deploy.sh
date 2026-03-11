#!/bin/bash
set -e

echo "🚀 Deploying BLS MCP Server to Azure"
echo "======================================"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed"
    echo "   Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "🔐 Logging in to Azure..."
    az login
fi

# Get subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "📋 Using subscription: $SUBSCRIPTION_ID"
echo ""

# Deploy infrastructure
echo "📦 Deploying infrastructure..."
cd src/infra

# Deploy using Bicep
az deployment sub create \
    --location swedencentral \
    --template-file main.bicep \
    --parameters main.bicepparam \
    --query 'properties.outputs' \
    -o json > deployment-output.json

echo "✅ Infrastructure deployed successfully"
echo ""

# Extract outputs
RESOURCE_GROUP_ID=$(cat deployment-output.json | jq -r '.resource_group_id.value')
FUNC_APP_NAME=$(cat deployment-output.json | jq -r '.func_app_name.value')
FUNC_APP_URL=$(cat deployment-output.json | jq -r '.func_app_url.value')
SEARCH_ENDPOINT=$(cat deployment-output.json | jq -r '.search_endpoint.value')
OPENAI_ENDPOINT=$(cat deployment-output.json | jq -r '.openai_endpoint.value')

echo "📊 Deployment Details:"
echo "   Resource Group: $RESOURCE_GROUP_ID"
echo "   Function App: $FUNC_APP_NAME"
echo "   Function URL: $FUNC_APP_URL"
echo "   Search Endpoint: $SEARCH_ENDPOINT"
echo "   OpenAI Endpoint: $OPENAI_ENDPOINT"
echo ""

# Deploy function code
echo "📤 Deploying function code..."
cd ../..
func azure functionapp publish $FUNC_APP_NAME --python

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔐 Authentication: Managed Identity (no API keys)"
echo "📝 Next steps:"
echo "   1. Initialize data: python scripts/initialize_data.py"
echo "   2. Test the function: curl $FUNC_APP_URL/api/health"
echo ""
