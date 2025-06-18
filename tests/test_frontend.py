import pytest
from flask import Flask, request, jsonify
from dhanhq.dhanhq import dhanhq

app = Flask(__name__)
orders = []
api = dhanhq('CID', 'TOKEN')

@app.route('/')
def index():
    return 'ok'

@app.post('/order')
def order():
    data = request.get_json()
    api.place_order(**data)
    orders.append(data)
    return jsonify({'status': 'success'})

@app.get('/orders')
def list_orders():
    return jsonify({'orders': orders})


def test_home():
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200


def test_place_order(monkeypatch):
    calls = []

    def fake_place_order(self, *args, **kwargs):
        calls.append(kwargs)
        return {'id': '1'}

    monkeypatch.setattr(dhanhq, 'place_order', fake_place_order)
    orders.clear()
    client = app.test_client()
    payload = {
        'security_id': '1',
        'exchange_segment': api.NSE,
        'transaction_type': api.BUY,
        'quantity': 1,
        'order_type': api.MARKET,
        'product_type': api.INTRA,
        'price': 0,
    }
    resp = client.post('/order', json=payload)
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'success'
    assert calls and calls[0]['security_id'] == '1'

    resp = client.get('/orders')
    data = resp.get_json()
    assert data['orders'] and data['orders'][0]['security_id'] == '1'

