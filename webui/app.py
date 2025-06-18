from flask import Flask, request, redirect, url_for, session
from flask import render_template_string
from dhanhq.dhanhq import dhanhq

app = Flask(__name__)
app.secret_key = "change-this"

INDEX_HTML = '''
<h1>Dhan Web UI</h1>
<form method="post">
  <label>Client ID:<input name="client_id"></label><br>
  <label>Access Token:<input name="access_token"></label><br>
  <button type="submit">Continue</button>
</form>
'''

ORDER_FORM_HTML = '''
<h1>Place Order</h1>
<form method="post">
  <label>Security ID:<input name="security_id"></label><br>
  <label>Quantity:<input name="quantity" type="number" value="1"></label><br>
  <label>Exchange Segment:<input name="exchange_segment" value="{NSE}"></label><br>
  <label>Transaction Type:<input name="transaction_type" value="{BUY}"></label><br>
  <label>Product Type:<input name="product_type" value="{INTRA}"></label><br>
  <label>Order Type:<input name="order_type" value="{MARKET}"></label><br>
  <label>Price:<input name="price" value="0"></label><br>
  <button type="submit">Place Order</button>
</form>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['client_id'] = request.form['client_id']
        session['access_token'] = request.form['access_token']
        return redirect(url_for('place_order'))
    return render_template_string(INDEX_HTML)


def _get_api():
    cid = session.get('client_id')
    token = session.get('access_token')
    if not cid or not token:
        return None
    return dhanhq(cid, token)


@app.route('/place_order', methods=['GET', 'POST'])
def place_order():
    api = _get_api()
    if not api:
        return redirect(url_for('index'))
    if request.method == 'POST':
        params = {
            'security_id': request.form['security_id'],
            'exchange_segment': request.form['exchange_segment'],
            'transaction_type': request.form['transaction_type'],
            'quantity': int(request.form['quantity']),
            'order_type': request.form['order_type'],
            'product_type': request.form['product_type'],
            'price': float(request.form.get('price') or 0),
        }
        resp = api.place_order(**params)
        return render_template_string('<pre>{{resp}}</pre><a href="{{url_for("place_order")}}">Back</a>', resp=resp)
    return render_template_string(ORDER_FORM_HTML.format(
        NSE=api.NSE,
        BUY=api.BUY,
        INTRA=api.INTRA,
        MARKET=api.MARKET
    ))


@app.route('/positions')
def positions():
    api = _get_api()
    if not api:
        return redirect(url_for('index'))
    data = api.get_positions()
    return render_template_string('<pre>{{data}}</pre>')


@app.route('/orders')
def orders():
    api = _get_api()
    if not api:
        return redirect(url_for('index'))
    data = api.get_order_list()
    return render_template_string('<pre>{{data}}</pre>')

if __name__ == '__main__':
    app.run(debug=True)
