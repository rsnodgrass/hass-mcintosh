"""
McIntosh A/V for Home Assistant
"""
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN

LOG = logging.getLogger(__name__)

PLATFORMS = ['media_player']


async def config_update_listener(hass, entry):
    """Handle options update."""
    LOG.error(f'Config options updates {entry.options}')


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up platform from a ConfigEntry"""
    hass.data.setdefault(DOMAIN, {})

    # save under the entry id so multiple devices can be added to a single HASS
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # whenever config options are changed by user, callback config_update_lister
    entry.async_on_unload(entry.add_update_listener(config_update_listener))

    # forward the setup to the media_player platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, 'media_player')
    )
    return True
