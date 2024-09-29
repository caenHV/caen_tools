"""MaxCurrentsMap describes a total schema 
of the `max_currents_map.json` config
"""

from typing import TypedDict


class ChannelRestrictions(TypedDict):
    volt_change: float
    steady: float


class ChannelsCurrents(TypedDict):
    channel_alias: str
    parameters: ChannelRestrictions


class MaxCurrentsMap(TypedDict):
    max_current: ChannelsCurrents
