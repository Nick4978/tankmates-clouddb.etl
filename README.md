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

