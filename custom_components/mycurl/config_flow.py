import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from .sensor import (
    CONF_CURL_COMMAND,
    CONF_DATA_TYPE,
    DATA_TYPE_NUMERIC,
    DATA_TYPE_TEXT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
)
import subprocess
import logging

_LOGGER = logging.getLogger(__name__)

CONF_RUN_TEST = "run_test"


class MyCurlConfigFlow(config_entries.ConfigFlow, domain="mycurl"):
    """Handle a config flow for MyCurl."""

    VERSION = 1

    def __init__(self):
        self._last_test_output: str | None = None

    async def async_step_user(self, user_input=None):  # type: ignore[override]
        errors: dict[str, str] = {}
        if user_input is not None:
            run_test = user_input.get(CONF_RUN_TEST, False)
            curl_cmd = user_input.get(CONF_CURL_COMMAND, "").strip()

            if run_test:
                if curl_cmd:
                    def run_curl():
                        try:
                            result = subprocess.run(
                                curl_cmd,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )
                            if result.returncode == 0:
                                return result.stdout.strip() or "(no output)"
                            return f"Error: {result.stderr.strip() or 'unknown'}"
                        except Exception as exc:  # noqa: BLE001
                            _LOGGER.error("Test command exception: %s", exc)
                            return f"Exception: {exc}"

                    self._last_test_output = await self.hass.async_add_executor_job(run_curl)
                else:
                    self._last_test_output = "Please enter a curl command first."
            else:
                # creating entry path
                if not curl_cmd:
                    errors[CONF_CURL_COMMAND] = "required"
                if not errors:
                    data = dict(user_input)
                    data.pop(CONF_RUN_TEST, None)
                    return self.async_create_entry(title=data[CONF_NAME], data=data)

        defaults = user_input or {}
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
                vol.Required(CONF_CURL_COMMAND, default=defaults.get(CONF_CURL_COMMAND, "")): str,
                vol.Optional(
                    CONF_DATA_TYPE,
                    default=defaults.get(CONF_DATA_TYPE, DATA_TYPE_TEXT),
                ): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
                vol.Optional(
                    "scan_interval",
                    default=defaults.get(
                        "scan_interval", int(DEFAULT_SCAN_INTERVAL.total_seconds())
                    ),
                ): int,
                vol.Optional(CONF_RUN_TEST, default=False): bool,
            }
        )

        description_placeholders = {"test_output": self._last_test_output or ""}

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    @staticmethod
    def async_get_options_flow(config_entry):  # type: ignore[override]
        return MyCurlOptionsFlowHandler(config_entry)


class MyCurlOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):  # type: ignore[override]
        errors: dict[str, str] = {}
        if user_input is not None:
            # Do not carry over run_test flag in options
            user_input.pop(CONF_RUN_TEST, None)
            return self.async_create_entry(title="", data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=data.get(CONF_NAME, DEFAULT_NAME)): str,
                vol.Required(
                    CONF_CURL_COMMAND, default=data.get(CONF_CURL_COMMAND, "")
                ): str,
                vol.Optional(
                    CONF_DATA_TYPE, default=data.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)
                ): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
                vol.Optional(
                    "scan_interval",
                    default=data.get(
                        "scan_interval", int(DEFAULT_SCAN_INTERVAL.total_seconds())
                    ),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
