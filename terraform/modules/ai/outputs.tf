output "openai_account_id" {
  description = "Resource ID of the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.id
}

output "search_service_id" {
  description = "Resource ID of the Azure AI Search service"
  value       = azurerm_search_service.rag.id
}
