
# MyCurl

A Home Assistant custom component that creates sensors based on the output of curl commands.

## Installation

1. Copy the `custom_components/mycurl` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Configure the integration in your `configuration.yaml`.


## Features
- Create sensors that run curl commands and use their output as sensor values.


## Usage


### UI-based setup (recommended)

1. Install MyCurl via HACS.
2. Go to Home Assistant → Settings → Devices & Services → Integrations.
3. Click "Add Integration" and search for "MyCurl".
4. Enter the sensor name, curl command, data type (numeric/text), and scan interval in the UI form.
5. **Test your curl command before saving:** Use the "Test Command" button to run your curl command and see the output. This helps you tweak your jq filter or command to get the exact value you want (e.g. `| jq -r .bpi.USD.rate_float`).
6. After setup, you can change options (like data type or scan interval) from the UI at any time.
7. The sensor will be created and managed from the UI—no need to edit configuration.yaml!

### YAML setup (legacy, still supported)

Add an entry like this to your `configuration.yaml`:

```yaml
# Numeric sensor example (for graphs/statistics)
sensor:
	- platform: mycurl
		name: "Bitcoin Price"
		data_type: numeric
		curl_command: "curl -s https://api.coindesk.com/v1/bpi/currentprice/BTC.json | jq -r .bpi.USD.rate_float"
		scan_interval: 300

# Text sensor example (default)
	- platform: mycurl
		name: "Example Text"
		data_type: text
		curl_command: "echo 'Hello from MyCurl'"
		scan_interval: 300
```

This will create a numeric sensor (for graphs/statistics) and a text sensor (for plain text values).

**Note:**
- Use `data_type: numeric` for sensors you want to graph or use in statistics (output must be a number).
- Use `data_type: text` (or omit) for sensors that return text.
- Make sure any required tools (like `jq`) are installed on your Home Assistant system.

## HACS Compatibility
This repository is structured for HACS installation.

## License
MIT

## Author
[@minermartijn](https://github.com/minermartijn)
