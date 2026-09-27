resource "azurerm_cognitive_account" "openai" {
  name                = "oai-nakoba-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name         = "oai-nakoba-${var.environment}"
  local_auth_enabled            = false
  public_network_access_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_search_service" "rag" {
  name                = "srch-nakoba-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.search_location
  sku                 = "basic"

  replica_count   = 1
  partition_count = 1

  local_authentication_enabled  = false
  public_network_access_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                   = "text-embedding-3-large"
  cognitive_account_id   = azurerm_cognitive_account.openai.id
  version_upgrade_option = "NoAutoUpgrade"
  rai_policy_name        = "Microsoft.DefaultV2"

  model {
    format  = "OpenAI"
    name    = var.embedding_model_name
    version = var.embedding_model_version
  }

  scale {
    type     = "Standard"
    capacity = 10
  }
}

resource "azurerm_cognitive_deployment" "chat" {
  name                   = "gpt-5-6-sol"
  cognitive_account_id   = azurerm_cognitive_account.openai.id
  version_upgrade_option = "NoAutoUpgrade"
  rai_policy_name        = "Microsoft.DefaultV2"

  model {
    format  = "OpenAI"
    name    = var.chat_model_name
    version = var.chat_model_version
  }

  scale {
    type     = "GlobalStandard"
    capacity = 10
  }
}
