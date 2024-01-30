"""Config flow for easy setup"""
from __future__ import annotations

import logging
import asyncio
from typing import Any

import voluptuous as vol
from homeassistant import config_entries

# from pyavcontrol.const import BAUD_RATES
from homeassistant.components.zha import BAUD_RATES
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyavcontrol import DeviceModelLibrary
from pyavcontrol.config import CONFIG
from pyavcontrol.helper import construct_async_client

from .const import CONF_BAUD_RATE, CONF_MODEL, DEFAULT_URL, DOMAIN

LOG = logging.getLogger(__name__)

ERROR_CANNOT_CONNECT = {'base': 'cannot_connect'}
ERROR_UNSUPPORTED = {'base': 'unsupported'}


class UnsupportedError(HomeAssistantError):
    """Error for unsupported device types."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Mcintosh."""

    VERSION = 1

    async def async_step_user(
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

        LOG.info(f'Starting McIntosh config flow: {mcintosh_models}')

        if user_input is not None:
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
                return self.async_create_entry(
                    title=f'McIntosh {name}',
                    data={
                        CONF_MODEL: model_id,
                        CONF_NAME: name,
                        CONF_URL: url,
                        CONF_BAUD_RATE: baud,
                    },
                )

        # no user input yet, so display the form
        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default='McIntosh Audio'): cv.string,
                    vol.Required(CONF_MODEL): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=mcintosh_models,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_URL, default=DEFAULT_URL): cv.url,
                    vol.Optional(CONF_BAUD_RATE): vol.In(BAUD_RATES),
                }
            ),
            errors=errors,
        )
