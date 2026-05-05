"""Config flow for GoodWe SEMS+ integration."""

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .api import SemsPlusAuthError, SemsPlusClient
from .const import CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class GoodWeSemsPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoodWe SEMS+."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow."""
        return GoodWeSemsPlusOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        _LOGGER.debug("Config flow user step started")
        errors = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            _LOGGER.debug("Validating credentials for: %s", email)
            password = user_input[CONF_PASSWORD]

            # Validate credentials
            client = SemsPlusClient(email, password)
            try:
                _LOGGER.debug("Attempting to authenticate with credentials")
                await self.hass.async_add_executor_job(client.get_user)
                _LOGGER.debug("Credentials validated successfully")
            except SemsPlusAuthError as err:
                _LOGGER.warning("Authentication failed during config: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during config: %s", err)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()
                _LOGGER.info("Config entry created for: %s", email)
                return self.async_create_entry(
                    title=f"SEMS+ ({email})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class GoodWeSemsPlusOptionsFlow(OptionsFlow):
    """Handle options for GoodWe SEMS+."""

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle options step."""
        _LOGGER.debug("Options flow init step started")
        if user_input is not None:
            _LOGGER.debug("Saving options: %s", user_input)
            return self.async_abort_entry_configured()

        current_delay = self.config_entry.options.get(
            CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY
        )
        _LOGGER.debug("Current command delay setting: %d seconds", current_delay)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_COMMAND_DELAY,
                    default=current_delay,
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle options step with user input."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return await self.async_step_init()
