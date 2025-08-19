resource "random_string" "kv_suffix" {
  length  = 4
  upper   = false
  numeric = true
  special = false
}


resource "azurerm_key_vault" "kv" {
  name                          = "${var.prefix}-kv-${random_string.kv_suffix.result}"
  location                      = azurerm_resource_group.rg.location
  resource_group_name           = azurerm_resource_group.rg.name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  public_network_access_enabled = true
  tags                          = var.tags
}
