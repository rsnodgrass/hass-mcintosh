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
class McIntoshData:
    client: DeviceClient
    config: Mapping[str, Any]


async def connect_client_from_config(hass: HomeAssistant, entry: ConfigEntry):
    config = entry.data

    url = config[CONF_URL]
    model_id = config[CONF_MODEL]

    try:
        # connect to the device to confirm everything works
        client = await construct_async_client(
            model_id, url, hass.loop, connection_config=get_connection_overrides(config)
        )
    except Exception as e:
        raise ConfigEntryNotReady(f'Unable to connect to {model_id} / {url}') from e

    # save under the entry id so multiple devices can be added to a single HASS
    hass.data[DOMAIN][entry.entry_id] = McIntoshData(client, config)


async def config_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    LOG.info(f'McIntosh reconfigured: {config_entry}')
    await connect_client_from_config(hass, config_entry)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up from a config entry."""
    assert config_entry.unique_id
    hass.data.setdefault(DOMAIN, {})

    # connect to the device
    await connect_client_from_config(hass, config_entry)

    # FIXME: whenever config options are changed by user, callback config_update_lister
    # entry.async_on_unload(entry.add_update_listener(config_update_listener))

    # forward the setup to the media_player platform
    # hass.async_create_task(
    #    hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # )
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True
