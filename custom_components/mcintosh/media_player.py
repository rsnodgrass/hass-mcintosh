"""Home Assistant McIntosh Media Player"""

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    CONF_URL,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from pyavcontrol import DeviceClient
from pyavcontrol.config import CONFIG
from pyavcontrol.helper import construct_async_client
from ratelimit import limits

from .const import CONF_BAUD_RATE, CONF_MODEL, CONF_URL, DOMAIN

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

CONF_SOURCES = 'sources'

# Valid source ids:
#    monoprice6: 1-6 (Monoprice and Dayton Audio)
#    mcintosh8:   1-8
SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=8))
SOURCE_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME, default='Unknown Source'): cv.string}
)

SUPPORTED_MODELS = ['mcintosh_mx160']

# schema for media player service calls
SERVICE_CALL_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.comp_entity_ids})

MINUTES = 60
MAX_VOLUME = 100  # FIXME


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    namespace = 'mcintosh'  # FIXME
    model_id = config.get(CONF_MODEL)
    url = config.get(CONF_URL)

    config_overrides = {}
    if baud := config.get(CONF_BAUD_RATE):
        config_overrides[CONFIG.baudrate] = baud

    try:
        # connect to the device
        client = await construct_async_client(
            model_id, url, hass.loop, connection_config=config_overrides
        )

    except Exception as e:
        LOG.error(f"Failed connecting to '{model_id}' at {url}", e)
        raise PlatformNotReady

    # FIXME: default to the name of the device...from pyavcontrol client
    player_name = config.get(CONF_NAME)

    # add Media Player for the main control unit
    entities = [McIntoshMediaPlayer(namespace, player_name, client)]
    async_add_entities(entities, True)  # update_before_add=True)


class McIntoshMediaPlayer(MediaPlayerEntity):
    def __init__(self, namespace: str, name: str, client: DeviceClient):
        self._name = name
        self._client = client

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

        self._unique_id = f'{DOMAIN}_{namespace}_{name}'.lower().replace(' ', '_')

    async def async_update(self):
        """Retrieve the latest state."""
        try:
            LOG.debug(f'Updating {self.zone_info}')
            status = await self._amp.zone_status(self._zone_id)
            if not status:
                return
        except Exception as e:
            # log up to two times within a specific period to avoid saturating the logs
            @limits(calls=2, period=10 * MINUTES)
            def log_failed_zone_update(e):
                LOG.warning(f'Failed updating {self.zone_info}: {e}')

            log_failed_zone_update(e)
            return

        LOG.debug(f'{self.zone_info} status update: {status}')
        self._status = status

        source_id = status.get('source')
        if source_id:
            source_name = self._source_id_to_name.get(source_id)
            if source_name:
                self._source = source_name
            else:
                # sometimes the client may have not configured a source, but if the amplifier is set
                # to a source other than one defined, go ahead and dynamically create that source. This
                # could happen if the user changes the source through a different app or command.
                source_name = f'Source {source_id}'
                LOG.warning(
                    f"Undefined source id {source_id} for {self.zone_info}, adding '{source_name}'!"
                )
                self._source_id_to_name[source_id] = source_name
                self._source_name_to_id[source_name] = source_id

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def name(self):
        """Return the amp's name."""
        return self._name

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

        self._client.source.set(source)

    async def async_turn_on(self):
        self._client.power.on()

        # schedule a poll of the status of the zone ASAP to pickup volume levels/etc
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_turn_off(self):
        self._client.power.off()

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._client.mute.on()

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0—1.0"""
        # FIXME: translate to McIntosh...how to get max volume?
        amp_volume = int(volume * MAX_VOLUME)
        LOG.debug(f'Setting volume to {amp_volume} (HA volume {volume})')
        self._client.volume.set(volume={amp_volume})

    async def async_volume_up(self):
        self._client.volume.up()

    async def async_volume_down(self):
        self._client.volume.down()

    @property
    def icon(self):
        if self.state == STATE_OFF or self.is_volume_muted:
            return 'mdi:speaker-off'
        return 'mdi:speaker'
