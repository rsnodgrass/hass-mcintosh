"""Config flow for easy setup"""
from __future__ import annotations

import logging
import asyncio
from typing import Any, TypedDict

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyavcontrol import DeviceModelLibrary
from pyavcontrol.const import BAUD_RATES
from pyavcontrol.helper import construct_async_client

from . import get_connection_overrides
from .const import CONF_BAUD_RATE, CONF_MODEL, DEFAULT_URL, DOMAIN

LOG = logging.getLogger(__name__)

ERROR_CANNOT_CONNECT = {'base': 'cannot_connect'}
ERROR_UNSUPPORTED = {'base': 'unsupported'}


class EntryData(TypedDict, total=False):
    """TypedDict for config_entry data."""

    host: str
    jid: str
    model: str
    name: str


class UnsupportedError(HomeAssistantError):
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

    #    @staticmethod
    #    @callback
    #    def async_get_options_flow(config_entry):
    #        """Get the options flow for this handler."""
    #        return OptionsFlowHandler(config_entry)

    @staticmethod
    def config_schema(supported_models):
        # FIXME: do we need to repopulate with existing config?
        #  e.g. default=self._config_entry.options.get(CONF_URL),
        return vol.Schema(
            {
                vol.Optional(CONF_NAME, default='McIntosh Audio'): cv.string,
                # vol.Required(CONF_MODEL): selector.SelectSelector(
                #    selector.SelectSelectorConfig(
                #        options=supported_models,
                #        mode=selector.SelectSelectorMode.DROPDOWN,
                #    )
                # ),
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
        mcintosh_models = filter_models('mcintosh')
        LOG.info(f'Starting McIntosh config flow: {mcintosh_models}')

        if user_input is not None:
            LOG.info(f'Handling user input: {user_input}')

            name = user_input.get(CONF_NAME).strip()
            model_id = user_input[CONF_MODEL]
            url = user_input.get(CONF_URL).strip()

            try:
                if model_id not in mcintosh_models:
                    raise UnsupportedError

                loop = asyncio.get_event_loop()
                config_overrides = get_connection_overrides(user_input)

                # connect to the device to confirm everything works
                client = await construct_async_client(
                    model_id, url, loop, connection_config=config_overrides
                )

                # make sure connection is alive and working to the device

                # Check connection and try to initialize it.
                try:
                    await client.ping.ping()
                except Exception as e:
                    raise ConfigEntryNotReady(
                        f'Unable to connect to {name} / {model_id} / {url}'
                    ) from e

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

        LOG.warning(f'async_step_init()')

        return self.async_show_form(
            step_id='init',
            data_schema=McIntoshConfigFlow.config_schema(supported_models),
            errors=errors,
        )
