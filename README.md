# HA Curl Plugin

A Home Assistant custom component that creates sensors based on the output of curl commands.

## Installation

1. Copy the `custom_components/ha_curl_plugin` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Configure the integration in your `configuration.yaml`.


## Features
- Create sensors that run curl commands and use their output as sensor values.

## Usage

Add an entry like this to your `configuration.yaml`:

```yaml
sensor:
	- platform: ha_curl_plugin
		name: "Bitcoin Price"
		curl_command: "curl -s https://api.coindesk.com/v1/bpi/currentprice/BTC.json | jq -r .bpi.USD.rate_float"
		scan_interval: 300
```

This will create a sensor that fetches the current Bitcoin price in USD every 5 minutes.

**Note:** You can use any curl command that outputs a value. Make sure any required tools (like `jq`) are installed on your Home Assistant system.

## HACS Compatibility
This repository is structured for HACS installation.

## License
MIT

## Author
[@minermartijn](https://github.com/minermartijn)
