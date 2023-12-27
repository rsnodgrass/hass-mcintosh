"""
McIntosh Multi-Zone Amplifier Control for Home Assistant
"""
from homeassistant.core import HomeAssistant

PLATFORMS = ["media_player"]


@dataclass
class RS232DeviceInfo:
    """Metadata for a RS232/IP device."""

    model_id: str
    url: str
    baud: int
    name: str


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the McIntosh Multi-Zone Amplifier component."""
    return True


async def validate_connection(
    model_id: str, url: str, serial_config: dict
) -> RS232DeviceInfo:
    """Validate by connecting to the AV device"""

    model_def = DeviceModelLibrary.create().load_model(model_id, event_loop=loop)
    client = DeviceClient.create(model_def, url)

    try:
        await client.connect()
    except ConnectionError:
        await client.disconnect()
        raise

    # FIXME: get fro the model_def!!!
    manufacturer = model_def.get("manufacturer").get("name")
    model = model_def.get("manufacturer").get("model")
    friendly_name = "{manufacturer} {model}"

    info = AVDeviceInfo(
        model_id=model_id, host=device.host, baud=9600, name=friendly_name
    )

    await client.disconnect()
    return info
