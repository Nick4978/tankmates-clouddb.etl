resource "random_string" "cosmos_suffix" {
  length  = 4
  upper   = false
  numeric = true
  special = false
}


locals {
  cosmos_account_name = coalesce(var.cosmos_account_name, "${var.prefix}-cosmos-${random_string.cosmos_suffix.result}")
  containers = [
    "Corals", "Fish", "Inhabitants", "Inverts", "MediaTypes", "Pictures", "Plants",
    "Profile", "Records", "Tanks", "Tasks", "UserSettings",
    "WaterTestColorCharts", "WaterTestInstructions", "WaterTestKits",
    "WaterTestParameters", "WaterTestTypes", "WaterTests"
  ]
}

resource "azurerm_cosmosdb_account" "cosmos" {
  name                       = local.cosmos_account_name
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  offer_type                 = "Standard"
  kind                       = "GlobalDocumentDB"
  free_tier_enabled          = var.cosmos_free_tier
  automatic_failover_enabled = false

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }

  public_network_access_enabled = false # keep private
  tags                          = var.tags
}

resource "azurerm_cosmosdb_sql_database" "db" {
  name                = var.cosmos_db_name
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  autoscale_settings { max_throughput = 4000 } # database-level autoscale (shared)
}

resource "azurerm_cosmosdb_sql_container" "container" {
  for_each              = toset(local.containers)
  name                  = each.key
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_paths   = ["/tenantId"]
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"
    included_path {
      path = "/*"
    }
  }
}
