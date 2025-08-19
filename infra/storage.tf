resource "azurerm_storage_account" "sa" {
  name                     = "${var.prefix}st${replace(var.region, "-", "")}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "ingest" {
  name                  = "ingest"
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}
