
"""Platform for MyCurl sensor integration."""
import logging
import subprocess
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, CONF_COMMAND, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "MyCurl Sensor"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)

CONF_CURL_COMMAND = "curl_command"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_CURL_COMMAND): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
	vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
	"""Set up the MyCurl sensor platform."""
	name = config.get(CONF_NAME)
	curl_command = config.get(CONF_CURL_COMMAND)
	scan_interval = config.get(CONF_SCAN_INTERVAL)
	add_entities([MyCurlSensor(name, curl_command, scan_interval)])


class MyCurlSensor(SensorEntity):
	"""Representation of a Sensor that runs a curl command."""

	def __init__(self, name, curl_command, scan_interval):
		self._name = name
		self._curl_command = curl_command
		self._state = None
		self._attr_scan_interval = scan_interval

	@property
	def name(self):
		return self._name

	@property
	def state(self):
		return self._state

	def update(self):
		"""Fetch new state data for the sensor by running the curl command."""
		try:
			result = subprocess.run(self._curl_command, shell=True, capture_output=True, text=True, timeout=30)
			if result.returncode == 0:
				self._state = result.stdout.strip()
			else:
				_LOGGER.error("Curl command failed: %s", result.stderr)
				self._state = None
		except Exception as e:
			_LOGGER.error("Error running curl command: %s", e)
			self._state = None
