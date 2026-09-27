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

module "ai" {
  source = "./modules/ai"

  resource_group_name = azurerm_resource_group.nakoba.name
  location            = azurerm_resource_group.nakoba.location
  search_location     = var.search_location
  environment         = var.environment
  tags                = local.tags

  embedding_model_name    = var.embedding_model_name
  embedding_model_version = var.embedding_model_version
  chat_model_name         = var.chat_model_name
  chat_model_version      = var.chat_model_version
}

# Runtime RAG permissions for the Azure ML endpoint identity.
# Keep runtime read/inference-only; ingestion and index administration use separate permissions.

resource "azurerm_role_assignment" "endpoint_openai_user" {
  scope                = module.ai.openai_account_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = module.identity.endpoint_identity_principal_id
}

resource "azurerm_role_assignment" "endpoint_search_reader" {
  scope                = module.ai.search_service_id
  role_definition_name = "Search Index Data Reader"
  principal_id         = module.identity.endpoint_identity_principal_id
}
