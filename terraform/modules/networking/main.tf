# Isolated VNet for the ML compute plane. Kept to a single subnet since this
# is a reference implementation, not a multi-region production estate — the
# point being demonstrated is "compute isn't on the public internet," not a
# full hub-spoke topology.

resource "azurerm_virtual_network" "nakoba" {
  name                = "vnet-nakoba-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = ["10.20.0.0/16"]
  tags                = var.tags
}

resource "azurerm_subnet" "ml" {
  name                 = "snet-ml-${var.environment}"
  resource_group_name = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.nakoba.name
  address_prefixes     = ["10.20.1.0/24"]
}
