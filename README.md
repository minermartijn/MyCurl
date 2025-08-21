# MyCurl

A Home Assistant custom component that creates sensors based on the output of curl commands.

## Installation

1. Copy the `custom_components/mycurl` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Configure the integration in your `configuration.yaml`.


## Features
- Create sensors that run curl commands and use their output as sensor values.
- Modern UI config flow with:
	- Preset system for fun public APIs:
		- Random Advice
		- Trivia Question
		- Random Activity
		- Random Dog Picture
		- Random Cat Picture
		- Fox Picture
		- Chuck Norris Joke
		- Kanye West Quote
		- Random Cat Fact
		- Random Useless Fact
		- Random Joke
  - Auto key detection and data type selection for custom endpoints
  - Safe handling of jq filters (no more parse errors from empty or invalid filters)


## Usage

### UI-based setup (recommended)

1. Install MyCurl via HACS.
2. Go to Home Assistant → Settings → Devices & Services → Integrations.
3. Click "Add Integration" and search for "MyCurl".
4. Choose a preset (for fun public APIs) or select "Custom URL" to enter your own endpoint.
5. For presets, select which sensors you want to create (e.g. advice, joke, image URL, etc).
6. For custom endpoints, enter the URL. The integration will auto-detect available keys and data types, and let you select the value you want to use as a sensor.
7. The integration will preview the data and help you build a valid jq filter automatically. Invalid or empty filters are now handled safely (no more jq parse errors).
8. After setup, you can change options (like data type or scan interval) from the UI at any time.
9. The sensor will be created and managed from the UI—no need to edit configuration.yaml!

5. **Advanced:** If you want to test a curl command manually, you can use:

	```bash
	curl -s https://api.adviceslip.com/advice | jq -r .slip.advice
	curl -s https://opentdb.com/api.php?amount=1 | jq -r .results[0].question
	curl -s https://www.boredapi.com/api/activity | jq -r .activity
	curl -s https://dog.ceo/api/breeds/image/random | jq -r .message
	curl -s https://api.thecatapi.com/v1/images/search | jq -r '.[0].url'
	curl -s https://randomfox.ca/floof/ | jq -r .image
	curl -s https://api.chucknorris.io/jokes/random | jq -r .value
	curl -s https://api.kanye.rest | jq -r .quote
	curl -s https://catfact.ninja/fact | jq -r .fact
	curl -s https://uselessfacts.jsph.pl/api/v2/facts/random?language=en | jq -r .text
	curl -s https://official-joke-api.appspot.com/random_joke | jq -r .setup
	```
	(But the UI flow now helps you build this automatically!)

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

**Notes:**
- Use `data_type: numeric` for sensors you want to graph or use in statistics (output must be a number).
- Use `data_type: text` (or omit) for sensors that return text.
- Make sure any required tools (like `jq`) are installed on your Home Assistant system.
- The integration now prevents invalid or empty jq filters from causing errors. If you see a parse error, update to the latest version.

## HACS Compatibility
This repository is structured for HACS installation.

## License
MIT

## Author
[@minermartijn](https://github.com/minermartijn)
