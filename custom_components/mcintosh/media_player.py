"""Home Assistant Media Player for McIntosh, Monoprice and Dayton Audio multi-zone amplifiers"""

# FIXME: Add a MediaPlayer for the entire McIntosh unit to enable power on/off, mute, etc all zones

import logging

import voluptuous as vol
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
    CONF_ENTITY_NAMESPACE,
    CONF_NAME,
    CONF_PORT,
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.typing import HomeAssistantType
from pyavcontrol import CONFIG, construct_async_client
from ratelimit import limits
from serial import SerialException

from .const import (
    DOMAIN,
    SERVICE_JOIN,
    SERVICE_RESTORE,
    SERVICE_SNAPSHOT,
    SERVICE_UNJOIN,
)

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

CONF_SERIAL_CONFIG = 'rs232'
CONF_SERIAL_NUMBER = 'serial_number'  # allow for true unique id
CONF_SOURCES = 'sources'

# Valid source ids:
#    monoprice6: 1-6 (Monoprice and Dayton Audio)
#    mcintosh8:   1-8
SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=8))
SOURCE_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME, default='Unknown Source'): cv.string}
)

SERIAL_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(CONFIG.baudrate): vol.In(BAUD_RATES),
        vol.Optional(CONFIG.timeout): cv.small_float,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default='McIntosh House Audio'): cv.string,
        vol.Optional(CONF_TYPE, default='mcintosh8'): vol.In(SUPPORTED_AMP_TYPES),
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(CONF_ENTITY_NAMESPACE, default='mcintosh8'): cv.string,
        vol.Required(CONF_ZONES): vol.Schema({ZONE_IDS: ZONE_SCHEMA}),
        vol.Required(CONF_SOURCES): vol.Schema({SOURCE_IDS: SOURCE_SCHEMA}),
        vol.Optional(CONF_SERIAL_CONFIG): SERIAL_CONFIG_SCHEMA,
    }
)

# schema for media player service calls
SERVICE_CALL_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.comp_entity_ids})

MINUTES = 60


async def async_setup_platform(
    hass: HomeAssistantType, config, async_add_entities, discovery_info=None
):
    port = config.get(CONF_PORT)
    model_id = config.get(CONF_TYPE)

    try:
        """Set up the McIntosh amplifier platform."""
        namespace = config.get(
            CONF_ENTITY_NAMESPACE
        )  # FIXME: should this defualt to mode_name

        # allow manually overriding any of the serial configuration using the 'rs232' key
        config_overrides = config.get(CONF_SERIAL_CONFIG, {})
        client = await construct_async_client(
            model_id, port, hass.loop, connection_config=config_overrides
        )

        # FIXME: default to the name of the device...from pyavcontrol client
        player_name = config.get(CONF_NAME)

        # add Media Player for the main control unit
        entities = [Amplifier(namespace, player_name, client)]
        async_add_entities(entities, True)

        await async_setup_services(hass)

    except Exception as e:
        LOG.error(f"Failed connecting to '{model_id}' at {port}", e)
        raise PlatformNotReady


async def async_setup_services(hass: HomeAssistantType):
    # setup the service calls
    platform = entity_platform.current_platform.get()

    async def service_call_dispatcher(service_call):
        if all_entities := await platform.async_extract_from_service(service_call):
            for entity in all_entities:
                if service_call.service == SERVICE_SNAPSHOT:
                    await entity.async_snapshot()
                elif service_call.service == SERVICE_RESTORE:
                    await entity.async_restore()

    # register the save/restore snapshot services
    for service_call_name in (SERVICE_SNAPSHOT, SERVICE_RESTORE):
        hass.services.async_register(
            DOMAIN,
            service_call_name,
            service_call_dispatcher,
            schema=SERVICE_CALL_SCHEMA,
        )


class Amplifier(MediaPlayerEntity):
    """Representation of the amp."""

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
        """Set input source for all zones."""
        if source not in self._source_name_to_id:
            LOG.warning(
                f"Selected source '{source}' not valid for {self._name}, ignoring! Sources: {self._source_name_to_id}"
            )
            return

        self._client.source.set(source)

    async def async_turn_on(self):
        """Turn the media player on."""
        self._client.power.on()

        # schedule a poll of the status of the zone ASAP to pickup volume levels/etc
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_turn_off(self):
        """Turn the media player off."""
        self._client.power.off()

    async def async_snapshot(self):
        """Save zone's current state."""
        self._status_snapshot = await self._amp.zone_status(self._zone_id)
        LOG.info(f'Saved state snapshot for {self.zone_info}')

    async def async_restore(self):
        """Restore saved state."""
        if self._status_snapshot:
            await self._amp.restore_zone(self._status_snapshot)
            self.async_schedule_update_ha_state(force_refresh=True)
            LOG.info(f'Restored previous state for {self.zone_info}')
        else:
            LOG.warning(
                f'Restore service called for {self.zone_info}, but no snapshot previously saved.'
            )

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._client.mute.on()

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0—1.0"""
        # FIXME: translate to McIntosh
        amp_volume = int(volume * MAX_VOLUME)
        LOG.debug(f'Setting volume to {amp_volume} (HA volume {volume})')
        self._client.volume.set(volume={amp_volume})

    async def async_volume_up(self):
        """Volume up the media player."""
        self._client.volume.up()

        # FIXME: call the volume up API on the amp object, instead of manually increasing volume
        # reminder the volume is on the amplifier scale (0-38), not Home Assistants (1-100)
        await self._amp.set_volume(self._zone_id, min(volume + 1, MAX_VOLUME))

    async def async_volume_down(self):
        """Volume down media player."""
        self._client.volume.down()

    @property
    def icon(self):
        if self.state == STATE_OFF or self.is_volume_muted:
            return 'mdi:speaker-off'
        return 'mdi:speaker'
