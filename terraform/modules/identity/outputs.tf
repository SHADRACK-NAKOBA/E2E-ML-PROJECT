output "endpoint_identity_id" { value = azurerm_user_assigned_identity.endpoint.id }
output "endpoint_identity_client_id" { value = azurerm_user_assigned_identity.endpoint.client_id }
output "endpoint_identity_principal_id" {
  value = azurerm_user_assigned_identity.endpoint.principal_id
}
