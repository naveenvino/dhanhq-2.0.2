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
    async def send(self, msg):
        self.sent.append(msg)
    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        await asyncio.sleep(0)
        return ''
    async def ping(self):
        pass
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
