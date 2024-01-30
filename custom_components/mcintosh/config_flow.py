"""Config flow for easy setup"""
from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyavcontrol import DeviceModelLibrary
from pyavcontrol.config import CONFIG
from pyavcontrol.const import BAUD_RATES
from pyavcontrol.helper import construct_async_client

from .const import CONF_BAUD_RATE, CONF_MODEL, DEFAULT_URL, DOMAIN

LOG = logging.getLogger(__name__)

ERROR_CANNOT_CONNECT = {'base': 'cannot_connect'}
ERROR_UNSUPPORTED = {'base': 'unsupported'}

MCINTOSH_MODELS = []


class UnsupportedError(HomeAssistantError):
    """Error for unsupported device types."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Mcintosh."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    @staticmethod
    def supported_models():
        # load all the supported models from pyavcontrol and filter down to only McIntosh models
        supported_models = DeviceModelLibrary.create().supported_models()

        # NOTE: in future may need to be more selective to only include mcintosh_*
        # that meet specific criteria...e.g. not all may be media players.
        # Alternatively since new physical models are not released often, this
        # could also be a static list of models! (PROBABLY BEST OPTION)
        mcintosh_models = [x for x in supported_models if x.startswith('mcintosh')]
        # mcintosh_models = ['mcintosh_mx160']
        return mcintosh_models

    @staticmethod
    def config_schema(supported_models):
        # FIXME: do we need to repopulate with existing config?
        #  e.g. default=self._config_entry.options.get(CONF_URL),
        return vol.Schema(
            {
                vol.Optional(CONF_NAME, default='McIntosh Audio'): cv.string,
                vol.Required(CONF_MODEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=supported_models,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_URL, default=DEFAULT_URL): cv.url,
                vol.Optional(CONF_BAUD_RATE): vol.In(BAUD_RATES),
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step of selecting model to configure."""
        errors: dict[str, str] | None = None

        # NOTE: in future may need to be more selective to only include mcintosh_*
        # that meet specific criteria...e.g. not all may be media players.
        # Alternatively since new physical models are not released often, this
        # could also be a static list of models! (PROBABLY BEST OPTION)
        mcintosh_models = ConfigFlow.supported_models()
        LOG.info(f'Starting McIntosh config flow: {mcintosh_models}')

        if user_input is not None:
            LOG.info(f'Handling user input: {user_input}')

            name = user_input.get(CONF_NAME).strip()
            model_id = user_input[CONF_MODEL]
            url = user_input.get(CONF_URL).strip()
            baud = user_input.get(CONF_BAUD_RATE)

            try:
                if model_id not in mcintosh_models:
                    raise UnsupportedError

                config_overrides = {}
                if baud:
                    config_overrides[CONFIG.baudrate] = baud

                loop = asyncio.get_event_loop()

                # connect to the device to confirm everything works
                client = await construct_async_client(
                    model_id, url, loop, connection_config=config_overrides
                )

                # await self.async_set_unique_id(client.serial)
                # self._abort_if_unique_id_configured()

            except ConnectionError as e:
                errors = ERROR_CANNOT_CONNECT
                LOG.warning(f'Failed config_flow: {errors}', e)
            except UnsupportedError as e:
                errors = ERROR_UNSUPPORTED
                LOG.warning(f'Failed config_flow: {errors}', e)
            else:
                return self.async_create_entry(title='', data=user_input)

        LOG.info(f'Displaying standard form')
        # no user input yet, so display the form
        return self.async_show_form(
            step_id='user',
            data_schema=ConfigFlow.config_schema(mcintosh_models),
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component after it has already been setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Manage the options for the custom component."""
        errors: dict[str, str] = {}

        supported_models = ConfigFlow.supported_models()

        if user_input is not None:
            # Validation and additional processing logic omitted for brevity.
            # ...
            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return self.async_create_entry(title='', data=user_input)

        return self.async_show_form(
            step_id='init',
            data_schema=ConfigFlow.config_schema(supported_models),
            errors=errors,
        )
