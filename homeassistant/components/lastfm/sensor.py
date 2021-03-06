"""Sensor for Last.fm account status."""
import logging
import re

import pylast as lastfm
from pylast import WSError
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_API_KEY
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

_LOGGER = logging.getLogger(__name__)

ATTR_LAST_PLAYED = "last_played"
ATTR_PLAY_COUNT = "play_count"
ATTR_TOP_PLAYED = "top_played"
ATTRIBUTION = "Data provided by Last.fm"

STATE_NOT_SCROBBLING = "Not Scrobbling"

CONF_USERS = "users"

ENTITY_ID_FORMAT = "sensor.lastfm_{}"

ICON = "mdi:lastfm"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_USERS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


def setup_platform(
    hass: HomeAssistantType, config: ConfigType, add_entities, discovery_info=None
):
    """Set up the Last.fm sensor platform."""
    api_key = config[CONF_API_KEY]
    users = config.get(CONF_USERS)

    lastfm_api = lastfm.LastFMNetwork(api_key=api_key)

    entities = []
    for username in users:
        try:
            lastfm_api.get_user(username).get_image()
            entities.append(LastfmSensor(hass, username, lastfm_api))
        except WSError as error:
            _LOGGER.error(error)
            return

    add_entities(entities, True)


class LastfmSensor(Entity):
    """A class for the Last.fm account."""

    def __init__(self, hass: HomeAssistantType, user, lastfm_api):
        """Initialize the sensor."""
        self._user = lastfm_api.get_user(user)
        self._name = user
        self._lastfm = lastfm_api
        self._state = STATE_NOT_SCROBBLING
        self._playcount = None
        self._lastplayed = None
        self._topplayed = None
        self._cover = None

        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, user, hass=hass)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Update device state."""
        self._cover = self._user.get_image()
        self._playcount = self._user.get_playcount()
        last = self._user.get_recent_tracks(limit=2)[0]
        self._lastplayed = f"{last.track.artist} - {last.track.title}"
        top = self._user.get_top_tracks(limit=1)[0]
        toptitle = re.search("', '(.+?)',", str(top))
        topartist = re.search("'(.+?)',", str(top))
        self._topplayed = "{} - {}".format(topartist.group(1), toptitle.group(1))
        now = self._user.get_now_playing()
        if now is None:
            self._state = STATE_NOT_SCROBBLING
            return
        self._state = f"{now.artist} - {now.title}"

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_LAST_PLAYED: self._lastplayed,
            ATTR_PLAY_COUNT: self._playcount,
            ATTR_TOP_PLAYED: self._topplayed,
        }

    @property
    def entity_picture(self):
        """Avatar of the user."""
        return self._cover

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON
