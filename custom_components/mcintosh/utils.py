"""Various utilities for the McIntosh integration"""

from .const import CONF_BAUD_RATE


def get_connection_overrides(config: dict) -> dict:
    config_overrides = {}
    if baud := config.get(CONF_BAUD_RATE):
        config_overrides[CONF_BAUD_RATE] = baud
    return config_overrides
