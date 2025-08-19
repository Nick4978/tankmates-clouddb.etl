resource "azurerm_private_endpoint" "cosmos" {
  name                = "${var.prefix}-pe-cosmos"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.privatelink.id
  tags                = var.tags

  private_service_connection {
    name                           = "cosmos-psc"
    is_manual_connection           = false
    private_connection_resource_id = azurerm_cosmosdb_account.cosmos.id
    subresource_names              = ["Sql"]
  }

  # ✅ Inline zone group (works across provider versions)
  private_dns_zone_group {
    name                 = "cosmos-sql-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos_sql.id]
  }
}
