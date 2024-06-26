# McIntosh A/V Control for Home Assistant (IMPLEMENTATION IN PROGRESS)

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/v/release/rsnodgrass/hass-mcintosh.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-mcintosh.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/MIT)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/DYks67r)

![McIntosh Logo](https://raw.githubusercontent.com/rsnodgrass/hass-mcintosh/main/brands/logo.png)

# THIS DO NOT WORK! THIS IS IN PROGRESS.

My MX160 was broken in shipping and so I no longer have a device for testing or development so progress has been slow. This integration and underlying libraries is expected to be completed late 2024.

## LOOKING TO BUY MX160 or MX170

If you have an MX160 or MX170 you are looking to sell, please contact me.

## Support

Visit the [community support discussion thread](XXXXXX) for issues with this integration. If you have a code change or bug fix, feel free to submit a Pull Request.

### Supported Devices

See *[pyavcontrol](https://github.com/rsnodgrass/pyavcontrol/blob/main/SUPPORTED.md#McIntosh)* for a full list of supported hardware.

## Installation

### Step 1: Install Custom Components

ake sure that [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) is installed and then add the "Integration" repository: `rsnodgrass/hass-mcintosh`.

### Step 2: Configuration

This integration is completely configured via config flow.

#### Example OLD-STYLE configuration.yaml:

```yaml
media_player:
  - platform: mcintosh
    model: mcintosh_mx160
    url: /dev/ttyUSB0
    sources:
      1:
        name: "Sonos"
      5:
        name: "FireTV"
```

## See Also

* [Community support discussion thread](https://community.home-assistant.io/t/mcintosh-dayton-audio-sonance-multi-zone-amps/450908)
* [pyavcontrol](https://github.com/rsnodgrass/pyavcontrol)
* [RS232 to USB cable](https://www.amazon.com/RS232-to-USB/dp/B0759HSLP1?tag=carreramfi-20)
