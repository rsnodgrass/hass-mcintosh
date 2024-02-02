"""Home Assistant McIntosh Media Player"""

import logging
from typing import Final

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyavcontrol import DeviceClient

from . import McIntoshData
from .const import CONF_MODEL, CONF_URL, DOMAIN

LOG = logging.getLogger(__name__)

SUPPORTED_AMP_FEATURES = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

SUPPORTED_ZONE_FEATURES = (
    SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_STEP
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
)

MINUTES: Final = 60
MAX_VOLUME = 100  # FIXME


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data: McIntoshData = hass.data[DOMAIN][config_entry.entry_id]

    # add Media Player entity
    entities = [McIntoshMediaPlayer(config_entry, data.client)]
    async_add_entities(new_entities=entities, update_before_add=True)


class McIntoshMediaPlayer(MediaPlayerEntity):
    _attr_has_entity_name = True

    def __init__(self, config_entry: ConfigEntry, client: DeviceClient) -> None:
        self._config_entry = config_entry
        self._client = client

        self._attr_name = config_entry.data[CONF_NAME]
        self._model_id = config_entry.data[CONF_MODEL]

        self._attr_unique_id = (
            f'{DOMAIN}_{self._model_id}_{self._attr_name}'.lower().replace(' ', '_')
        )

        # FIXME: need API from pyavcontrol to get manufacter/model info (beside model_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry[CONF_URL])},
            manufacturer='McIntosh',
            model=self._model_id,
            name=self._attr_name,
            sw_version='Unknown',
        )

        # _attr_supported_features = XXX # FIXME: dynamically set features based on client features

        self._update_attr()

    @callback
    def _update_attr(self, client):
        # self._attr_extra_state_attributes = {
        #    "trigger1": client.trigger_status(trigger=1),
        #    "trigger2": client.trigger_status(trigger=2),
        # }
        pass

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        await self._initialize()

    async def _initialize(self) -> None:
        """Initialize connection dependent variables."""
        # self._software_status = await self._client.get_softwareupdate_status()
        LOG.debug('Connected to %s / %s', self._model_id, self._unique_id)

        await self._update_current_state()
        # await self._update_sources()

    async def _update_current_state(self) -> None:
        """Get current state of the device"""
        # FIXME: load all the various data from the client and populate state/attributes

        self._sources = []
        # HASS won't necessarily be running the first time this method is run
        if self.hass.is_running:
            self.async_write_ha_state()

    async def _update_sources(self) -> None:
        """Get sources for the specific product."""

        self._sources = []

        sources = {}  # FIXME
        self._source_id_to_name = sources  # [source_id]   -> source name
        self._source_name_to_id = {
            v: k for k, v in sources.items()
        }  # [source name] -> source_id

        # sort list of source names
        self._source_names = sorted(
            self._source_name_to_id.keys(), key=lambda v: self._source_name_to_id[v]
        )
        # TODO: Ideally the source order could be overridden in YAML config (e.g. TV should appear first on list).
        #       Optionally, we could just sort based on the zone number, and let the user physically wire in the
        #       order they want (doesn't work for pre-amp out channel 7/8 on some McIntosh)

        # HASS won't necessarily be running the first time this method is run
        if self.hass.is_running:
            self.async_write_ha_state()

    async def async_update(self):
        """Retrieve the latest state."""
        LOG.debug(f'Updating %s', self.unique_id)

    @property
    def state(self):
        """Return the amp's power state."""
        return STATE_UNKNOWN

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORTED_AMP_FEATURES

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_names

    async def async_select_source(self, source):
        if source not in self._source_name_to_id:
            LOG.warning(
                f"Selected source '{source}' not valid for {self._name}, ignoring! Sources: {self._source_name_to_id}"
            )
            return

        await self._client.source.set(source)

    async def async_turn_on(self):
        await self._client.power.on()

        # schedule a poll of the status of the zone ASAP to pickup volume levels/etc
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_turn_off(self):
        await self._client.power.off()

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        await self._client.mute.on()

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0—1.0"""
        # FIXME: translate to McIntosh...how to get max volume?
        scaled_volume = int(volume * MAX_VOLUME)
        LOG.debug(f'Setting volume to {scaled_volume} (HA volume {volume})')
        await self._client.volume.set(volume=scaled_volume)

    async def async_volume_up(self):
        await self._client.volume.up()

    async def async_volume_down(self):
        await self._client.volume.down()

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        # if self._volume.level and self._volume.level.level:
        #    return float(self._volume.level.level / 100)
        return None

    @property
    def icon(self) -> str | None:
        if self.state == STATE_OFF or self.is_volume_muted:
            return 'mdi:speaker-off'
        return 'mdi:speaker'
