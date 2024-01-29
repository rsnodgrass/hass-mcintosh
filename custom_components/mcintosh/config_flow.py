"""Config flow for easy setup"""
from __future__ import annotations

import logging
import asyncio
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyavcontrol import DeviceModelLibrary, construct_async_client
from pyavcontrol.config import CONFIG

from .const import CONF_BAUD_RATE, CONF_MODEL, DEFAULT_URL, DOMAIN

LOG = logging.getLogger(__name__)

ERROR_CANNOT_CONNECT = {'base': 'cannot_connect'}
ERROR_UNSUPPORTED = {'base': 'unsupported'}


class UnsupportedError(HomeAssistantError):
    """Error for unsupported device types."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Mcintosh."""

    VERSION = 1

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step of selecting model to configure."""
        errors: dict[str, str] | None = None

        # load all the supported models from pyavcontrol and filter down to only McIntosh models
        supported_models = DeviceModelLibrary.create().supported_models()

        # NOTE: in future may need to be more selective to only include mcintosh_*
        # that meet specific criteria...e.g. not all may be media players.
        # Alternatively since new physical models are not released often, this
        # could also be a static list of models! (PROBABLY BEST OPTION)
        mcintosh_models = [x for x in supported_models if x.startswith('mcintosh')]
        # mcintosh_models = ['mcintosh_mx160']

        if user_input is not None:
            name = user_input.get(CONF_NAME).strip()
            model_id = user_input[CONF_MODEL]

            try:
                if model_id not in mcintosh_models:
                    raise UnsupportedError

            except ConnectionError:
                errors = ERROR_CANNOT_CONNECT
            except UnsupportedError:
                errors = ERROR_UNSUPPORTED
            else:
                return self.async_create_entry(
                    title=f'McIntosh {name}',
                    data={CONF_MODEL: model_id, CONF_NAME: name},
                )

        # no user input yet, so display the form
        return self.async_show_form(
            step_id='model',
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL, default=mcintosh_models[0]
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=mcintosh_models,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_NAME, default=False): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user initiated device additions."""
        errors: dict[str, str] | None = None

        if user_input:
            url = user_input.get(CONF_URL).strip()
            baud = user_input.get(CONF_BAUD_RATE)

            try:
                config_overrides = {}
                if baud:
                    config_overrides[CONFIG.baudrate] = baud

                model_id = 'mcintosh_mx160'  # FIXME (get from step 1)

                loop = asyncio.get_event_loop()

                # connect to the device to confirm everything works
                client = await construct_async_client(
                    model_id, url, loop, connection_config=config_overrides
                )
                client.is_connected()

            except ConnectionError:
                errors = ERROR_CANNOT_CONNECT
            except UnsupportedError:
                errors = ERROR_UNSUPPORTED
            else:
                await self.async_set_unique_id(user_input[CONF_URL])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f'McIntosh {user_input[CONF_URL]}', data={CONF_URL: url}
                )

        return self.async_show_form(
            step_id='connection',
            data_schema=vol.Schema({vol.Required(CONF_URL, default=DEFAULT_URL): str}),
            errors=errors,
        )
