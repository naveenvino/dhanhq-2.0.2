import pytest
from flask import Flask, request, jsonify
from dhanhq.dhanhq import dhanhq

app = Flask(__name__)

@app.post('/webhook')
def webhook():
    data = request.get_json()
    api = dhanhq('CID', 'TOKEN')
    api.place_order(
        security_id=data['security_id'],
        exchange_segment=data['exchange_segment'],
        transaction_type=data['transaction_type'],
        quantity=data['quantity'],
        order_type=data.get('order_type', api.MARKET),
        product_type=data.get('product_type', api.INTRA),
        price=data.get('price', 0),
    )
    return jsonify({'status': 'ok'})


def test_webhook_places_order(monkeypatch):
    calls = []

    def fake_place_order(self, *args, **kwargs):
        calls.append(kwargs)
        return {'status': 'success'}

    monkeypatch.setattr(dhanhq, 'place_order', fake_place_order)
    client = app.test_client()
    payload = {
        'security_id': '123',
        'exchange_segment': dhanhq.NSE,
        'transaction_type': dhanhq.BUY,
        'quantity': 1,
        'order_type': dhanhq.MARKET,
        'product_type': dhanhq.INTRA,
        'price': 0,
    }
    resp = client.post('/webhook', json=payload)
    assert resp.status_code == 200
    assert calls
    assert calls[0]['security_id'] == '123'
    assert calls[0]['transaction_type'] == dhanhq.BUY


def test_webhook_custom_price(monkeypatch):
    captured = {}

    def fake_place_order(self, *args, **kwargs):
        captured.update(kwargs)
        return {'status': 'success'}

    monkeypatch.setattr(dhanhq, 'place_order', fake_place_order)
    client = app.test_client()
    payload = {
        'security_id': '555',
        'exchange_segment': dhanhq.NSE,
        'transaction_type': dhanhq.SELL,
        'quantity': 10,
        'order_type': dhanhq.LIMIT,
        'product_type': dhanhq.CNC,
        'price': 101.5,
    }
    resp = client.post('/webhook', json=payload)
    assert resp.status_code == 200
    assert captured['price'] == 101.5
    assert captured['order_type'] == dhanhq.LIMIT
