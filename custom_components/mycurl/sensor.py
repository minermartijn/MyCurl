
"""Platform for MyCurl sensor integration."""
import logging
import subprocess
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, async_setup_entry
from homeassistant.const import CONF_NAME, CONF_COMMAND, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "MyCurl Sensor"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)

CONF_CURL_COMMAND = "curl_command"

CONF_DATA_TYPE = "data_type"
DATA_TYPE_NUMERIC = "numeric"
DATA_TYPE_TEXT = "text"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_CURL_COMMAND): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
	vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
	vol.Optional(CONF_DATA_TYPE, default=DATA_TYPE_TEXT): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
})



def setup_platform(hass, config, add_entities, discovery_info=None):
	"""Set up the MyCurl sensor platform from YAML."""
	name = config.get(CONF_NAME)
	curl_command = config.get(CONF_CURL_COMMAND)
	scan_interval = config.get(CONF_SCAN_INTERVAL)
	data_type = config.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)
	add_entities([MyCurlSensor(name, curl_command, scan_interval, data_type)], True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
	"""Set up MyCurl sensor from a config entry (UI)."""
	data = entry.data
	name = data.get(CONF_NAME, DEFAULT_NAME)
	curl_command = data.get(CONF_CURL_COMMAND)
	# Backwards compatibility: build curl command if only URL provided
	if not curl_command and data.get("url"):
		curl_command = build_curl_command(data.get("url"), data.get("jq_filter"))
		hass.config_entries.async_update_entry(entry, data={**data, CONF_CURL_COMMAND: curl_command})
	scan_interval = timedelta(seconds=data.get("scan_interval", int(DEFAULT_SCAN_INTERVAL.total_seconds())))
	data_type = data.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)
	async_add_entities([MyCurlSensor(name, curl_command, scan_interval, data_type)], True)


def build_curl_command(url: str | None, jq_filter: str | None) -> str | None:
	if not url:
		return None
	cmd = f"curl -s {url.strip()}"
	if jq_filter:
		jq_expr = jq_filter.strip()
		if jq_expr:
			cmd += f" | jq -r {jq_expr}"
	return cmd



class MyCurlSensor(SensorEntity):
	"""Representation of a Sensor that runs a curl command."""

	def __init__(self, name, curl_command, scan_interval, data_type):
		self._name = name
		self._curl_command = curl_command
		self._state = None
		self._attr_scan_interval = scan_interval
		self._data_type = data_type
		# Set device_class and state_class if numeric
		if self._data_type == DATA_TYPE_NUMERIC:
			self._attr_device_class = "measurement"
			self._attr_state_class = "measurement"

	@property
	def name(self):
		return self._name

	@property
	def state(self):
		return self._state

	@property
	def icon(self):
		# Use bundled integration icon
		return "mdi:cloud-download"

	def update(self):
		"""Fetch new state data for the sensor by running the curl command."""
		try:
			result = subprocess.run(self._curl_command, shell=True, capture_output=True, text=True, timeout=30)
			if result.returncode == 0:
				value = result.stdout.strip()
				if self._data_type == DATA_TYPE_NUMERIC:
					try:
						# Try to cast to float or int
						if "." in value:
							self._state = float(value)
						else:
							self._state = int(value)
					except Exception:
						_LOGGER.error("Expected numeric output but got: %s", value)
						self._state = None
				else:
					self._state = value
			else:
				_LOGGER.error("Curl command failed: %s", result.stderr)
				self._state = None
		except Exception as e:
			_LOGGER.error("Error running curl command: %s", e)
			self._state = None
