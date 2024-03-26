"""
The McIntosh A/V integration.
"""
import logging
from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pyavcontrol import DeviceClient
from pyavcontrol.helper import construct_async_client

from .const import CONF_BAUD_RATE, CONF_MODEL, CONF_URL, DOMAIN
from .utils import get_connection_overrides

LOG = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER]


@dataclass
class DeviceClientDetails:
    client: DeviceClient
    config: Mapping[str, Any]


async def connect_to_device(hass: HomeAssistant, entry: ConfigEntry):
    config = entry.data
    url = config[CONF_URL]
    model_id = config[CONF_MODEL]

    try:
        # connect to the device to confirm everything works
        client = await construct_async_client(
            model_id, url, hass.loop, connection_config=get_connection_overrides(config)
        )
    except Exception as e:
        raise ConfigEntryNotReady(f'Connection failed to {model_id} @ {url}') from e

    # save under the entry id so multiple devices can be added to a single HASS
    hass.data[DOMAIN][entry.entry_id] = DeviceClientDetails(client, config)


async def config_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    LOG.info(f'Reconnecting to device after reconfiguration: {config_entry}')
    await connect_to_device(hass, config_entry)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up from a config entry."""
    # assert config_entry.unique_id  # FIXME
    hass.data.setdefault(DOMAIN, {})

    await connect_to_device(hass, config_entry)

    # FIXME: whenever config options are changed by user, callback config_update_lister
    config_entry.async_on_unload(
        config_entry.add_update_listener(config_update_listener)
    )

    # forward the setup to the media_player platform
    # hass.async_create_task(
    #    hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # )
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True
