"""Compatibility facade for travel runtime helpers.

Keep tool modules independent of helper placement while the implementation stays
split into focused files small enough to inspect in one context window.
"""
import asyncio
from urllib.parse import urlencode

from ..nearby import search_nearby as _search_nearby
from ..railways import (search_trains as _search_trains,
                        station_suggestions as _station_suggestions)
from ..tbank_urls import (afisha_event_url as _afisha_event_url,
                          hotel_details_url as _hotel_details_url,
                          safe_tbank_url as _safe_tbank_url,
                          with_leading_tbank_url as _with_leading_tbank_url)
from ..weather import weather_report as _weather_report
from . import session as _session_module
from . import response as _response_module
from . import comparison_support as _comparison_module
from . import hotel_support as _hotel_module

for _module in (_session_module, _response_module, _comparison_module, _hotel_module):
    globals().update({
        name: getattr(_module, name)
        for name in dir(_module)
        if not name.startswith("__")
    })
