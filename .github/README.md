## TankMates ETL to Cosmos (All Scripts)

### 1) One-time: Bootstrap Terraform with OIDC
- Run Terraform locally once or set `AZ_GHA_CLIENT_ID` repo variable to the value of the `github_client_id` Terraform output.
- Then run the **terraform** workflow to create Azure resources:
  - RG, VNet/Subnets, Log Analytics
  - Storage Account (blob)
  - Key Vault
  - Cosmos DB (Free Tier), DB, Containers (pk `/tenantId`)
  - Private Endpoint for Cosmos (keeps it private)
  - Container Apps Environment + ETL Job
  - Azure AD App + SP + Federated Credential for GitHub OIDC
  - RBAC:
    - SP: Contributor on RG
    - UAMI: Cosmos DB Built-in Data Contributor

### 2) Prepare SQLite artifact
- In GitHub, upload artifact named `sqlite-db` containing `tankmates.db`
  - Or adjust `etl.yaml` input names.

### 3) Run ETL
- Trigger the **etl-run** workflow → it:
  1. Downloads SQLite artifact.
  2. Uploads to Storage blob.
  3. Generates short-lived SAS (read-only).
  4. Starts Container Apps Job with `SQLITE_SAS_URL`.
  5. The job downloads the DB and upserts rows into Cosmos.

### 4) Config
- Edit `etl/config.example.json` to set:
  - `tenantId` (optional; default placeholder is used if null)
  - batch size / concurrency
  - container map (already aligned to schema)



  # ETL Pipeline

This folder contains Python scripts to extract, transform, and load data
from a local SQLite database (tankmates.db) into Azure Cosmos DB.

## Components

- run.py — Orchestrates the ETL pipeline  
- transform.py — Handles data transformation rules  
- load_cosmos.py — Handles writes to Cosmos DB  
- config.example.json — Example config file with table mappings  

## How It Works

1. Download SQLite database (tankmates.db) from blob storage  
2. Read and transform records per table (adds $tenantId$)  
3. Upsert documents into Cosmos DB containers  
4. Write a CSV log (etl_log.csv) with record counts and any errors  
5. Upload the log back to blob storage  

## Running Locally

$cd etl$  
$pip install -r requirements.txt$  
$python run.py$  

Make sure the following environment variables are set:

- $COSMOS_ENDPOINT$  
- $STORAGE_ACCOUNT$  
- $STORAGE_CONTAINER$  
- $SQLITE_BLOB_NAME$  
- $ETL_LOG_BLOB_NAME$  
- $CONFIG_PATH$  

## Running in Azure

The ETL also runs inside an **Azure Container App Job**.  
It automatically pulls this repo and executes $run.py$.  
Logs are stored in the ingest container as $etl_log.csv$.  
