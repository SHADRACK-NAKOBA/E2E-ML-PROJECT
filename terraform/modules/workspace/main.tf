# The Azure ML workspace is the lifecycle control plane: compute clusters,
# registered environments, registered data assets, training jobs, and the
# model registry all live here with RBAC on top — not scattered across an
# unrelated storage account and a compute subscription nobody tracks.

resource "azurerm_storage_account" "ml" {
  name                     = "stnakoba${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_key_vault" "ml" {
  name                       = "kv-nakoba-${var.environment}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = var.tags
}

resource "azurerm_application_insights" "ml" {
  name                = "appi-nakoba-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  application_type    = "web"
  tags                = var.tags

  lifecycle {
    ignore_changes = [
      workspace_id
    ]
  }
}

resource "azurerm_container_registry" "ml" {
  name                = "acrnakoba${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = false # identity-based auth only — no admin password to leak
  tags                = var.tags

}

resource "azurerm_machine_learning_workspace" "nakoba" {
  name                          = "mlw-nakoba-${var.environment}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  application_insights_id       = azurerm_application_insights.ml.id
  key_vault_id                  = azurerm_key_vault.ml.id
  storage_account_id            = azurerm_storage_account.ml.id
  container_registry_id         = azurerm_container_registry.ml.id
  public_network_access_enabled = true # dev: required for managed online endpoint access

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_machine_learning_compute_cluster" "training" {
  name                          = "cpu-cluster-${var.environment}"
  location                      = var.location
  machine_learning_workspace_id = azurerm_machine_learning_workspace.nakoba.id
  vm_priority                   = "Dedicated" # dev training compute; using dedicated quota
  vm_size                       = "Standard_DS2_v2"

  scale_settings {
    min_node_count                       = 0
    max_node_count                       = 1
    scale_down_nodes_after_idle_duration = "PT15M"
  }

  identity {
    type = "SystemAssigned"
  }
}

data "azurerm_client_config" "current" {}
