variable "subscription_id" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "region" {
  type    = string
  default = "eastus"
}

variable "resource_group_name" {
  type    = string
  default = "teracorp-east-resource-group"
}

variable "prefix" {
  type    = string
  default = "tm"
}

variable "tags" {
  type = map(string)
  default = {
    env     = "dev"
    project = "tankmates"
  }
}

# GitHub OIDC binding
variable "github_owner" {
  type    = string
  default = "nick4978"
}

variable "github_repo" {
  type    = string
  default = "tankmates-clouddb.etl"
}

variable "github_branch" {
  type    = string
  default = "master"
}

# Cosmos
variable "cosmos_free_tier" {
  type    = bool
  default = true
}

variable "cosmos_db_name" {
  type    = string
  default = "tankmatesdb"
}

variable "cosmos_account_name" {
  type    = string
  default = null # auto-generated if null
}
