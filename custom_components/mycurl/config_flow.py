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
        self._parsed: Any | None = None
        self._suggested_keys: list[str] = []
        self._last_filter_value: str | None = None
        self._path: list[str] = []  # navigation path for nested dicts

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
            refresh = user_input.get(CONF_REFRESH)
            navigate_back = user_input.get("nav_back")
            drill = user_input.get("drill")
            create_flag = user_input.get(CONF_CREATE)
            jq_filter = user_input.get(CONF_JQ_FILTER, "").strip()
            key_select = user_input.get(CONF_KEY_SELECT) or None
            data_type = user_input.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)
            scan_interval = user_input.get("scan_interval", scan_interval)

            if refresh:
                await self._async_fetch_sample()
                self._path = []
            elif navigate_back:
                if self._path:
                    self._path.pop()
            elif drill and key_select:
                target = self._resolve_path(self._path + [key_select])
                if isinstance(target, dict):
                    self._path.append(key_select)
                else:
                    # If not a dict we consider selecting the value as filter
                    if not jq_filter:
                        jq_filter = self._compose_filter(self._path + [key_select])
            elif create_flag:
                # Compose filter from path if jq_filter empty and path not empty
                if not jq_filter and (self._path or key_select):
                    jq_filter = self._compose_filter(self._path + ([key_select] if key_select else []))
                value_preview = self._apply_filter(jq_filter)
                self._last_filter_value = None if value_preview is None else str(value_preview)[:400]
                if not jq_filter:
                    errors[CONF_JQ_FILTER] = "required"
                if not errors:
                    data: dict[str, Any] = {
                        CONF_NAME: self._name or DEFAULT_NAME,
                        CONF_URL: self._url,
                        CONF_JQ_FILTER: jq_filter,
                        CONF_DATA_TYPE: data_type,
                        "scan_interval": scan_interval,
                    }
                    data[CONF_CURL_COMMAND] = build_curl_command(self._url, jq_filter)
                    return self.async_create_entry(title=data[CONF_NAME], data=data)

            # If key selected (not drilling) and no jq filter yet, set a tentative preview
            if key_select and not jq_filter and not drill:
                tentative = self._compose_filter(self._path + [key_select])
                value_preview = self._apply_filter(tentative)
                self._last_filter_value = None if value_preview is None else str(value_preview)[:400]
            elif jq_filter:
                value_preview = self._apply_filter(jq_filter)
                self._last_filter_value = None if value_preview is None else str(value_preview)[:400]

        # Build schema for selection step
        key_field = {}
        current_container = self._resolve_path(self._path) if self._path else self._parsed
        self._suggested_keys = []
        if isinstance(current_container, dict):
            self._suggested_keys = [str(k) for k in list(current_container.keys())[:100]]
        if self._suggested_keys:
            key_field = {vol.Optional(CONF_KEY_SELECT, default=key_select or ""): vol.In(self._suggested_keys)}

        schema_dict: dict[Any, Any] = {
            vol.Optional(CONF_JQ_FILTER, default=jq_filter): str,
            **key_field,
            vol.Optional(CONF_DATA_TYPE, default=data_type): vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT]),
            vol.Optional("scan_interval", default=scan_interval): int,
            vol.Optional(CONF_REFRESH, default=False): bool,
            vol.Optional("nav_back", default=False): bool,
            vol.Optional("drill", default=False): bool,
            vol.Optional(CONF_CREATE, default=False): bool,
        }
        schema = vol.Schema(schema_dict)

        # Build description previews
        previews: list[str] = []
        if self._raw_output:
            previews.append("Raw sample (truncated):\n" + self._raw_output[:500])
        # Key/value preview table
        if isinstance(current_container, dict):
            kv_lines = []
            for k in self._suggested_keys[:25]:
                val = current_container.get(k)
                kv_lines.append(f"{k}: {self._summarize_value(val)}")
            previews.append("Keys:\n" + "\n".join(kv_lines))
        if self._path:
            previews.append("Path: " + ".".join(self._path))
        if self._last_filter_value is not None:
            previews.append("Value preview:\n" + str(self._last_filter_value))
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
        self._parsed = None
        try:
            self._parsed = json.loads(self._raw_output)
        except Exception:
            self._parsed = None
        self._path = []

    def _apply_filter(self, jq_filter: str) -> Any:
        if not jq_filter or not self._raw_output:
            return None
        if not jq_filter.startswith('.'):
            return None
        try:
            parsed = self._parsed if self._parsed is not None else json.loads(self._raw_output)
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

    def _resolve_path(self, path: list[str]) -> Any:
        node: Any = self._parsed
        for p in path:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return None
        return node

    def _compose_filter(self, path: list[str]) -> str:
        return "." + ".".join(path)

    def _summarize_value(self, val: Any) -> str:
        if isinstance(val, (int, float, bool)):
            return str(val)
        if isinstance(val, str):
            return val[:40] + ("…" if len(val) > 40 else "")
        if isinstance(val, list):
            return f"[list len={len(val)}]"
        if isinstance(val, dict):
            keys = list(val.keys())[:5]
            more = "…" if len(val.keys()) > 5 else ""
            return "{" + ", ".join(keys) + more + "}"
        if val is None:
            return "null"
        return str(val)[:40]

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
