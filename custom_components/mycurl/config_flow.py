import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from .sensor import CONF_CURL_COMMAND, CONF_DATA_TYPE, DATA_TYPE_NUMERIC, DATA_TYPE_TEXT, DEFAULT_NAME, DEFAULT_SCAN_INTERVAL



import subprocess
import logging

_LOGGER = logging.getLogger(__name__)

class MyCurlConfigFlow(config_entries.ConfigFlow, domain="mycurl"):
    """Handle a config flow for MyCurl."""

    VERSION = 1


    async def async_step_user(self, user_input=None):
        errors = {}
        test_output = None
        if user_input is not None:
            # If test button pressed, run the curl command and show output
            if user_input.get("test_command"):
                curl_cmd = user_input.get(CONF_CURL_COMMAND, "").strip()
                if curl_cmd:
                    try:
                        # Run the command in executor to avoid blocking event loop
                        def run_curl():
                            try:
                                result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=10)
                                if result.returncode == 0:
                                    return result.stdout.strip()
                                else:
                                    return f"Error: {result.stderr.strip()}"
                            except Exception as e:
                                _LOGGER.error("Test command exception: %s", e)
                                return f"Exception: {e}"
                        test_output = await self.hass.async_add_executor_job(run_curl)
                    except Exception as e:
                        _LOGGER.error("Test command async exception: %s", e)
                        test_output = f"Exception: {e}"
                else:
                    test_output = "Please enter a curl command."
            else:
                # Validate curl command is not empty
                if not user_input[CONF_CURL_COMMAND].strip():
                    errors[CONF_CURL_COMMAND] = "required"
                if not errors:
                    # Remove test_command key if present
                    user_input.pop("test_command", None)
                    return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME) if user_input else DEFAULT_NAME): str,
            vol.Required(CONF_CURL_COMMAND, default=user_input.get(CONF_CURL_COMMAND, "") if user_input else ""): str,
            vol.Optional(CONF_DATA_TYPE, default=user_input.get(CONF_DATA_TYPE, DATA_TYPE_TEXT) if user_input else DATA_TYPE_TEXT): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
            vol.Optional("scan_interval", default=user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL.total_seconds()) if user_input else DEFAULT_SCAN_INTERVAL.total_seconds()): int,
        })

        description_placeholders = {"test_output": test_output or ""}

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders,
            last_step=False,
            extra_step_buttons={"test_command": "Test Command"},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return MyCurlOptionsFlowHandler(config_entry)


class MyCurlOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=data.get(CONF_NAME, DEFAULT_NAME)): str,
                vol.Required(CONF_CURL_COMMAND, default=data.get(CONF_CURL_COMMAND, "")): str,
                vol.Optional(CONF_DATA_TYPE, default=data.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
                vol.Optional("scan_interval", default=data.get("scan_interval", DEFAULT_SCAN_INTERVAL.total_seconds())): int,
            }),
            errors=errors,
        )
