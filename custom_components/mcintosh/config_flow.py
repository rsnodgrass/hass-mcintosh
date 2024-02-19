"""Config flow for easy setup"""
from __future__ import annotations

import logging
import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyavcontrol import DeviceModelLibrary

# from pyavcontrol.const import BAUD_RATES
from pyavcontrol.helper import construct_async_client

BAUD_RATES = [9600]  # FIXME: remove

from . import get_connection_overrides
from .const import CONF_BAUD_RATE, CONF_MODEL, DEFAULT_URL, DOMAIN

LOG = logging.getLogger(__name__)

ERROR_CANNOT_CONNECT = {'base': 'cannot_connect'}
ERROR_UNSUPPORTED = {'base': 'unsupported'}

from homeassistant.const import CONF_PORT, CONF_URL


class UnsupportedDeviceError(HomeAssistantError):
    """Error for unsupported device types."""


def filter_models(prefix: str):
    # load all the supported models from pyavcontrol and filter down to only McIntosh models
    supported_models = DeviceModelLibrary.create().supported_models()

    # NOTE: in future may need to be more selective to only include mcintosh_*
    # that meet specific criteria...e.g. not all may be media players.
    # Alternatively since new physical models are not released often, this
    # could also be a static list of models! (PROBABLY BEST OPTION)
    filtered_models = [x for x in supported_models if x.startswith(prefix)]
    # filtered_models = ['mcintosh_mx160']
    return filtered_models


class McIntoshConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the McIntosh flow."""
        pass

    #    @staticmethod
    #    @callback
    #    def async_get_options_flow(config_entry):
    #        """Get the options flow for this handler."""
    #        return OptionsFlowHandler(config_entry)

    @staticmethod
    def config_schema(supported_models) -> vol.Schema:
        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=supported_models,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_URL, default=DEFAULT_URL
                ): cv.string  # this should NOT be cv.url
                # vol.Optional(CONF_BAUD_RATE): vol.In(BAUD_RATES),
            }
        )
        LOG.warning(f'Prepared {type(schema)} schema {schema}')
        return schema

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> FlowResult:
        """Handle the initial step of selecting model to configure."""
        errors: dict[str, str] = {}

        # NOTE: in future may need to be more selective to only include mcintosh_*
        # that meet specific criteria...e.g. not all may be media players.
        # Alternatively since new physical models are not released often, this
        # could also be a static list of models! (PROBABLY BEST OPTION)
        mcintosh_models = filter_models('mcintosh')
        LOG.warning(f'Starting McIntosh config flow: {mcintosh_models}')

        if user_input is not None:
            LOG.warning(f'Handling user input: {user_input}')

            model_id = user_input[CONF_MODEL]
            url = user_input.get(CONF_URL).strip()

            try:
                if model_id not in mcintosh_models:
                    raise UnsupportedDeviceError

                loop = asyncio.get_event_loop()
                config_overrides = get_connection_overrides(user_input)

                # connect to the device to confirm everything works
                client = await construct_async_client(
                    model_id, url, loop, connection_config=config_overrides
                )

                # make sure connection is alive and working to the device

                # Check connection and try to initialize it.
                try:
                    # await client.ping.ping()
                    pass
                except Exception as e:
                    raise ConfigEntryNotReady(
                        f'Connection failed to {model_id} @ {url}'
                    ) from e

                # await self.async_set_unique_id(client.serial)
                # self._abort_if_unique_id_configured()

            except ConnectionError as e:
                errors = ERROR_CANNOT_CONNECT
                LOG.warning(f'Failed config_flow: {errors}', e)
            except UnsupportedDeviceError as e:
                errors = ERROR_UNSUPPORTED
                LOG.warning(f'Failed config_flow: {errors}', e)
            else:
                return self.async_create_entry(title='McIntosh', data=user_input)

        LOG.warning(f'Displaying initial form')

        # no user input yet, so display the form
        schema = McIntoshConfigFlow.config_schema(mcintosh_models)
        LOG.warning(f'SCHEMA: {type(schema)} {schema}')
        return self.async_show_form(step_id='user', data_schema=schema, errors=errors)


class McIntoshOptionsFlow(OptionsFlow):
    """Handles options flow for the component after it has already been setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Manage the options for the custom component."""
        errors: dict[str, str] = {}
        supported_models = filter_models('mcintosh')

        if user_input is not None:
            # Validation and additional processing logic omitted for brevity.
            # ...
            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return self.async_create_entry(title='', data=user_input)

        LOG.warning('async_step_init()')

        return self.async_show_form(
            step_id='init',
            data_schema=McIntoshConfigFlow.config_schema(supported_models),
            errors=errors,
        )
