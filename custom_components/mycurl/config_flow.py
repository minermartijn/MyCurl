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
import json
from typing import Any

_LOGGER = logging.getLogger(__name__)

CONF_URL = "url"
CONF_JQ_FILTER = "jq_filter"
CONF_KEY_SELECT = "key_select"
CONF_REFRESH = "refresh"
CONF_CREATE = "create"


class MyCurlConfigFlow(config_entries.ConfigFlow, domain="mycurl"):
    """Two-step flow: (1) Name+URL, (2) Select key/filter & finalize."""

    VERSION = 1

    def __init__(self):
        self._name: str | None = None
        self._url: str | None = None
        self._raw_output: str | None = None
        self._suggested_keys: list[str] = []
        self._last_filter_value: str | None = None

    async def async_step_user(self, user_input=None):  # type: ignore[override]
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input.get(CONF_NAME, DEFAULT_NAME).strip()
            url = user_input.get(CONF_URL, "").strip()
            if not url:
                errors[CONF_URL] = "required"
            else:
                self._name = name or DEFAULT_NAME
                self._url = url
                # Fetch sample immediately
                await self._async_fetch_sample()
                return await self.async_step_select()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self._name or DEFAULT_NAME): str,
                vol.Required(CONF_URL, default=self._url or ""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select(self, user_input=None):  # type: ignore[override]
        errors: dict[str, str] = {}
        jq_filter: str = ""
        key_select: str | None = None
        data_type = DATA_TYPE_TEXT
        scan_interval = int(DEFAULT_SCAN_INTERVAL.total_seconds())

        if user_input is not None:
            if user_input.get(CONF_REFRESH):
                await self._async_fetch_sample()
            jq_filter = user_input.get(CONF_JQ_FILTER, "").strip()
            key_select = user_input.get(CONF_KEY_SELECT) or None
            data_type = user_input.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)
            scan_interval = user_input.get("scan_interval", scan_interval)

            # If key chosen and no explicit jq filter, derive it
            if key_select and not jq_filter:
                jq_filter = f".{key_select}"

            value_preview = self._apply_filter(jq_filter)
            self._last_filter_value = value_preview

            if user_input.get(CONF_CREATE):
                # finalize
                data: dict[str, Any] = {
                    CONF_NAME: self._name or DEFAULT_NAME,
                    CONF_URL: self._url,
                    CONF_JQ_FILTER: jq_filter,
                    CONF_DATA_TYPE: data_type,
                    "scan_interval": scan_interval,
                }
                data[CONF_CURL_COMMAND] = build_curl_command(self._url, jq_filter)
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        # Build schema for selection step
        key_field = (
            {vol.Optional(CONF_KEY_SELECT, default=key_select or ""): vol.In(self._suggested_keys)}
            if self._suggested_keys
            else {}
        )
        schema_dict: dict[Any, Any] = {
            vol.Optional(CONF_JQ_FILTER, default=jq_filter): str,
            **key_field,
            vol.Optional(CONF_DATA_TYPE, default=data_type): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
            vol.Optional("scan_interval", default=scan_interval): int,
            vol.Optional(CONF_REFRESH, default=False): bool,
            vol.Optional(CONF_CREATE, default=False): bool,
        }
        schema = vol.Schema(schema_dict)

        # Build description previews
        previews: list[str] = []
        if self._raw_output:
            previews.append("Raw sample (truncated):\n" + self._raw_output[:600])
        if self._last_filter_value is not None:
            previews.append("Filtered value:\n" + str(self._last_filter_value)[:400])
        description_placeholders = {"test_output": "\n\n".join(previews)}

        return self.async_show_form(
            step_id="select",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def _async_fetch_sample(self):
        if not self._url:
            return
        cmd = f"curl -s {self._url}"
        def run_curl():
            try:
                result = subprocess.run(
                    cmd,
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
        self._suggested_keys = []
        try:
            parsed = json.loads(self._raw_output)
            if isinstance(parsed, dict):
                self._suggested_keys = [str(k) for k in list(parsed.keys())[:50]]
        except Exception:
            pass

    def _apply_filter(self, jq_filter: str) -> Any:
        if not jq_filter or not self._raw_output:
            return None
        if not jq_filter.startswith('.'):
            return None
        try:
            parsed = json.loads(self._raw_output)
        except Exception:
            return None
        current: Any = parsed
        for part in jq_filter[1:].split('.'):
            if part == "":
                continue
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    @staticmethod
    def async_get_options_flow(config_entry):  # type: ignore[override]
        return MyCurlOptionsFlowHandler(config_entry)


class MyCurlOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):  # type: ignore[override]
        errors: dict[str, str] = {}
        data = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=data.get(CONF_NAME, DEFAULT_NAME)): str,
                vol.Required(CONF_URL, default=data.get(CONF_URL, "")): str,
                vol.Optional(CONF_JQ_FILTER, default=data.get(CONF_JQ_FILTER, "")): str,
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
