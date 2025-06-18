import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dhanhq.dhanhq import dhanhq

client_id = os.environ.get("CLIENT_ID")
access_token = os.environ.get("ACCESS_TOKEN")

if not client_id or not access_token:
    raise RuntimeError("CLIENT_ID and ACCESS_TOKEN environment variables must be set")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

dhan = dhanhq(client_id, access_token)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/order", methods=["POST"])
def order():
    form = request.form
    result = dhan.place_order(
        security_id=form["security_id"],
        exchange_segment=form["exchange_segment"],
        transaction_type=form["transaction_type"],
        quantity=form["quantity"],
        order_type=form["order_type"],
        product_type=form["product_type"],
        price=form.get("price", 0),
        trigger_price=form.get("trigger_price", 0),
    )
    flash(str(result))
    return redirect(url_for("index"))


@app.route("/orders")
def orders():
    result = dhan.get_order_list()
    orders = result.get("data", []) if isinstance(result, dict) else []
    return render_template("orders.html", orders=orders)


if __name__ == "__main__":
    app.run(debug=True)
