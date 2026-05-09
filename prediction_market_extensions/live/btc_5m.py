from __future__ import annotations

from datetime import UTC, datetime
import os
import time
from typing import Sequence

from nautilus_trader.adapters.polymarket.providers import PolymarketDataLoader
from nautilus_trader.core.nautilus_pyo3 import HttpClient
from nautilus_trader.model.identifiers import InstrumentId

WINDOW_SECONDS = 300
DEFAULT_MARKET_COUNT = 36
LIVE_BTC_5M_EVENT_SLUGS_ENV = "LIVE_BTC_5M_EVENT_SLUGS"
LIVE_BTC_5M_MARKET_COUNT_ENV = "LIVE_BTC_5M_MARKET_COUNT"
LIVE_BTC_5M_INCLUDE_CURRENT_ENV = "LIVE_INCLUDE_CURRENT_MARKET"


def floor_to_btc_5m_start(timestamp: int | None = None) -> int:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    return ts - (ts % WINDOW_SECONDS)


def btc_5m_market_slug(market_start_ts: int) -> str:
    return f"btc-updown-5m-{int(market_start_ts)}"


def upcoming_btc_5m_event_slugs(
    *,
    market_count: int = DEFAULT_MARKET_COUNT,
    include_current: bool = True,
    timestamp: int | None = None,
) -> list[str]:
    start = floor_to_btc_5m_start(timestamp)
    if not include_current:
        start += WINDOW_SECONDS
    return [btc_5m_market_slug(start + (index * WINDOW_SECONDS)) for index in range(market_count)]


def configured_btc_5m_event_slugs() -> list[str]:
    raw = os.getenv(LIVE_BTC_5M_EVENT_SLUGS_ENV, "")
    slugs = [slug.strip() for slug in raw.split(",") if slug.strip()]
    if slugs:
        return slugs
    include_current = os.getenv(LIVE_BTC_5M_INCLUDE_CURRENT_ENV, "1").lower() in {
        "1",
        "true",
        "yes",
    }
    return upcoming_btc_5m_event_slugs(
        market_count=int(os.getenv(LIVE_BTC_5M_MARKET_COUNT_ENV, str(DEFAULT_MARKET_COUNT))),
        include_current=include_current,
    )


def upcoming_btc_5m_window_label(*, timestamp: int | None = None) -> str:
    start = floor_to_btc_5m_start(timestamp)
    end = start + WINDOW_SECONDS
    start_label = datetime.fromtimestamp(start, UTC).isoformat()
    end_label = datetime.fromtimestamp(end, UTC).isoformat()
    return f"{start_label} -> {end_label}"


async def load_btc_5m_instrument_ids(
    *,
    market_count: int = DEFAULT_MARKET_COUNT,
    include_current: bool = True,
    event_slugs: Sequence[str] | None = None,
    http_client: HttpClient | None = None,
) -> tuple[InstrumentId, ...]:
    client = http_client or HttpClient(timeout_secs=15)
    instrument_ids: list[InstrumentId] = []
    slugs = (
        list(event_slugs)
        if event_slugs is not None
        else upcoming_btc_5m_event_slugs(
            market_count=market_count,
            include_current=include_current,
        )
    )
    for slug in slugs:
        for token_index in (0, 1):
            loader = await PolymarketDataLoader.from_market_slug(
                slug,
                token_index=token_index,
                http_client=client,
            )
            instrument_ids.append(loader.instrument.id)
    return tuple(instrument_ids)
