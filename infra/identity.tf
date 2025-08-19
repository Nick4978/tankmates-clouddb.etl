###############################################
# Identity + GitHub OIDC + RBAC assignments  #
###############################################

# App registration for GitHub OIDC
resource "azuread_application" "gha" {
  display_name = "${var.prefix}-gha-oidc"
}

resource "azuread_service_principal" "gha_sp" {
  client_id = azuread_application.gha.client_id
}

# Federated credential (azuread v2.x resource name)
resource "azuread_application_federated_identity_credential" "gha_fic" {
  application_object_id = azuread_application.gha.object_id
  display_name          = "github-${var.github_owner}-${var.github_repo}-${var.github_branch}"
  audiences             = ["api://AzureADTokenExchange"]
  issuer                = "https://token.actions.githubusercontent.com"
  subject               = "repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/${var.github_branch}"
}

# RG Contributor for the SP
resource "azurerm_role_assignment" "gha_contrib" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.gha_sp.object_id
}


###############################################
# User‑Assigned Managed Identity for ETL Job  #
###############################################
resource "azurerm_user_assigned_identity" "etl" {
  name                = "${var.prefix}-uami-etl"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

# Cosmos DB data access (RBAC) for ETL job
#resource "azurerm_role_assignment" "etl_cosmos_data" {
#  scope                = azurerm_cosmosdb_account.cosmos.id
#  role_definition_name = "Cosmos DB Built-in Data Contributor"
#  principal_id         = azurerm_user_assigned_identity.etl.principal_id
#}

# Storage access for ETL job (read SQLite blob + write CSV log)
resource "azurerm_role_assignment" "etl_storage_blob_contrib" {
  scope                = azurerm_storage_account.sa.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.etl.principal_id
}

# (Optional) Narrower role split; 'Contributor' above already includes read.
resource "azurerm_role_assignment" "etl_storage_blob_reader" {
  scope                = azurerm_storage_account.sa.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.etl.principal_id
}

###############################################
# Outputs (handy for wiring GitHub repo vars) #
###############################################
output "github_client_id" {
  description = "Azure AD application (client) ID for the GitHub OIDC app"
  value       = azuread_application.gha.application_id
}
