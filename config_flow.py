"""Config flow et Options flow avec Bot Token."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

DOMAIN = "knx_telegram_notifier"

CONF_NAME = "name"
CONF_GROUP_ADDRESSES = "group_addresses"
CONF_BOT_TOKEN = "bot_token"
CONF_CHAT_ID = "chat_id"
CONF_PAYLOAD_TRIGGER = "payload_trigger"
CONF_MESSAGE = "message"


class KnxTelegramConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
  """Flux de configuration initial."""

  VERSION = 1

  async def async_step_user(self, user_input=None):
    if user_input is not None:
      return self.async_create_entry(
          title=user_input[CONF_NAME], data=user_input
      )

    schema = vol.Schema({
        vol.Required(CONF_NAME, default="Notifier KNX"): str,
        vol.Required(CONF_GROUP_ADDRESSES, default="1/2/10"): str,
        vol.Optional(CONF_BOT_TOKEN, default=""): str,
        vol.Required(CONF_CHAT_ID): str,
        vol.Optional(CONF_PAYLOAD_TRIGGER, default=1): int,
        vol.Optional(
            CONF_MESSAGE, default="🚨 Alarme KNX reçue sur {address}"
        ): str,
    })
    return self.async_show_form(step_id="user", data_schema=schema)

  @staticmethod
  @callback
  def async_get_options_flow(config_entry):
    return KnxTelegramOptionsFlowHandler(config_entry)


class KnxTelegramOptionsFlowHandler(config_entries.OptionsFlow):
  """Options flow pour reconfigurer sans redémarrage."""

  def __init__(self, config_entry):
    self.config_entry = config_entry

  async def async_step_init(self, user_input=None):
    if user_input is not None:
      return self.async_create_entry(title="", data=user_input)

    opts = {**self.config_entry.data, **self.config_entry.options}

    schema = vol.Schema({
        vol.Required(
            CONF_GROUP_ADDRESSES,
            default=opts.get(CONF_GROUP_ADDRESSES, ""),
        ): str,
        vol.Optional(
            CONF_BOT_TOKEN,
            default=opts.get(CONF_BOT_TOKEN, ""),
        ): str,
        vol.Required(
            CONF_CHAT_ID, default=opts.get(CONF_CHAT_ID, "")
        ): str,
        vol.Optional(
            CONF_PAYLOAD_TRIGGER,
            default=opts.get(CONF_PAYLOAD_TRIGGER, 1),
        ): int,
        vol.Optional(
            CONF_MESSAGE,
            default=opts.get(
                CONF_MESSAGE, "🚨 Alarme KNX reçue sur {address}"
            ),
        ): str,
    })
    return self.async_show_form(step_id="init", data_schema=schema)