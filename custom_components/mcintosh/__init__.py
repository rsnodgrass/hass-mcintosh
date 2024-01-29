"""
McIntosh A/V for Home Assistant
"""
from homeassistant.core import HomeAssistant

PLATFORMS = ['media_player']


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the McIntosh Multi-Zone Amplifier component."""
    return True
