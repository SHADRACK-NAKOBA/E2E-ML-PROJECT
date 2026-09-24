terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }

  # Remote state — never local state for anything beyond a laptop experiment.
  # Configure via -backend-config at init time per environment (dev/staging/prod).
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "nakoba" {
  name     = "rg-nakoba-${var.environment}"
  location = var.location
  tags     = local.tags
}

module "networking" {
  source              = "./modules/networking"
  resource_group_name = azurerm_resource_group.nakoba.name
  location            = azurerm_resource_group.nakoba.location
  environment         = var.environment
  tags                = local.tags
}

module "identity" {
  source              = "./modules/identity"
  resource_group_name = azurerm_resource_group.nakoba.name
  location            = azurerm_resource_group.nakoba.location
  environment         = var.environment
  key_vault_id        = module.workspace.key_vault_id
  storage_account_id  = module.workspace.storage_account_id
  acr_id              = module.workspace.acr_id
  tags                = local.tags
}

module "workspace" {
  source              = "./modules/workspace"
  resource_group_name = azurerm_resource_group.nakoba.name
  location            = azurerm_resource_group.nakoba.location
  environment         = var.environment
  subnet_id           = module.networking.ml_subnet_id
  tags                = local.tags
}

locals {
  tags = {
    project     = "nakoba"
    environment = var.environment
    managed_by  = "terraform"
  }
}
