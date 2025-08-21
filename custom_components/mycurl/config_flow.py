
import logging
import json
import asyncio
from typing import Any, Dict, List, Optional

import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from .sensor import (
    CONF_CURL_COMMAND,
    CONF_DATA_TYPE,
    DATA_TYPE_NUMERIC,
    DATA_TYPE_TEXT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    build_curl_command,
)

_LOGGER = logging.getLogger(__name__)

CONF_URL = "url"
CONF_JQ_FILTER = "jq_filter"
CONF_KEY_SELECT = "key_select"
CONF_REFRESH = "refresh"
CONF_CREATE = "create"
CONF_PRESET = "preset"
CONF_API_KEY = "api_key"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_HEADERS = "headers"
CONF_METHOD = "method"

# Enhanced presets with more popular APIs
PRESETS = {
    "Random Advice": {
        "name": "Random Advice",
        "url_template": "https://api.adviceslip.com/advice",
        "description": "Get a random piece of advice",
        "required_params": [],
        "sensors": [
            {"key": "slip.advice", "name": "Advice", "type": DATA_TYPE_TEXT},
            {"key": "slip.id", "name": "Advice ID", "type": DATA_TYPE_NUMERIC},
        ],
    },
    "Trivia Question": {
        "name": "Trivia Question",
        "url_template": "https://opentdb.com/api.php?amount=1",
        "description": "Get a random trivia question",
        "required_params": [],
        "sensors": [
            {"key": "results[0].question", "name": "Question", "type": DATA_TYPE_TEXT},
            {"key": "results[0].correct_answer", "name": "Correct Answer", "type": DATA_TYPE_TEXT},
            {"key": "results[0].category", "name": "Category", "type": DATA_TYPE_TEXT},
            {"key": "results[0].difficulty", "name": "Difficulty", "type": DATA_TYPE_TEXT},
            {"key": "results[0].type", "name": "Type", "type": DATA_TYPE_TEXT},
        ],
    },
    "Random Activity": {
        "name": "Random Activity",
        "url_template": "https://bored-api.appbrewery.com/random",
        "description": "Get a random activity suggestion",
        "required_params": [],
        "sensors": [
            {"key": "activity", "name": "Activity", "type": DATA_TYPE_TEXT},
            {"key": "type", "name": "Type", "type": DATA_TYPE_TEXT},
            {"key": "participants", "name": "Participants", "type": DATA_TYPE_NUMERIC},
            {"key": "price", "name": "Price", "type": DATA_TYPE_NUMERIC},
            {"key": "availability", "name": "Availability", "type": DATA_TYPE_NUMERIC},
            {"key": "accessibility", "name": "Accessibility", "type": DATA_TYPE_TEXT},
            {"key": "duration", "name": "Duration", "type": DATA_TYPE_TEXT},
            {"key": "kidFriendly", "name": "Kid Friendly", "type": DATA_TYPE_TEXT},
            {"key": "link", "name": "Link", "type": DATA_TYPE_TEXT},
            {"key": "key", "name": "Key", "type": DATA_TYPE_TEXT},
        ],
    },
    "Random Dog Picture": {
        "name": "Random Dog Picture",
        "url_template": "https://dog.ceo/api/breeds/image/random",
        "description": "Get a random dog image URL",
        "required_params": [],
        "sensors": [
            {"key": "message", "name": "Dog Image URL", "type": DATA_TYPE_TEXT},
            {"key": "status", "name": "Status", "type": DATA_TYPE_TEXT},
        ],
    },
    "Random Cat Picture": {
        "name": "Random Cat Picture",
        "url_template": "https://api.thecatapi.com/v1/images/search",
        "description": "Get a random cat image URL",
        "required_params": [],
        "sensors": [
            {"key": "[0].url", "name": "Cat Image URL", "type": DATA_TYPE_TEXT},
            {"key": "[0].width", "name": "Width", "type": DATA_TYPE_NUMERIC},
            {"key": "[0].height", "name": "Height", "type": DATA_TYPE_NUMERIC},
        ],
    },
    "Fox Picture": {
        "name": "Fox Picture",
        "url_template": "https://randomfox.ca/floof/",
        "description": "Get a random fox image URL",
        "required_params": [],
        "sensors": [
            {"key": "image", "name": "Fox Image URL", "type": DATA_TYPE_TEXT},
            {"key": "link", "name": "Link", "type": DATA_TYPE_TEXT},
        ],
    },
    "Chuck Norris Joke": {
        "name": "Chuck Norris Joke",
        "url_template": "https://api.chucknorris.io/jokes/random",
        "description": "Get a random Chuck Norris joke",
        "required_params": [],
        "sensors": [
            {"key": "value", "name": "Joke", "type": DATA_TYPE_TEXT},
            {"key": "icon_url", "name": "Icon URL", "type": DATA_TYPE_TEXT},
            {"key": "url", "name": "Joke URL", "type": DATA_TYPE_TEXT},
            {"key": "id", "name": "Joke ID", "type": DATA_TYPE_TEXT},
        ],
    },
    "Kanye West Quote": {
        "name": "Kanye West Quote",
        "url_template": "https://api.kanye.rest",
        "description": "Get a random Kanye West quote",
        "required_params": [],
        "sensors": [
            {"key": "quote", "name": "Quote", "type": DATA_TYPE_TEXT},
        ],
    },
    "Random Cat Fact": {
        "name": "Random Cat Fact",
        "url_template": "https://catfact.ninja/fact",
        "description": "Get a random cat fact",
        "required_params": [],
        "sensors": [
            {"key": "fact", "name": "Fact", "type": DATA_TYPE_TEXT},
            {"key": "length", "name": "Length", "type": DATA_TYPE_NUMERIC},
        ],
    },
    "Random Useless Fact": {
        "name": "Random Useless Fact",
        "url_template": "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",
        "description": "Get a random useless fact",
        "required_params": [],
        "sensors": [
            {"key": "text", "name": "Fact", "type": DATA_TYPE_TEXT},
            {"key": "source", "name": "Source", "type": DATA_TYPE_TEXT},
            {"key": "source_url", "name": "Source URL", "type": DATA_TYPE_TEXT},
            {"key": "permalink", "name": "Permalink", "type": DATA_TYPE_TEXT},
        ],
    },
    "Random Joke": {
        "name": "Random Joke",
        "url_template": "https://official-joke-api.appspot.com/random_joke",
        "description": "Get a random joke (setup and punchline)",
        "required_params": [],
        "sensors": [
            {"key": "setup", "name": "Setup", "type": DATA_TYPE_TEXT},
            {"key": "punchline", "name": "Punchline", "type": DATA_TYPE_TEXT},
            {"key": "type", "name": "Type", "type": DATA_TYPE_TEXT},
            {"key": "id", "name": "Joke ID", "type": DATA_TYPE_NUMERIC},
        ],
    },
}


class MyCurlConfigFlow(config_entries.ConfigFlow, domain="mycurl"):
    """Config flow for MyCurl integration."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._name: Optional[str] = None
        self._url: Optional[str] = None
        self._raw_output: Optional[str] = None
        self._parsed: Optional[Any] = None
        self._path: List[str] = []
        self._preset_data: Optional[Dict[str, Any]] = None
        self._preset_params: Dict[str, str] = {}
        self._key_filter: str = ""
        self._last_filter_value: Optional[str] = None
        self._pending_finalize: bool = False

    async def async_step_user(self, user_input=None):
        """Handle the initial step - show preset selection."""
        return await self.async_step_preset()

    async def async_step_preset(self, user_input=None):
        """Handle preset selection."""
        errors = {}
        if user_input is not None:
            preset_key = user_input.get(CONF_PRESET)
            if preset_key == "custom":
                return await self.async_step_custom()
            if preset_key in PRESETS:
                self._preset_data = PRESETS[preset_key]
                self._name = self._preset_data["name"]
                required_params = self._preset_data.get("required_params", [])
                if required_params:
                    return await self.async_step_preset_params()
                # No parameters needed, configure URL and create all sensors with scan_interval=300
                self._url = self._preset_data["url_template"]
                sensors = []
                for sensor in self._preset_data.get("sensors", []):
                    jq_filter = f".{sensor['key']}" if not sensor['key'].startswith('.') else sensor['key']
                    sensor_data = {
                        CONF_NAME: f"{self._name} - {sensor['name']}",
                        CONF_URL: self._url,
                        CONF_JQ_FILTER: jq_filter,
                        CONF_DATA_TYPE: sensor['type'],
                        CONF_SCAN_INTERVAL: 300,
                    }
                    sensor_data[CONF_CURL_COMMAND] = build_curl_command(self._url, jq_filter)
                    sensors.append(sensor_data)
                if len(sensors) == 1:
                    return self.async_create_entry(title=sensors[0][CONF_NAME], data=sensors[0])
                return self.async_create_entry(title=self._name, data={"sensors": sensors, "preset": self._preset_data["name"]})
            errors[CONF_PRESET] = "invalid_preset"

        # Build preset options
        preset_options = {
            key: f"{preset['name']} - {preset['description']}"
            for key, preset in PRESETS.items()
        }
        preset_options["custom"] = "Custom URL (manual configuration)"
        schema = vol.Schema({vol.Required(CONF_PRESET): vol.In(preset_options)})
        return self.async_show_form(
            step_id="preset",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "preset_count": str(len(PRESETS)),
                "test_output": "Choose a popular API preset or create a custom configuration."
            },
        )

    async def async_step_preset_params(self, user_input=None):
        """Handle preset parameter configuration."""
        errors = {}
        if user_input is not None:
            self._preset_params.update(user_input)
            required_params = self._preset_data.get("required_params", [])
            for param in required_params:
                if not user_input.get(param, "").strip():
                    errors[param] = "required"
            if not errors:
                url_template = self._preset_data["url_template"]
                try:
                    all_params = {
                        **self._preset_data.get("default_params", {}),
                        **self._preset_params,
                    }
                    self._url = url_template.format(**all_params)
                    # After params, create all sensors with scan_interval=300
                    sensors = []
                    for sensor in self._preset_data.get("sensors", []):
                        jq_filter = f".{sensor['key']}" if not sensor['key'].startswith('.') else sensor['key']
                        sensor_data = {
                            CONF_NAME: f"{self._name} - {sensor['name']}",
                            CONF_URL: self._url,
                            CONF_JQ_FILTER: jq_filter,
                            CONF_DATA_TYPE: sensor['type'],
                            CONF_SCAN_INTERVAL: 300,
                        }
                        sensor_data[CONF_CURL_COMMAND] = build_curl_command(self._url, jq_filter)
                        sensors.append(sensor_data)
                    if len(sensors) == 1:
                        return self.async_create_entry(title=sensors[0][CONF_NAME], data=sensors[0])
                    return self.async_create_entry(title=self._name, data={"sensors": sensors, "preset": self._preset_data["name"]})
                except KeyError as e:
                    errors["base"] = f"Missing parameter: {e}"

        required_params = self._preset_data.get("required_params", [])
        default_params = self._preset_data.get("default_params", {})
        schema_fields = {}
        for param in required_params:
            default_value = self._preset_params.get(param, default_params.get(param, ""))
            schema_fields[vol.Required(param, default=default_value)] = str
        schema_fields[vol.Optional(CONF_API_KEY, default=self._preset_params.get(CONF_API_KEY, ""))] = str
        schema = vol.Schema(schema_fields)
        param_help = [
            f"• {param}: Required for {self._preset_data['name']}"
            for param in required_params
        ]
        return self.async_show_form(
            step_id="preset_params",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "test_output": (
                    f"Configure parameters for {self._preset_data['name']}:\n" + "\n".join(param_help)
                )
            },
        )

    # Removed async_step_preset_sensors: presets now skip sensor selection and use scan_interval=300

    async def async_step_custom(self, user_input=None):
        """Handle custom URL configuration."""
        errors = {}
        
        if user_input is not None:
            name = user_input.get(CONF_NAME, DEFAULT_NAME).strip()
            url = user_input.get(CONF_URL, "").strip()
            
            if not url:
                errors[CONF_URL] = "required"
            else:
                self._name = name or DEFAULT_NAME
                self._url = url
                
                # Test URL and fetch sample
                test_result = await self._async_test_url()
                if test_result["success"]:
                    await self._async_fetch_sample()
                    return await self.async_step_select()
                else:
                    errors["base"] = f"Connection failed: {test_result['error']}"

        schema = vol.Schema({
            vol.Required(CONF_NAME, default=self._name or DEFAULT_NAME): str,
            vol.Required(CONF_URL, default=self._url or ""): str,
        })

        return self.async_show_form(
            step_id="custom",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "test_output": "Enter a name and URL for your custom endpoint."
            }
        )

    async def async_step_select(self, user_input=None):
        """Handle key selection for custom endpoints."""
        errors = {}
        key_filter = self._key_filter
        scan_interval = 300
        jq_filter = ""

        # Determine current container and build key list
        current_container = self._resolve_path(self._path) if self._path else self._parsed
        keys = []
        key_labels = {}
        auto_numeric = False
        auto_key = None
        preview_value = None

        if isinstance(current_container, dict):
            raw_keys = [str(k) for k in list(current_container.keys())]
            if key_filter:
                raw_keys = [k for k in raw_keys if key_filter.lower() in k.lower()]
            raw_keys = raw_keys[:150]

            # Sort keys: dicts first, then lists, then primitives
            def sort_key(k: str):
                v = current_container.get(k)
                if isinstance(v, dict):
                    return (0, k.lower())
                elif isinstance(v, list):
                    return (1, k.lower())
                else:
                    return (2, k.lower())

            raw_keys.sort(key=sort_key)

            for k in raw_keys:
                val = current_container.get(k)
                summary = self._summarize_value(val)
                icon = "📁" if isinstance(val, dict) else ("📋" if isinstance(val, list) else "🔢" if isinstance(val, (int, float)) else "📝")
                key_labels[k] = f"{icon} {k} = {summary}"

                # Auto-detect single numeric value
                if len(raw_keys) == 1 and isinstance(val, (int, float)):
                    auto_numeric = True
                    auto_key = k
                    preview_value = val

            keys = raw_keys

        # Add navigation option if we're in a nested path
        if self._path:
            keys = [".."] + keys
            key_labels[".."] = "⬆️ .. (go up)"

        if user_input is not None:
            # Handle auto-numeric case
            if auto_numeric and auto_key and not user_input.get(CONF_JQ_FILTER):
                jq_filter = f".{auto_key}"
                data_type = DATA_TYPE_NUMERIC
                scan_interval = user_input.get(CONF_SCAN_INTERVAL, 300)
            else:
                jq_filter = user_input.get(CONF_JQ_FILTER, "").strip()
                key_select = user_input.get(CONF_KEY_SELECT)
                data_type = user_input.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)
                scan_interval = user_input.get(CONF_SCAN_INTERVAL, 300)
                key_filter = user_input.get("key_filter", "").strip()
                self._key_filter = key_filter

                # Handle navigation
                if key_select == "..":
                    if self._path:
                        self._path.pop()
                    return await self.async_step_select()
                elif key_select and key_select in current_container:
                    target = current_container[key_select]
                    if isinstance(target, dict):
                        # Navigate deeper
                        self._path.append(key_select)
                        return await self.async_step_select()
                    else:
                        # Select this value
                        jq_filter = self._compose_filter(self._path + [key_select])
                        self._pending_finalize = True

            # Finalize if we have a filter
            # Only allow valid jq_filter (not empty or just '.')
            if jq_filter and jq_filter != ".":
                value_preview = self._apply_filter(jq_filter)
                if value_preview is not None:
                    self._last_filter_value = str(value_preview)[:400]

                    data = {
                        CONF_NAME: self._name or DEFAULT_NAME,
                        CONF_URL: self._url,
                        CONF_JQ_FILTER: jq_filter,
                        CONF_DATA_TYPE: data_type,
                        CONF_SCAN_INTERVAL: scan_interval,
                    }
                    data[CONF_CURL_COMMAND] = build_curl_command(self._url, jq_filter)
                    return self.async_create_entry(title=data[CONF_NAME], data=data)
                else:
                    errors[CONF_JQ_FILTER] = "Filter returned no value"
            elif not jq_filter or jq_filter == ".":
                # No filter: treat as raw output, do not pass jq_filter
                data = {
                    CONF_NAME: self._name or DEFAULT_NAME,
                    CONF_URL: self._url,
                    CONF_JQ_FILTER: "",
                    CONF_DATA_TYPE: data_type,
                    CONF_SCAN_INTERVAL: scan_interval,
                }
                data[CONF_CURL_COMMAND] = build_curl_command(self._url, "")
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        # Build form schema
        schema_fields = {}

        if auto_numeric and auto_key:
            # Simple case: single numeric value
            schema_fields[vol.Optional(CONF_DATA_TYPE, default=DATA_TYPE_NUMERIC)] = vol.In([DATA_TYPE_NUMERIC])
            schema_fields[vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval)] = vol.All(
                int, vol.Range(min=5, max=3600)
            )
        else:
            # Full configuration
            schema_fields[vol.Optional(CONF_DATA_TYPE, default=DATA_TYPE_TEXT)] = vol.In([DATA_TYPE_NUMERIC, DATA_TYPE_TEXT])
            schema_fields[vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval)] = vol.All(
                int, vol.Range(min=5, max=3600)
            )
            schema_fields[vol.Optional(CONF_JQ_FILTER, default=jq_filter)] = str
            schema_fields[vol.Optional("key_filter", default=key_filter)] = str

            if keys:
                schema_fields[vol.Optional(CONF_KEY_SELECT, default="")] = vol.In({
                    "": "Select a key...",
                    **key_labels
                })

        schema = vol.Schema(schema_fields)

        # Build preview
        preview_lines = []
        
        # Show sample data
        if self._parsed:
            try:
                pretty_json = json.dumps(self._parsed, indent=2)[:800]
                preview_lines.append("📄 Sample JSON response:")
                preview_lines.append(pretty_json)
            except Exception:
                preview_lines.append(f"📄 Raw response: {self._raw_output[:400]}")
        elif self._raw_output:
            preview_lines.append(f"📄 Raw response: {self._raw_output[:400]}")

        # Show current path
        if self._path:
            preview_lines.append(f"\n📂 Current path: {'.'.join(self._path)}")

        # Show preview of selected value
        if self._last_filter_value is not None:
            preview_lines.append(f"\n✅ Selected value: {self._last_filter_value}")

        # Show auto-detected value
        if auto_numeric and auto_key and preview_value is not None:
            preview_lines.append(f"\n🎯 Auto-detected: {auto_key} = {preview_value} (numeric)")

        # Show navigation tips
        if not auto_numeric:
            preview_lines.append("\n💡 Tips:")
            preview_lines.append("• Select 📁 folders to navigate deeper")
            preview_lines.append("• Select 🔢📝 values to create sensor")
            preview_lines.append("• Use 'key_filter' to search keys")
            if self._path:
                preview_lines.append("• Select ⬆️ .. to go back up")

        return self.async_show_form(
            step_id="select",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "test_output": "\n".join(preview_lines)
            }
        )

    async def _async_test_url(self) -> Dict[str, Any]:
        """Test if URL is accessible."""
        if not self._url:
            return {"success": False, "error": "No URL provided"}

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self._url) as response:
                    if response.status == 200:
                        return {"success": True, "status": response.status}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _async_fetch_sample(self):
        """Fetch sample data from the URL."""
        if not self._url:
            return

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self._url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            self._parsed = await response.json()
                            self._raw_output = json.dumps(self._parsed, indent=2)
                        else:
                            self._raw_output = await response.text()
                            try:
                                self._parsed = json.loads(self._raw_output)
                            except json.JSONDecodeError:
                                self._parsed = None
                    else:
                        self._raw_output = f"HTTP {response.status}"
                        self._parsed = None
        except Exception as e:
            self._raw_output = f"Error: {str(e)}"
            self._parsed = None
        
        # Reset navigation path
        self._path = []

    def _get_sensor_preview(self, key: str) -> str:
        """Get preview value for a sensor key."""
        if not self._parsed:
            return "No data"
        
        try:
            value = self._apply_filter(f".{key}")
            if value is None:
                return "null"
            return str(value)[:50]
        except Exception:
            return "Error"

    def _apply_filter(self, jq_filter: str) -> Any:
        """Apply a simple dot-notation filter to parsed JSON."""
        if not jq_filter or not self._parsed:
            return None
            
        if not jq_filter.startswith('.'):
            return None

        current = self._parsed
        parts = jq_filter[1:].split('.') if jq_filter != '.' else []
        
        for part in parts:
            if not part:
                continue
                
            # Handle array indices
            if part.isdigit():
                part = int(part)
            
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and isinstance(part, int) and 0 <= part < len(current):
                current = current[part]
            else:
                return None
                
        return current

    def _resolve_path(self, path: List[str]) -> Any:
        """Resolve a path in the parsed JSON."""
        node = self._parsed
        for p in path:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return None
        return node

    def _compose_filter(self, path: List[str]) -> str:
        """Compose a jq filter from a path."""
        if not path:
            return "."
        return "." + ".".join(path)

    def _summarize_value(self, val: Any) -> str:
        """Create a short summary of a value."""
        if isinstance(val, (int, float, bool)):
            return str(val)
        elif isinstance(val, str):
            return f'"{val[:30]}{"…" if len(val) > 30 else ""}"'
        elif isinstance(val, list):
            return f"Array[{len(val)}]"
        elif isinstance(val, dict):
            keys = list(val.keys())[:3]
            more = "…" if len(val.keys()) > 3 else ""
            return f"{{{', '.join(keys)}{more}}}"
        elif val is None:
            return "null"
        else:
            return str(val)[:30]

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow handler."""
        return MyCurlOptionsFlowHandler(config_entry)


class MyCurlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for MyCurl."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        errors = {}
        data = {**self.config_entry.data, **self.config_entry.options}
        
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_NAME, default=data.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_URL, default=data.get(CONF_URL, "")): str,
            vol.Optional(CONF_JQ_FILTER, default=data.get(CONF_JQ_FILTER, "")): str,
            vol.Optional(CONF_DATA_TYPE, default=data.get(CONF_DATA_TYPE, DATA_TYPE_TEXT)): vol.In([
                DATA_TYPE_NUMERIC, DATA_TYPE_TEXT
            ]),
            vol.Optional(CONF_SCAN_INTERVAL, default=data.get(
                CONF_SCAN_INTERVAL, 
                int(DEFAULT_SCAN_INTERVAL.total_seconds()) if hasattr(DEFAULT_SCAN_INTERVAL, 'total_seconds') else 300
            )): vol.All(int, vol.Range(min=5, max=3600)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )