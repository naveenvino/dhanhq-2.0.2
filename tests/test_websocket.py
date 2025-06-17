import json
import asyncio
import pytest
from dhanhq.marketfeed import DhanFeed
from dhanhq.orderupdate import OrderSocket

class DummyWebSocket:
    def __init__(self, messages=None):
        self.messages = list(messages or [])
        self.sent = []
        self.state = 1  # open
        self.closed = False
    async def send(self, msg):
        self.sent.append(msg)
    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        await asyncio.sleep(0)
        return ''
    async def ping(self):
        pass
    async def close(self):
        self.closed = True
    def __aiter__(self):
        return self
    async def __anext__(self):
        if self.messages:
            return self.messages.pop(0)
        raise StopAsyncIteration
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_dhanfeed_connect(monkeypatch):
    ws = DummyWebSocket()
    async def mock_connect(url):
        assert 'version=2' in url
        return ws
    monkeypatch.setattr('websockets.connect', mock_connect)
    called = False
    async def fake_subscribe(self):
        nonlocal called
        called = True
    monkeypatch.setattr(DhanFeed, 'subscribe_instruments', fake_subscribe)
    feed = DhanFeed('CID', 'TOKEN', [], version='v2')
    await feed.connect()
    assert feed.ws is ws
    assert called

@pytest.mark.asyncio
async def test_order_socket(monkeypatch):
    message = json.dumps({"Type": "order_alert", "Data": {"orderNo": "1", "status": "ok"}})
    ws = DummyWebSocket(messages=[message])
    def mock_connect(url):
        assert url == 'wss://api-order-update.dhan.co'
        return ws
    monkeypatch.setattr('websockets.connect', mock_connect)
    received = []
    async def fake_handle(self, data):
        received.append(data)
    monkeypatch.setattr(OrderSocket, 'handle_order_update', fake_handle)
    socket = OrderSocket('CID', 'TOKEN')
    await socket.connect_order_update()
    assert received and received[0]['Data']['orderNo'] == '1'
    assert ws.sent


@pytest.mark.asyncio
async def test_dhanfeed_disconnect(monkeypatch):
    ws = DummyWebSocket()
    feed = DhanFeed('CID', 'TOKEN', [], version='v2')
    feed.ws = ws
    monkeypatch.setattr(DhanFeed, 'create_header', lambda self, **kwargs: b'header')
    await feed.disconnect()
    assert ws.closed
    assert ws.sent[0] == '{"RequestCode": 12}'
    assert ws.sent[1] == b'header'
    assert feed.ws is None


@pytest.mark.asyncio
async def test_get_instrument_data(monkeypatch):
    ws = DummyWebSocket(messages=[b'data'])
    feed = DhanFeed('CID', 'TOKEN', [], version='v2')
    feed.ws = ws
    captured = []
    def fake_process(self, data):
        captured.append(data)
        return 'parsed'
    monkeypatch.setattr(DhanFeed, 'process_data', fake_process)
    result = await feed.get_instrument_data()
    assert result == 'parsed'
    assert captured[0] == b'data'


@pytest.mark.asyncio
async def test_handle_order_update_unknown(monkeypatch):
    socket = OrderSocket('CID', 'TOKEN')
    warnings = []
    monkeypatch.setattr('logging.warning', lambda msg, *a, **k: warnings.append(msg))
    await socket.handle_order_update({'Type': 'unknown'})
    assert warnings
