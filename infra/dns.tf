# Private DNS zone for Cosmos SQL API
resource "azurerm_private_dns_zone" "cosmos_sql" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

# Link your VNet so resources inside can resolve the privatelink FQDN
resource "azurerm_private_dns_zone_virtual_network_link" "cosmos_sql_link" {
  name                  = "${var.prefix}-cosmos-sql-link"
  private_dns_zone_name = azurerm_private_dns_zone.cosmos_sql.name
  resource_group_name   = azurerm_resource_group.rg.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
  registration_enabled  = false
  tags                  = var.tags
}
