import json
import io
import os
import asyncio
import responses
import pytest
from dhanhq.dhanhq import dhanhq
from dhanhq.marketfeed import DhanFeed


class DummyWS:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send(self, msg):
        self.sent.append(msg)


@responses.activate
def test_get_order_by_id_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/orders/1'
    responses.add(responses.GET, url, json={'id': '1'}, status=200)
    resp = api.get_order_by_id('1')
    assert resp['status'] == 'success'
    assert resp['data'] == {'id': '1'}


@responses.activate
def test_get_order_by_id_error():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/orders/1'
    responses.add(responses.GET, url, json={'error': 'not found'}, status=404)
    resp = api.get_order_by_id('1')
    assert resp['status'] == 'failure'


@responses.activate
def test_modify_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/orders/1'
    responses.add(responses.PUT, url, json={'ok': True}, status=200)
    resp = api.modify_order('1', api.LIMIT, 'ENTRY', 1, 10, 0, 0, api.DAY)
    assert resp['status'] == 'success'
    sent = json.loads(responses.calls[0].request.body)
    assert sent['orderId'] == '1'


@responses.activate
def test_cancel_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/orders/1'
    responses.add(responses.DELETE, url, json={'ok': True}, status=200)
    resp = api.cancel_order('1')
    assert resp['status'] == 'success'


@responses.activate
def test_place_slice_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/orders/slicing'
    responses.add(responses.POST, url, json={'id': '2'}, status=200)
    resp = api.place_slice_order('1', api.NSE, api.BUY, 1, api.MARKET, api.CNC, 10)
    assert resp['status'] == 'success'


@responses.activate
def test_open_browser_for_tpin_bulk(tmp_path, monkeypatch):
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/edis/form'
    responses.add(responses.POST, url, json={'edisFormHtml': '<form></form>'}, status=200)
    import sys, tempfile

    monkeypatch.setattr(sys.modules['dhanhq.dhanhq'], 'web_open', lambda x: None)

    tmp_file_path = tmp_path / 'temp_form.html'

    class DummyTempFile:
        def __init__(self, path):
            self.name = str(path)
            self._f = open(self.name, 'w')

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self._f.close()

        def write(self, data):
            self._f.write(data)

    def dummy_named_tempfile(*args, **kwargs):
        assert kwargs.get('delete') is False
        return DummyTempFile(tmp_file_path)

    monkeypatch.setattr(sys.modules['dhanhq.dhanhq'].tempfile, 'NamedTemporaryFile', dummy_named_tempfile)

    resp = api.open_browser_for_tpin('ISIN', 1, 'NSE', bulk=True)
    assert resp['status'] == 'success'
    sent = json.loads(responses.calls[0].request.body)
    assert sent['bulk'] is True
    assert not tmp_file_path.exists()


@responses.activate
def test_generate_bulk_tpin_form():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/edis/bulkform'
    responses.add(responses.POST, url, json={'edisFormHtml': '<form>\\data</form>'}, status=200)
    data = [{'isin': 'ISIN', 'qty': 1, 'exchange': 'NSE'}]
    resp = api.generate_bulk_tpin_form(data)
    assert resp['status'] == 'success'
    assert resp['data']['edisFormHtml'] == '<form>data</form>'
    sent = json.loads(responses.calls[0].request.body)
    assert sent['edisRequests'] == data


@responses.activate
def test_kill_switch_failure():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/killswitch?killSwitchStatus=ACTIVATE'
    responses.add(responses.POST, url, json={'err': 'bad'}, status=400)
    resp = api.kill_switch('activate')
    assert resp['status'] == 'failure'


@responses.activate
def test_kill_switch_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/killswitch?killSwitchStatus=DEACTIVATE'
    responses.add(responses.POST, url, json={'status': 'off'}, status=200)
    resp = api.kill_switch('deactivate')
    assert resp['status'] == 'success'
    assert resp['data'] == {'status': 'off'}


@responses.activate
def test_get_kill_switch_status_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/killswitch'
    responses.add(responses.GET, url, json={'status': 'ACTIVE'}, status=200)
    resp = api.get_kill_switch_status()
    assert resp['status'] == 'success'
    assert resp['data'] == {'status': 'ACTIVE'}


def test_convert_to_date_time():
    api = dhanhq('CID', 'TOKEN')
    dt = api.convert_to_date_time(0)
    assert dt.year == 1970


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(monkeypatch):
    ws = DummyWS()
    feed = DhanFeed('CID', 'TOKEN', [], version='v2')
    feed.ws = ws
    monkeypatch.setattr(asyncio, 'ensure_future', lambda coro: asyncio.create_task(coro))
    monkeypatch.setattr(DhanFeed, 'validate_and_process_tuples', lambda self, lst, batch_size=100: {'15': [[(1, '1')]]})
    feed.subscribe_symbols([(1, '1', 15)])
    await asyncio.sleep(0)
    assert ws.sent
    ws.sent.clear()
    feed.unsubscribe_symbols([(1, '1', 15)])
    await asyncio.sleep(0)
    assert ws.sent
