"""Platform to locally control Tuya-based cover devices - edited to handle orion garage door."""
import asyncio
import logging
import time
from functools import partial

import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_COMMANDS_SET,
    CONF_CURRENT_POSITION_DP,
    CONF_POSITION_INVERTED,
    CONF_POSITIONING_MODE,
    CONF_SET_POSITION_DP,
    CONF_SPAN_TIME,
)

_LOGGER = logging.getLogger(__name__)

COVER_ONOFF_CMDS = "on_off_stop"
COVER_OPENCLOSE_CMDS = "open_close"
COVER_OPENCLOSESTOP_CMDS = "open_close_stop"
COVER_FZZZ_CMDS = "fz_zz_stop"
COVER_12_CMDS = "1_2_3"
COVER_MODE_NONE = "none"
COVER_MODE_POSITION = "position"
COVER_MODE_TIMED = "timed"
COVER_TIMEOUT_TOLERANCE = 3.0

DEFAULT_COMMANDS_SET = COVER_ONOFF_CMDS
DEFAULT_POSITIONING_MODE = COVER_MODE_NONE
DEFAULT_SPAN_TIME = 25.0


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_COMMANDS_SET): vol.In(
            [COVER_ONOFF_CMDS, COVER_OPENCLOSE_CMDS, COVER_OPENCLOSESTOP_CMDS, COVER_FZZZ_CMDS, COVER_12_CMDS]
        ),
        vol.Optional(CONF_POSITIONING_MODE, default=DEFAULT_POSITIONING_MODE): vol.In(
            [COVER_MODE_NONE, COVER_MODE_POSITION, COVER_MODE_TIMED]
        ),
        vol.Optional(CONF_CURRENT_POSITION_DP): vol.In(dps),
        vol.Optional(CONF_SET_POSITION_DP): vol.In(dps),
        vol.Optional(CONF_POSITION_INVERTED, default=False): bool,
        vol.Optional(CONF_SPAN_TIME, default=DEFAULT_SPAN_TIME): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=300.0)
        ),
    }


class TuyaLocalCover(LocalTuyaEntity, CoverEntity):
    """Tuya garage door device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaCover."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        commands_set = DEFAULT_COMMANDS_SET
        if self.has_config(CONF_COMMANDS_SET):
            commands_set = self._config[CONF_COMMANDS_SET]
        self._open_cmd = commands_set.split("_")[0]
        self._close_cmd = commands_set.split("_")[1]
        self._stop_cmd = ""
        if len(commands_set.split("_")) > 2:
            self._stop_cmd = commands_set.split("_")[2]
        
        # hard coded for orion garage door
        self._control_dp_id = 1 # False=close, True=open
        self._action_dp_id  = 3 # False=closed, True=opened

        self._timer_start = time.time()
        self._state = self._stop_cmd
        self._previous_state = self._state
        self._current_cover_position = 0
        _LOGGER.debug("Initialized garage door [%s]", self.name)

    @property
    def supported_features(self):
        """Flag supported features."""
        supported = SUPPORT_OPEN | SUPPORT_CLOSE
        if self._stop_cmd != "":
            supported |= SUPPORT_STOP
        if self._config[CONF_POSITIONING_MODE] != COVER_MODE_NONE:
            supported |= SUPPORT_SET_POSITION
        return supported

    @property
    def _current_state(self):
        """Return the current state of the cover if it can be determined,
        or None if it is inconclusive.
        """
        if self._action_dp_id:
            state_flag = self.dps(self._action_dp_id)
            state = self._state_flag_to_str(state_flag)
            if state in ["opening", "closing", "opened", "closed"]:
                return state
        return None

    def _state_to_percent(self, state):
        """Convert a state to percent open"""
        if state == "opened":
            return 100
        elif state == "closed":
            return 0
        else:
            return 50

    def _state_flag_to_str(self, f):
        if f:
            return "opened"
        else:
            return "closed"

    @property
    def current_cover_position(self):
        """Return current cover position in percent."""
        if self._action_dp_id:
            state_flag = self.dps(self._action_dp_id)
            state = self._state_flag_to_str(state_flag)
            return self._state_to_percent(state)
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_NONE:
            return None
        return self._current_cover_position

    @property
    def is_opening(self):
        """Return if cover is opening."""
        state = self._current_state
        if state is None:
            # If we return false, and is_closing and is_opening are also false,
            # HA assumes open.  If we don't know, return None.
            return None
        else:
            return state == "opening"

    @property
    def is_closing(self):
        """Return if cover is closing."""
        state = self._current_state
        if state is None:
            # If we return false, and is_closing and is_opening are also false,
            # HA assumes open.  If we don't know, return None.
            return None
        else:
            return state == "closing"

    @property
    def is_closed(self):
        """Return if the cover is closed or not, if it can be determined."""
        state = self._current_state
        if state is None:
            # If we return false, and is_closing and is_opening are also false,
            # HA assumes open.  If we don't know, return None.
            return None
        else:
            return state == "closed"

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        self.debug("Setting cover position: %r", kwargs[ATTR_POSITION])
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            newpos = float(kwargs[ATTR_POSITION])

            currpos = self.current_cover_position
            posdiff = abs(newpos - currpos)
            mydelay = posdiff / 100.0 * self._config[CONF_SPAN_TIME]
            if newpos > currpos:
                self.debug("Opening to %f: delay %f", newpos, mydelay)
                await self.async_open_cover()
            else:
                self.debug("Closing to %f: delay %f", newpos, mydelay)
                await self.async_close_cover()
            self.hass.async_create_task(self.async_stop_after_timeout(mydelay))
            self.debug("Done")

        elif self._config[CONF_POSITIONING_MODE] == COVER_MODE_POSITION:
            converted_position = int(kwargs[ATTR_POSITION])
            if self._config[CONF_POSITION_INVERTED]:
                converted_position = 100 - converted_position

            if 0 <= converted_position <= 100 and self.has_config(CONF_SET_POSITION_DP):
                await self._device.set_dp(
                    converted_position, self._config[CONF_SET_POSITION_DP]
                )

    async def async_stop_after_timeout(self, delay_sec):
        """Stop the cover if timeout (max movement span) occurred."""
        await asyncio.sleep(delay_sec)
        await self.async_stop_cover()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if self._control_dp_id is not None:
            await self._device.set_dp(True, self._control_dp_id)
            return
        self.debug("Launching command %s to cover ", self._open_cmd)
        await self._device.set_dp(self._open_cmd, self._dp_id)
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            # for timed positioning, stop the cover after a full opening timespan
            # instead of waiting the internal timeout
            self.hass.async_create_task(
                self.async_stop_after_timeout(
                    self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
                )
            )

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        if self._control_dp_id is not None:
            await self._device.set_dp(False, self._control_dp_id)
            return
        self.debug("Launching command %s to cover ", self._close_cmd)
        await self._device.set_dp(self._close_cmd, self._dp_id)
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            # for timed positioning, stop the cover after a full opening timespan
            # instead of waiting the internal timeout
            self.hass.async_create_task(
                self.async_stop_after_timeout(
                    self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
                )
            )

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.debug("Launching command %s to cover ", self._stop_cmd)
        await self._device.set_dp(self._stop_cmd, self._dp_id)


    def status_restored(self, stored_state):
        """Restore the last stored cover status."""
        return
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            stored_pos = stored_state.attributes.get("current_position")
            if stored_pos is not None:
                self._current_cover_position = stored_pos
                self.debug("Restored cover position %s", self._current_cover_position)

    def status_updated(self):
        """Device status was updated."""
        return
        self._previous_state = self._state
        # False=closed, True=open
        self._state = self._open_cmd if self.dps(self._action_dp_id) else self._close_cmd
        if self._state.isupper():
            self._open_cmd = self._open_cmd.upper()
            self._close_cmd = self._close_cmd.upper()
            self._stop_cmd = self._stop_cmd.upper()

        if self.has_config(CONF_CURRENT_POSITION_DP):
            curr_pos = self.dps_conf(CONF_CURRENT_POSITION_DP)
            if self._config[CONF_POSITION_INVERTED]:
                self._current_cover_position = 100 - curr_pos
            else:
                self._current_cover_position = curr_pos
        if (
            self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED
            and self._state != self._previous_state
        ):
            if self._previous_state != self._stop_cmd:
                # the state has changed, and the cover was moving
                time_diff = time.time() - self._timer_start
                pos_diff = round(time_diff / self._config[CONF_SPAN_TIME] * 100.0)
                if self._previous_state == self._close_cmd:
                    pos_diff = -pos_diff
                self._current_cover_position = min(
                    100, max(0, self._current_cover_position + pos_diff)
                )

                change = "stopped" if self._state == self._stop_cmd else "inverted"
                self.debug(
                    "Movement %s after %s sec., position difference %s",
                    change,
                    time_diff,
                    pos_diff,
                )

            # store the time of the last movement change
            self._timer_start = time.time()

        # Keep record in last_state as long as not during connection/re-connection,
        # as last state will be used to restore the previous state
        if (self._state is not None) and (not self._device.is_connecting):
            self._last_state = self._state


async_setup_entry = partial(async_setup_entry, DOMAIN, TuyaLocalCover, flow_schema)
