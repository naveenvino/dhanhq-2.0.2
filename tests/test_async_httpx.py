import json
import pytest

from dhanhq.async_httpx import AsyncDhanhq


class DummyResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def json(self):
        return self._data


class DummySession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return DummyResponse(self.responses.pop(0))

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return DummyResponse(self.responses.pop(0))

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_async_httpx_place_order():
    session = DummySession([{"order_id": "1"}])
    api = AsyncDhanhq("CID", "TOKEN", session=session)
    resp = await api.place_order(
        security_id="123",
        exchange_segment=api.NSE,
        transaction_type=api.BUY,
        quantity=1,
        order_type=api.MARKET,
        product_type=api.INTRA,
        price=0,
    )
    assert resp["status"] == "success"
    body = json.loads(session.calls[0][2]["data"])
    assert body["dhanClientId"] == "CID"


@pytest.mark.asyncio
async def test_async_httpx_get_positions():
    session = DummySession([{"positions": []}])
    api = AsyncDhanhq("CID", "TOKEN", session=session)
    resp = await api.get_positions()
    assert resp["data"] == {"positions": []}
    assert session.calls[0][0] == "GET"
