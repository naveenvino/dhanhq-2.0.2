import webapp.app as webapp_app
from datetime import date
app = webapp_app.app


def _login(client):
    """Helper to mark the session as logged in."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True



def test_index_page():
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'bootstrap.min.css' in html
    assert 'class="container"' in html


def test_trade_page(monkeypatch):
    client = app.test_client()
    _login(client)
    resp = client.get('/trade')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'class="container"' in html
    assert 'class="row g-3"' in html


def test_orders_page(monkeypatch):
    def fake_get_api():
        class Api:
            def get_order_list(self):
                return {"data": [{"orderId": "1", "status": "ok"}]}

        return Api()

    monkeypatch.setattr(webapp_app, 'get_api', fake_get_api)

    client = app.test_client()
    _login(client)
    resp = client.get('/orders')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'table table-bordered table-striped' in html
    assert 'class="container"' in html


def test_analytics_data_endpoint():
    client = app.test_client()
    _login(client)
    with app.app_context():
        webapp_app.db.drop_all()
        webapp_app.db.create_all()
        webapp_app.db.session.add(webapp_app.DailyPnL(day=date(2024, 1, 1), pnl=100))
        webapp_app.db.session.add(webapp_app.DailyPnL(day=date(2024, 1, 2), pnl=-50))
        webapp_app.db.session.commit()
    resp = client.get('/analytics/data')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'dates' in data and len(data['dates']) == 2
    assert 'cumulative' in data and data['cumulative'][1] == 50


def test_export_live_csv():
    client = app.test_client()
    _login(client)
    with app.app_context():
        webapp_app.db.drop_all()
        webapp_app.db.create_all()
        tr = webapp_app.TradeResult(pnl=10.0)
        webapp_app.db.session.add(tr)
        webapp_app.db.session.commit()
    resp = client.get('/export/live')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'

