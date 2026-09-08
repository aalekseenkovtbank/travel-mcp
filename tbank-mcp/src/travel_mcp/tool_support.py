"""Internal namespace shared by travel tool modules.

The extracted tool bodies intentionally retain their original names. This module
is the single compatibility seam that maps those names to focused implementations
in runtime, travel_compare, renderer and source adapters. ``__all__`` explicitly
allows private helper names because they are internal to this package, not public
MCP tools.
"""
from __future__ import annotations

from .. import nearby as _nearby_module
from .. import railways as _railways_module
from .. import tbank_urls as _tbank_urls_module
from .. import travel_compare as _travel_compare_module
from .. import trip_page as _trip_page_module
from .. import trip_personalization as _trip_personalization_module
from .. import weather as _weather_module
from . import runtime as _runtime_module

_SOURCE_MODULES = (
    _runtime_module,
    _travel_compare_module,
    _tbank_urls_module,
    _trip_page_module,
    _trip_personalization_module,
    _nearby_module,
    _weather_module,
    _railways_module,
)

for _source_module in _SOURCE_MODULES:
    globals().update({
        name: getattr(_source_module, name)
        for name in dir(_source_module)
        if not name.startswith("__")
    })

__all__ = ('ComparisonError',
 'ComparisonFailure',
 'Decimal',
 'FlightComparisonData',
 'FlightComparisonItem',
 'FlightComparisonResponse',
 'FlightHotelComparisonData',
 'FlightHotelComparisonItem',
 'FlightHotelComparisonResponse',
 'HotelComparisonData',
 'HotelComparisonItem',
 'HotelComparisonResponse',
 'Literal',
 'ObservedGroup',
 'Path',
 'RenderPageResult',
 'RenderTravelPageResult',
 'RenderTripPageResult',
 'StayWindow',
 'TbankApiError',
 'TrainComparisonData',
 'TrainComparisonItem',
 'TrainComparisonResponse',
 'TravelPageDocument',
 'TripPageDocumentV1',
 'TripPersonalizationProfile',
 '_VENUE_AFISHA_HINT',
 '_VENUE_CINEMA_HINT',
 '_afisha_event_url',
 '_checked_at',
 '_comparison_dates',
 '_comparison_limit',
 '_comparison_meta',
 '_comparison_status',
 '_comparison_warnings',
 '_comparison_windows',
 '_cut',
 '_eligible_flights',
 '_eligible_hotels',
 '_err',
 '_failure',
 '_flat',
 '_flight_inventory_call',
 '_flight_passengers',
 '_formatted_error',
 '_hotel_address',
 '_hotel_amount',
 '_hotel_children',
 '_hotel_coordinates',
 '_hotel_date',
 '_hotel_details_url',
 '_hotel_guests',
 '_hotel_id',
 '_hotel_image_urls',
 '_hotel_inventory_call',
 '_hotel_map_frame',
 '_hotel_positive_ids',
 '_hotel_rate_filters',
 '_hotel_review_item',
 '_hotel_search_filters_input',
 '_hotel_search_guests',
 '_hotel_search_window',
 '_https_image_url',
 '_json_envelope',
 '_json_out',
 '_public_session',
 '_require',
 '_response_format',
 '_rows_out',
 '_safe_tbank_url',
 '_search_nearby',
 '_search_trains',
 '_station_suggestions',
 '_train_inventory_call',
 '_weather_report',
 '_window_value',
 '_with_leading_tbank_url',
 'asyncio',
 'build_personalization_profile',
 'comparison_groups',
 'date',
 'datetime',
 'format_inventory_reply_json',
 'normalize_flight_inventory',
 'normalize_hotel_inventory',
 'normalize_train_inventory',
 'os',
 'price_delta',
 're',
 'render_page_content',
 'render_travel_page_files',
 'render_trip_page_files',
 'rub_number',
 'sort_flights',
 'sort_hotels',
 'sort_trains',
 'timedelta',
 'urlencode')
