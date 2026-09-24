# Scoped managed identity for the endpoint compute — RBAC narrowed to exactly
# the Key Vault secrets and storage container this workload needs. No shared
# service principal, no long-lived secret sitting in a pipeline YAML.

resource "azurerm_user_assigned_identity" "endpoint" {
  name                = "id-nakoba-endpoint-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User" # read-only — never Secrets Officer for a runtime identity
  principal_id         = azurerm_user_assigned_identity.endpoint.principal_id
}

resource "azurerm_role_assignment" "storage_blob_reader" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.endpoint.principal_id
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.endpoint.principal_id
}
