
# MyCurl

A Home Assistant custom component that creates sensors based on the output of curl commands.

## Installation

1. Copy the `custom_components/mycurl` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Configure the integration in your `configuration.yaml`.


## Features
- Create sensors that run curl commands and use their output as sensor values.

## Usage



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
