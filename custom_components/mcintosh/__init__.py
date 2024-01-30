"""
McIntosh A/V for Home Assistant
"""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ['media_player']


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up platform from a ConfigEntry"""
    hass.data.setdefault(DOMAIN, {})

    # save under the entry id so multiple devices can be added to a single HASS
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # forward the setup to the media_player platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, 'media_player')
    )
    return True
