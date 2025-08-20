
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery
from homeassistant.const import Platform
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mycurl"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
	"""Set up MyCurl from configuration.yaml (legacy)."""
	return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Set up MyCurl from a config entry (UI)."""
	hass.async_create_task(
		hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
	)
	return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload a config entry."""
	return await hass.config_entries.async_forward_entry_unload(entry, Platform.SENSOR)
