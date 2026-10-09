"""Intégration sur-mesure KNX vers Telegram avec verrouillage sur alarme active."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "knx_telegram_notifier"
PLATFORMS = ["switch", "binary_sensor", "button"]


class KnxNotifierData:
  """Gestionnaire central d'état de l'instance."""

  def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
    self.hass = hass
    self.entry = entry
    self.active = True
    self.in_alarm = False
    self.remove_listener = None
    self.entities = []
    _LOGGER.info(
        "Initialisation de KnxNotifierData pour '%s' (ID: %s)",
        entry.title,
        entry.entry_id,
    )

  def update_config(self):
    """Met à jour la configuration depuis les données de l'instance."""
    config = {**self.entry.data, **self.entry.options}
    raw_addrs = config.get("group_addresses", "")
    self.addresses = [a.strip() for a in raw_addrs.split(",") if a]
    self.bot_token = config.get("bot_token", "").strip()
    self.chat_id = str(config.get("chat_id", "")).strip()
    self.payload = config.get("payload_trigger", 1)
    self.message = config.get("message", "🚨 Alarme KNX reçue sur {address}")

    _LOGGER.info(
        "[%s] Configuration mise à jour - Adresses: %s | Trigger Payload: %s | Chat ID: %s | Token présent: %s",
        self.entry.title,
        self.addresses,
        self.payload,
        self.chat_id,
        bool(self.bot_token),
    )

  def _is_payload_matching(self, raw_value) -> bool:
    """Compare la valeur reçue du bus KNX avec le déclencheur configuré."""
    if isinstance(raw_value, tuple) and len(raw_value) > 0:
      raw_value = raw_value[0]

    if isinstance(raw_value, bool):
      raw_value = 1 if raw_value else 0

    try:
      return int(raw_value) == int(self.payload)
    except (ValueError, TypeError):
      return str(raw_value) == str(self.payload)

  async def _send_telegram_message(self, message_text: str):
    """Envoie un message Telegram directement via l'API HTTPS."""
    if not self.bot_token:
      _LOGGER.error(
          "[%s] Échec de l'envoi : Aucun Bot Token Telegram n'a été configuré.",
          self.entry.title,
      )
      return

    if not self.chat_id:
      _LOGGER.error(
          "[%s] Échec de l'envoi : Aucun Chat ID n'a été configuré.",
          self.entry.title,
      )
      return

    session = async_get_clientsession(self.hass)
    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    payload = {
        "chat_id": self.chat_id,
        "text": message_text,
    }

    _LOGGER.debug(
        "[%s] Envoi de la requête HTTP vers Telegram (Chat ID: %s)...",
        self.entry.title,
        self.chat_id,
    )

    try:
      async with session.post(url, json=payload, timeout=10) as response:
        if response.status == 200:
          _LOGGER.info(
              "[%s] Message Telegram envoyé avec succès !", self.entry.title
          )
        else:
          response_body = await response.text()
          _LOGGER.error(
              "[%s] Rejet Telegram (HTTP %s) : %s",
              self.entry.title,
              response.status,
              response_body,
          )
    except Exception as err:
      _LOGGER.error(
          "[%s] Exception lors de la connexion à l'API Telegram : %s",
          self.entry.title,
          err,
      )

  def register_knx(self):
    """S'inscrit à l'écoute des événements du bus KNX."""
    if self.remove_listener:
      _LOGGER.debug(
          "[%s] Désinscription de l'ancien listener KNX.", self.entry.title
      )
      self.remove_listener()

    @callback
    def knx_event_callback(event):
      destination = event.data.get("destination") or event.data.get(
          "destination_address"
      )

      # Extraction de la valeur (data, value ou payload)
      value = (
          event.data.get("data")
          if "data" in event.data
          else event.data.get("value")
      )
      if value is None:
        value = event.data.get("payload")

      _LOGGER.debug(
          "[%s] Événement KNX détecté -> Adresse: %s | Valeur brute: %s (%s)",
          self.entry.title,
          destination,
          value,
          type(value).__name__,
      )

      if not self.active:
        _LOGGER.debug(
            "[%s] Ignoré : la surveillance est désactivée.", self.entry.title
        )
        return

      if destination in self.addresses:
        _LOGGER.info(
            "[%s] Adresse KNX '%s' correspondante identifiée !",
            self.entry.title,
            destination,
        )

        if self._is_payload_matching(value):
          # --- NOUVELLE VÉRIFICATION : Verrouillage si alarme déjà active ---
          if self.in_alarm:
            _LOGGER.info(
                "[%s] Événement ignoré : l'alarme est déjà active. En attente du Reset.",
                self.entry.title,
            )
            return

          _LOGGER.warning(
              "🚨 [%s] Alarme déclenchée par l'adresse %s (Payload: %s)",
              self.entry.title,
              destination,
              value,
          )

          self.in_alarm = True
          self.notify_entities()

          formatted_msg = self.message.format(
              name=self.entry.title, address=destination, value=value
          )

          self.hass.async_create_task(
              self._send_telegram_message(formatted_msg)
          )
        else:
          _LOGGER.debug(
              "[%s] Valeur reçue (%s) différente du déclencheur configuré (%s).",
              self.entry.title,
              value,
              self.payload,
          )

    self.remove_listener = self.hass.bus.async_listen(
        "knx_event", knx_event_callback
    )
    _LOGGER.info(
        "[%s] Écouteur KNX activé sur le bus d'événements HA.", self.entry.title
    )

  def reset_alarm(self):
    """Réinitialise l'état d'alarme et autorise les nouvelles notifications."""
    _LOGGER.info(
        "[%s] Réinitialisation de l'état d'alarme (Reset).", self.entry.title
    )
    self.in_alarm = False
    self.notify_entities()

  def set_active(self, state: bool):
    """Active ou désactive la surveillance."""
    _LOGGER.info(
        "[%s] Modification de l'état d'activation -> %s", self.entry.title, state
    )
    self.active = state
    self.notify_entities()

  def notify_entities(self):
    """Met à jour l'affichage des entités associées dans Home Assistant."""
    for entity in self.entities:
      if entity.hass:
        entity.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  """Initialisation d'une instance de l'intégration."""
  _LOGGER.info("[%s] Chargement de l'intégration...", entry.title)
  hass.data.setdefault(DOMAIN, {})

  data_handler = KnxNotifierData(hass, entry)
  data_handler.update_config()
  data_handler.register_knx()

  hass.data[DOMAIN][entry.entry_id] = data_handler

  await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
  entry.async_on_unload(entry.add_update_listener(update_listener))
  return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
  """Rappels lors d'une modification des options dans l'interface UI."""
  _LOGGER.info(
      "[%s] Mise à jour des options reçue. Reconfiguration à chaud...",
      entry.title,
  )
  data_handler = hass.data[DOMAIN][entry.entry_id]
  data_handler.update_config()
  data_handler.register_knx()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  """Déchargement propre de l'intégration."""
  _LOGGER.info("[%s] Déchargement en cours...", entry.title)
  unload_ok = await hass.config_entries.async_unload_platforms(
      entry, PLATFORMS
  )
  if unload_ok:
    data_handler = hass.data[DOMAIN].pop(entry.entry_id)
    if data_handler.remove_listener:
      data_handler.remove_listener()
  return unload_ok