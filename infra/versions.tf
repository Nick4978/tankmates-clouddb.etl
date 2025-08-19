terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.113" # current stable
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47" # needs >= 2.28 for federated_identity_credential
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
