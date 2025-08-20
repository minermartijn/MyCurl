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
    build_curl_command,
)
import subprocess
import logging

_LOGGER = logging.getLogger(__name__)

CONF_FETCH_SAMPLE = "fetch_sample"
CONF_URL = "url"
CONF_JQ_FILTER = "jq_filter"
CONF_KEY_SELECT = "key_select"


class MyCurlConfigFlow(config_entries.ConfigFlow, domain="mycurl"):
    """Handle a config flow for MyCurl."""

    VERSION = 1

    def __init__(self):
        self._raw_output: str | None = None
        self._filtered_output: str | None = None
        self._suggested_keys: list[str] = []

    async def async_step_user(self, user_input=None):  # type: ignore[override]
        errors: dict[str, str] = {}
        if user_input is not None:
            fetch_sample = user_input.get(CONF_FETCH_SAMPLE, False)

            # Always derive curl command from URL + jq (simplified UX)
            curl_cmd = build_curl_command(user_input.get(CONF_URL), user_input.get(CONF_JQ_FILTER)) or ""
            user_input[CONF_CURL_COMMAND] = curl_cmd

            # If user selected a key from suggestions, populate jq_filter if empty
            key_select = user_input.get(CONF_KEY_SELECT)
            if key_select and not user_input.get(CONF_JQ_FILTER):
                user_input[CONF_JQ_FILTER] = f".{key_select}"
                curl_cmd = build_curl_command(user_input.get(CONF_URL), user_input.get(CONF_JQ_FILTER)) or ""
                user_input[CONF_CURL_COMMAND] = curl_cmd

            if fetch_sample:
                # Fetch raw data (timeout modest)
                if user_input.get(CONF_URL):
                    def run_curl():
                        try:
                            result = subprocess.run(
                                curl_cmd or f"curl -s {user_input.get(CONF_URL)}",
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )
                            if result.returncode == 0:
                                return result.stdout
                            return f"Error: {result.stderr.strip() or 'unknown'}"
                        except Exception as exc:  # noqa: BLE001
                            _LOGGER.error("Sample fetch exception: %s", exc)
                            return f"Exception: {exc}"

                    raw_text = await self.hass.async_add_executor_job(run_curl)
                    self._raw_output = raw_text.strip() if isinstance(raw_text, str) else str(raw_text)

                    # Attempt to parse JSON and build suggestions
                    self._suggested_keys = []
                    import json  # local import
                    try:
                        parsed = json.loads(self._raw_output)
                        if isinstance(parsed, dict):
                            self._suggested_keys = [str(k) for k in list(parsed.keys())[:25]]
                            # Apply simple jq-like filter if provided (dot path)
                            jq_filter = user_input.get(CONF_JQ_FILTER, "").strip()
                            if jq_filter.startswith('.') and len(jq_filter) > 1:
                                val = parsed
                                for part in jq_filter[1:].split('.'):
                                    if isinstance(val, dict) and part in val:
                                        val = val[part]
                                    else:
                                        val = None
                                        break
                                if val is not None:
                                    import pprint
                                    self._filtered_output = pprint.pformat(val)[:800]
                                else:
                                    self._filtered_output = "(no match for filter)"
                            else:
                                self._filtered_output = None
                        else:
                            self._filtered_output = None
                    except Exception:
                        self._filtered_output = None
                else:
                    self._raw_output = "Please enter a URL first."
            else:
                # Finalize entry
                if not user_input.get(CONF_URL):
                    errors[CONF_URL] = "required"
                if not errors:
                    data = dict(user_input)
                    # Remove transient fetch flag & key select
                    for transient in (CONF_FETCH_SAMPLE, CONF_KEY_SELECT):
                        data.pop(transient, None)
                    return self.async_create_entry(title=data[CONF_NAME], data=data)

        defaults = user_input or {}
        base_fields = {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_URL, default=defaults.get(CONF_URL, "")): str,
            vol.Optional(CONF_JQ_FILTER, default=defaults.get(CONF_JQ_FILTER, "")): str,
        }
        # Add key selector if suggestions available
        if self._suggested_keys:
            base_fields[vol.Optional(CONF_KEY_SELECT, default=defaults.get(CONF_KEY_SELECT, ""))] = vol.In(self._suggested_keys)
        base_fields[vol.Optional(CONF_FETCH_SAMPLE, default=False)] = bool
        base_fields[vol.Optional(CONF_DATA_TYPE, default=defaults.get(CONF_DATA_TYPE, DATA_TYPE_TEXT))] = vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT])
        data_schema = vol.Schema(base_fields)

        # Build description placeholders for raw and filtered preview (truncated)
        preview_parts = []
        if self._raw_output:
            trunc = self._raw_output[:800]
            preview_parts.append(f"Raw:\n{trunc}")
        if self._filtered_output:
            preview_parts.append(f"Filtered:\n{self._filtered_output}")
        description_placeholders = {"test_output": "\n\n".join(preview_parts) if preview_parts else ""}

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
