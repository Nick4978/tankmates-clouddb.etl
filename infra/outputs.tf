output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.cosmos.endpoint
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}

output "storage_account" {
  value = azurerm_storage_account.sa.name
}

output "ingest_container" {
  value = azurerm_storage_container.ingest.name
}
