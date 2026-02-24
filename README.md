# BLS MCP Server

Model Context Protocol (MCP) server for accessing and analyzing Bureau of Labor Statistics data. Enables LLMs to query and interpret BLS datasets through a structured API.

## Overview

This serverless MCP implementation indexes Bureau of Labor Statistics data from bls.gov and provides AI-powered analysis capabilities through Semantic Kernel orchestration.

## Architecture

**Hosting**: Azure Functions with MCP Extension  
**Authentication**: Microsoft Easy Auth  
**AI Orchestration**: Semantic Kernel  
**Data Source**: Bureau of Labor Statistics (bls.gov)

The application uses user-assigned managed identity for secure Azure resource access and follows Azure best practices for serverless deployments.

## Tech Stack

- Python 3.11
- Azure Functions (Consumption Plan)
- Semantic Kernel
- Bicep (Infrastructure as Code)

## Deployment

Validate the deployment:
```bash
cd src/infra
az deployment sub validate \
  --location swedencentral \
  --template-file main.bicep \
  --parameters location=swedencentral
```

Deploy to Azure:
```bash
az deployment sub create \
  --location swedencentral \
  --template-file main.bicep \
  --parameters location=swedencentral
```

## Project Structure

```
bls-mcp/
├── src/
│   ├── function_app.py      # Main function app entry point
│   ├── core/                # Core application logic
│   │   └── kernel.py        # Semantic Kernel configuration
│   └── infra/               # Infrastructure definitions
│       ├── main.bicep       # Main deployment template
│       ├── app/             # Function app module
│       └── identity/        # Managed identity module
```