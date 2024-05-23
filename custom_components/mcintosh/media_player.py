"""Home Assistant McIntosh Media Player"""

import logging
from typing import Final

from homeassistant import core
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeviceClientDetails
from .const import CONF_MODEL, CONF_SOURCES, DOMAIN

LOG = logging.getLogger(__name__)

MINUTES: Final = 60
MAX_VOLUME = 100  # FIXME


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if data := hass.data[DOMAIN][config_entry.entry_id]:
        entities = [McIntoshMediaPlayer(config_entry, data)]
        async_add_entities(new_entities=entities, update_before_add=True)
    else:
        LOG.error(
            f'Missing pre-connected client for {config_entry}, cannot create MediaPlayer'
        )


@core.callback
def _get_sources_from_dict(data):
    sources_config = data[CONF_SOURCES]
    source_id_name = {int(index): name for index, name in sources_config.items()}
    source_name_id = {v: k for k, v in source_id_name.items()}
    source_names = sorted(source_name_id.keys(), key=lambda v: source_name_id[v])
    return [source_id_name, source_name_id, source_names]


@core.callback
def _get_sources(config_entry):
    if CONF_SOURCES in config_entry.options:
        data = config_entry.options
    else:
        data = config_entry.data
    return _get_sources_from_dict(data)


class McIntoshMediaPlayer(MediaPlayerEntity):
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )
    _attr_has_entity_name = True

    def __init__(self, config_entry: ConfigEntry, details: DeviceClientDetails) -> None:
        self._config_entry = config_entry
        self._details = details
        self._client = details.client

        # self._attr_name = config_entry.data[CONF_NAME]
        self._model_id = config_entry.data[CONF_MODEL]

        self._attr_unique_id = (
            f'{DOMAIN}_{self._model_id}_{self._client}'.lower().replace(' ', '_')
        )

        # name for this device should be manufacturer + the top most supported model as default
        device_model = self._client.model()
        manufacturer = (device_model.info.get('manufacturer', 'McIntosh'),)
        if supported_model_names := device_model.get('models', []):
            model_name = supported_model_names[0]

            # if multiple model names are supported by this client, include them in the attributes
            # for this media player as a UI convenience for users
            if len(supported_model_names) > 1:
                self._attr_supported_models['supported_models'] = (
                    supported_model_names  # FIXME
                )
        else:
            model_name = 'Media Player'

        # sources = _get_sources(config_entry)

        # NOTE: This currently only supports the MAIN zone for media devices, but in future
        # may want to add support for additional zones:
        # zones = ['Main']
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer=manufacturer,
            model='{model_name}',
            name=f'{manufacturer} {model_name}',  # entity name
            sw_version='Unknown',
        )

        # self._attr_source_list = sources

        # FIXME: if additional models supported, update the

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
        LOG.debug('Updating %s', self.unique_id)

        # poll the client for latest state for the device
        try:
            # FIXME: how to get current state?
            state = await self._client.get_status(self._zone_id)
        except Exception as e:
            LOG.warning(f'Could not update {self.unique_id}', e)
            return
        finally:
            if not state:
                return

        # FIXME
        self._attr_state = MediaPlayerState.ON if state.power else MediaPlayerState.OFF
        self._attr_volume_level = state.volume / MAX_VOLUME
        # self._attr_is_volume_muted = state.mute
        # idx = state.source
        # self._attr_source = self._source_id_name.get(idx)

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
        if self.state is MediaPlayerState.OFF or self.is_volume_muted:
            return 'mdi:speaker-off'
        return 'mdi:speaker'
