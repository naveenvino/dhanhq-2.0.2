import os
os.environ.setdefault('SECRET_KEY', 'testsecret')
os.environ.setdefault('ADMIN_USERNAME', 'admin')
os.environ.setdefault('ADMIN_PASSWORD', 'admin@123')
import webapp.app as webapp_app
app = webapp_app.app


def _login(client):
    """Helper to log in via the login route."""
    client.post('/login', data={'username': 'admin', 'password': 'admin@123'})



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
