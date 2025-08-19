# Infrastructure (Terraform)

This folder provisions Azure resources using Terraform.

## Resources

- Resource Group  
- Virtual Network & Subnets  
- Private Endpoint for Cosmos DB  
- Azure Cosmos DB (SQL API) with multiple containers  
- Storage Account + Container for SQLite DB + Logs  
- Key Vault for secrets  
- Log Analytics Workspace  
- Container App Environment + Job for ETL  
- Azure AD App Registration for GitHub OIDC  

## Usage

`cd infra`  
`terraform init`  
`terraform plan`  
`terraform apply`  

## Notes

- If a resource group already exists, import it with:  
  `terraform import azurerm_resource_group.rg /subscriptions/<sub>/resourceGroups/<rg>`  

- Subnet for Container Apps must be at least /23 CIDR  

- Make sure your subscription has the `Microsoft.App` and `Microsoft.DocumentDB` providers registered:  

`az provider register --namespace Microsoft.App`  
`az provider register --namespace Microsoft.DocumentDB`  
