
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mycurl"
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # type: ignore[override]
	"""Set up MyCurl from YAML (no action needed)."""
	return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # type: ignore[override]
	"""Set up MyCurl from a config entry."""
	# Home Assistant API changed: async_forward_entry_setup -> async_forward_entry_setups
	if hasattr(hass.config_entries, "async_forward_entry_setups"):
		await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)  # New API (2024+)
	else:  # pragma: no cover - legacy path
		for platform in PLATFORMS:
			hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, platform))
	return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # type: ignore[override]
	"""Unload a config entry."""
	if hasattr(hass.config_entries, "async_unload_platforms"):
		unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)  # New API
	else:  # pragma: no cover - legacy path
		unloaded = True
		for platform in PLATFORMS:
			unloaded &= await hass.config_entries.async_forward_entry_unload(entry, platform)
	return unloaded
