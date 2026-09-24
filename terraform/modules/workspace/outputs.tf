output "workspace_name" { value = azurerm_machine_learning_workspace.nakoba.name }
output "workspace_id" { value = azurerm_machine_learning_workspace.nakoba.id }
output "acr_login_server" { value = azurerm_container_registry.ml.login_server }
output "acr_id" { value = azurerm_container_registry.ml.id }
output "key_vault_id" { value = azurerm_key_vault.ml.id }
output "key_vault_uri" { value = azurerm_key_vault.ml.vault_uri }
output "storage_account_id" { value = azurerm_storage_account.ml.id }
