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
2. Read and transform records per table (adds `tenantId`)  
3. Upsert documents into Cosmos DB containers  
4. Write a CSV log (etl_log.csv) with record counts and any errors  
5. Upload the log back to blob storage  

## Running Locally

`cd etl`  
`pip install -r requirements.txt`  
`python run.py`  

Make sure the following environment variables are set:

- `COSMOS_ENDPOINT`  
- `STORAGE_ACCOUNT`  
- `STORAGE_CONTAINER`  
- `SQLITE_BLOB_NAME`  
- `ETL_LOG_BLOB_NAME`  
- `CONFIG_PATH`  

## Running in Azure

The ETL also runs inside an **Azure Container App Job**.  
It automatically pulls this repo and executes `run.py`.  
Logs are stored in the ingest container as `etl_log.csv`.  
