"""Constants for the McIntosh integration"""
from __future__ import annotations

from typing import Final

DOMAIN: Final[str] = 'mcintosh'

DEFAULT_URL: Final = 'socket://mcintosh.local:4166'

CONF_URL: Final = 'url'
CONF_BAUD_RATE: Final = 'baud'
CONF_MODEL: Final = 'model_id'
CONF_SOURCES: Final = 'sources'

COMPATIBLE_MODELS: list[str] = []
