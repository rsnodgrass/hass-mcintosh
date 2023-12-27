"""Config flow for easy setup"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_URL

from . import UnsupportedError, validate_connection
from .const import DEFAULT_URL, DOMAIN

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_UNSUPPORTED = "unsupported"


class McIntoshConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Mcintosh integration."""

    VERSION = 1

    discovered_device: AVDeviceInfo

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user initiated device additions."""
        errors = {}
        url = DEFAULT_URL

        if user_input is not None:
            url = user_input[CONF_URL].strip()

            try:
                info = await validate_connection(model_id, url, serial_config)
            except ConnectionError:
                errors["base"] = ERROR_CANNOT_CONNECT
            except UnsupportedError:
                errors["base"] = ERROR_UNSUPPORTED
            else:
                url = info.url

                # await self.async_set_unique_id(info.serial, raise_on_progress=False)
                # self._abort_if_unique_id_configured(updates={CONF_URL: URL})

                name = "McIntosh"

                return self.async_create_entry(
                    title=f"{info.name}",
                    data={CONF_URL: url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=url): str}),
            errors=errors,
        )
