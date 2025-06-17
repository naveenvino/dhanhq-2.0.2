import json
import responses
from dhanhq.dhanhq import dhanhq

@responses.activate
def test_place_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/orders'
    responses.add(responses.POST, url, json={"order_id": "1"}, status=200)

    resp = api.place_order(
        security_id='123',
        exchange_segment=api.NSE,
        transaction_type=api.BUY,
        quantity=1,
        order_type=api.MARKET,
        product_type=api.INTRA,
        price=0
    )

    assert resp['status'] == 'success'
    assert resp['data'] == {"order_id": "1"}

    sent = json.loads(responses.calls[0].request.body)
    assert sent['dhanClientId'] == 'CID'
    assert sent['transactionType'] == api.BUY

@responses.activate
def test_get_positions_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/positions'
    responses.add(responses.GET, url, json={"positions": []}, status=200)

    resp = api.get_positions()

    assert resp['status'] == 'success'
    assert resp['data'] == {"positions": []}


@responses.activate
def test_get_super_orders_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/super/orders'
    responses.add(responses.GET, url, json={"orders": []}, status=200)

    resp = api.get_super_orders()

    assert resp['status'] == 'success'
    assert resp['data'] == {"orders": []}


@responses.activate
def test_place_super_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/super/orders'
    responses.add(responses.POST, url, json={"id": "1"}, status=200)

    resp = api.place_super_order(
        security_id='1',
        exchange_segment=api.NSE,
        transaction_type=api.BUY,
        product_type=api.INTRA,
        order_type=api.LIMIT,
        quantity=1,
        price=10,
        trigger_price=9,
        target=12,
        stop_loss=8
    )

    assert resp['status'] == 'success'
    assert resp['data'] == {"id": "1"}

    sent = json.loads(responses.calls[0].request.body)
    assert sent['dhanClientId'] == 'CID'
    assert sent['securityId'] == '1'


@responses.activate
def test_modify_super_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/super/orders/123'
    responses.add(responses.PUT, url, json={"ok": True}, status=200)

    resp = api.modify_super_order('123', leg_name='ENTRY_LEG', price=11)

    assert resp['status'] == 'success'

    sent = json.loads(responses.calls[0].request.body)
    assert sent['orderId'] == '123'
    assert sent['price'] == 11


@responses.activate
def test_cancel_super_order_success():
    api = dhanhq('CID', 'TOKEN')
    url = api.base_url + '/super/orders/123'
    responses.add(responses.DELETE, url, json={"status": "cancelled"}, status=200)

    resp = api.cancel_super_order('123')

    assert resp['status'] == 'success'
    assert resp['data'] == {"status": "cancelled"}
