# McIntosh A/V Control for Home Assistant

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/v/release/rsnodgrass/hass-mcintosh.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-mcintosh.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/DYks67r)


![McIntosh Logo](https://github.com/rsnodgrass/hass-mcintosh/blob/master/brands/logo.png?raw=true)


## Support

Visit the [community support discussion thread](https://community.home-assistant.io/t/mcintosh-dayton-audio-sonance-multi-zone-amps/450908) for issues with this integration. If you have a code change or bug fix, feel free to submit a Pull Request.

### Supported Devices

See *[pyavcontrol](https://github.com/rsnodgrass/pyavcontrol/blob/main/SUPPORTED.md#McIntosh)* for a full list of supported hardware.

## Installation

### Step 1: Install Custom Components

ake sure that [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) is installed and then add the "Integration" repository: `rsnodgrass/hass-mcintosh`.

### Step 2: Configuration

Configuration is similar to the monoprice component here: https://www.home-assistant.io/integrations/monoprice/

#### Example configuration.yaml:

```yaml
media_player:
  - platform: mcintosh
    type: mcintosh8
    port: /dev/ttyUSB0
    zones:
      11:
        name: "Main Bedroom"
      12:
        name: "Living Room"
      13:
        name: "Kitchen"
    sources:
      1:
        name: "Sonos"
      5:
        name: "FireTV"
```

## See Also

* [Community support discussion thread](https://community.home-assistant.io/t/mcintosh-dayton-audio-sonance-multi-zone-amps/450908)
* [pyavcontrol](https://github.com/rsnodgrass/pyavcontrol)
