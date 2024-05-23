"""Config flow for easy setup"""

from __future__ import annotations

import logging
import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyavcontrol import DeviceModelLibrary
from pyavcontrol.const import BAUD_RATES
from pyavcontrol.helper import construct_async_client
from pyavcontrol.library import filter_models_by_regex

from . import get_connection_overrides
from .const import CONF_BAUD_RATE, CONF_MODEL, DEFAULT_URL, DOMAIN

LOG = logging.getLogger(__name__)

ERROR_CANNOT_CONNECT = {'base': 'cannot_connect'}
ERROR_UNSUPPORTED = {'base': 'unsupported'}


class UnsupportedDeviceError(HomeAssistantError):
    """Error for unsupported device types."""


class McIntoshConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the McIntosh config flow."""
        pass

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return McIntoshOptionsFlow(config_entry)

    @staticmethod
    def step_user_schema(supported_models) -> vol.Schema:
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
                ): cv.string,  # this should NOT be cv.url (since also can be a path)
                vol.Optional(CONF_BAUD_RATE): vol.In(BAUD_RATES),
            }
        )
        # LOG.debug(f'Prepared {type(schema)} schema {schema}')
        return schema

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> FlowResult:
        """Handle the initial step of selecting model to configure."""
        errors: dict[str, str] = {}

        if user_input is not None:
            LOG.info(f'Config flow user input: {user_input}')

            model_id = user_input[CONF_MODEL]
            url = user_input.get(CONF_URL).strip()

            try:
                loop = asyncio.get_event_loop()
                config_overrides = get_connection_overrides(user_input)

                # connect to the device to confirm everything works
                client = await construct_async_client(
                    model_id, url, loop, connection_config=config_overrides
                ).is_connected()

                # unique_id is client serial, if available, otherwise the url + model
                unique_id = f'{model_id}_{url}'
                if hasattr(client, 'serial'):
                    try:
                        unique_id = await client.serial()
                    except Exception:
                        LOG.info(
                            f'Failed getting serial number, defaulting unique_id to {unique_id}'
                        )

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

            except ConnectionError as e:
                errors = ERROR_CANNOT_CONNECT
                LOG.warning(f'Failed config_flow: {errors}', e)
            except UnsupportedDeviceError as e:
                errors = ERROR_UNSUPPORTED
                LOG.warning(f'Failed config_flow: {errors}', e)
            else:
                return self.async_create_entry(title='McIntosh', data=user_input)

        # no user input yet, display the initial configuration form
        supported_models = DeviceModelLibrary.create().supported_models()

        # NOTE: in future may need to be more selective to only include devices
        # that meet specific criteria...e.g. not all may be media players.
        #
        # Alternatively since new physical models are not released often, this
        # could also be a static list of models.
        mcintosh_models = filter_models_by_regex(supported_models, 'mcintosh')
        LOG.debug('Starting McIntosh config flow: %s', mcintosh_models)

        schema = McIntoshConfigFlow.step_user_schema(mcintosh_models)
        return self.async_show_form(step_id='user', data_schema=schema, errors=errors)


# FIXME: add "sources" config panel (as options flow and initial setup)


class McIntoshOptionsFlow(OptionsFlow):
    """Handles options flow for the component after it has already been setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    @staticmethod
    def step_options_schema(model_def: dict) -> vol.Schema:
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL, default=DEFAULT_URL
                ): cv.string,  # this should NOT be cv.url (since also can be a path)
                vol.Optional(CONF_BAUD_RATE): vol.In(BAUD_RATES),
            }
        )
        # LOG.debug(f'Prepared {type(schema)} schema {schema}')
        return schema

    async def async_step_options(
        self, user_input: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Manage the options for the custom component."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validation and additional processing logic omitted for brevity.
            # ...
            if not errors:
                # Value of data will be set on the options property of our config_entry instance.
                return self.async_create_entry(title='', data=user_input)

        model = DeviceModelLibrary.create().load_model(CONF_MODEL)
        schema = McIntoshConfigFlow.step_user_schema(model)
        return self.async_show_form(step_id='init', data_schema=schema, errors=errors)
