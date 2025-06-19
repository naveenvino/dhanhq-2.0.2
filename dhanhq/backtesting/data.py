"""Helpers for loading historical candle data using :class:`dhqnhq.dhanhq`."""

from __future__ import annotations

from typing import List, Dict
from dhanhq.dhanhq import dhanhq


def load_intraday_data(api: dhanhq, **kwargs) -> List[Dict]:
    """Load intraday candles via the REST API."""
    resp = api.intraday_minute_data(**kwargs)
    if resp.get("status") == "success":
        return resp.get("data", [])
    return []


def load_daily_data(api: dhanhq, **kwargs) -> List[Dict]:
    """Load daily candles via the REST API."""
    resp = api.historical_daily_data(**kwargs)
    if resp.get("status") == "success":
        return resp.get("data", [])
    return []
