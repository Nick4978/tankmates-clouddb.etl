###############################################
# Container Apps Environment + ETL Job       #
###############################################

resource "azurerm_container_app_environment" "cae" {
  name                       = "${var.prefix}-cae"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  infrastructure_subnet_id   = azurerm_subnet.apps.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  tags                       = var.tags
}

resource "azurerm_container_app_job" "etl" {
  name                         = "${var.prefix}-etl-job"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  container_app_environment_id = azurerm_container_app_environment.cae.id

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.etl.id]
  }

  replica_timeout_in_seconds = 1800
  replica_retry_limit        = 1

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name  = "etl"
      image = "mcr.microsoft.com/devcontainers/python:3.11"

      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "COSMOS_ENDPOINT"
        value = azurerm_cosmosdb_account.cosmos.endpoint
      }
      env {
        name  = "COSMOS_CONNSTR"
        value = azurerm_cosmosdb_account.cosmos.primary_sql_connection_string
      }
      env {
        name  = "STORAGE_ACCOUNT"
        value = azurerm_storage_account.sa.name
      }

      env {
        name  = "STORAGE_CONTAINER"
        value = azurerm_storage_container.ingest.name
      }

      env {
        name  = "SQLITE_BLOB_NAME"
        value = "tankmates.db"
      }

      env {
        name  = "ETL_LOG_BLOB_NAME"
        value = "etl_log.csv"
      }

      env {
        name  = "CONFIG_PATH"
        value = "/workspace/${var.github_repo}-${var.github_branch}/etl/config.example.json"
      }

      command = [
        "bash",
        "-lc",
        <<-EOT
          set -euo pipefail
          apt-get update -y && apt-get install -y --no-install-recommends unzip curl ca-certificates
          mkdir -p /workspace
          echo "Downloading repo zip: https://codeload.github.com/${var.github_owner}/${var.github_repo}/zip/refs/heads/${var.github_branch}"
          curl -fsSL -o /tmp/repo.zip "https://codeload.github.com/${var.github_owner}/${var.github_repo}/zip/refs/heads/${var.github_branch}"
          unzip -q /tmp/repo.zip -d /workspace
          pip install --no-cache-dir -r "/workspace/${var.github_repo}-${var.github_branch}/etl/requirements.txt"
          python "/workspace/${var.github_repo}-${var.github_branch}/etl/run.py"
        EOT
      ]
    }
  }

  tags = var.tags
}


output "etl_job_name" {
  value       = azurerm_container_app_job.etl.name
  description = "Name of the Container Apps Job you can trigger from GitHub Actions"
}

output "container_app_env" {
  value       = azurerm_container_app_environment.cae.name
  description = "Container Apps environment name"
}
