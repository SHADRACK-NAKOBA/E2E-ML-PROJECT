variable "resource_group_name" {
  description = "Resource group containing the AI platform resources"
  type        = string
}

variable "location" {
  description = "Azure region for AI resources"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
}

variable "embedding_model_name" {
  description = "Azure OpenAI embedding model name"
  type        = string
  default     = "text-embedding-3-large"
}

variable "embedding_model_version" {
  description = "Azure OpenAI embedding model version"
  type        = string
}

variable "chat_model_name" {
  description = "Azure OpenAI chat model name"
  type        = string
}

variable "chat_model_version" {
  description = "Azure OpenAI chat model version"
  type        = string
}

variable "search_location" {
  description = "Azure region for the Azure AI Search service"
  type        = string
}
