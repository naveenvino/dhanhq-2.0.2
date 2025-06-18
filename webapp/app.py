import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dhanhq.dhanhq import dhanhq

app = Flask(__name__)
app.secret_key = "dhanhq-front"


def get_api():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if not client_id or not access_token:
        raise RuntimeError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set")
    return dhanhq(client_id, access_token)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/place_order", methods=["POST"])
def place_order():
    api = get_api()
    data = request.form
    resp = api.place_order(
        security_id=data["security_id"],
        exchange_segment=data["exchange_segment"],
        transaction_type=data["transaction_type"],
        quantity=int(data["quantity"]),
        order_type=data.get("order_type", api.MARKET),
        product_type=data.get("product_type", api.INTRA),
        price=float(data.get("price", 0)),
    )
    flash(resp.get("status"))
    return redirect(url_for("index"))


@app.route("/orders")
def orders():
    api = get_api()
    resp = api.get_order_list()
    return render_template("order_list.html", orders=resp.get("data", []))


if __name__ == "__main__":
    app.run(debug=True)
