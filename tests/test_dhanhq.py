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
