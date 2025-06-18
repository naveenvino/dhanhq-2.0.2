import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from dhanhq.dhanhq import dhanhq
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = "dhanhq-front"

# In-memory store for strategies (for a real application, use a database)
strategies = []

def get_api():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if not client_id or not access_token:
        raise RuntimeError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set")
    return dhanhq(client_id, access_token)

def execute_strategies():
    """
    This function is called by the scheduler to execute trading strategies.
    This is a placeholder for your actual trading logic.
    """
    api = get_api()
    print("Executing strategies...")
    for strategy in strategies:
        if strategy["status"] == "active":
            # 1. Check if it's time to enter a trade based on strategy.entry_time
            # 2. Fetch market data for Nifty to determine strike prices.
            # 3. Place orders using api.place_order().
            # 4. Monitor the position for stop-loss or target profit.
            # 5. Exit the position at strategy.exit_time or if SL/TGT is hit.
            pass

@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("strategies"))
    return render_template("index.html")

@app.post("/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if username == "admin" and password == "admin@123":
        session["logged_in"] = True
        return redirect(url_for("strategies"))
    flash("Invalid credentials")
    return redirect(url_for("index"))

@app.route("/strategies", methods=["GET", "POST"])
def manage_strategies():
    if not session.get("logged_in"):
        return redirect(url_for("index"))

    if request.method == "POST":
        strategy = {
            "name": request.form["name"],
            "entry_time": request.form["entry_time"],
            "exit_time": request.form["exit_time"],
            "call_strike": request.form["call_strike"],
            "put_strike": request.form["put_strike"],
            "stop_loss": request.form["stop_loss"],
            "target_profit": request.form["target_profit"],
            "status": "active"
        }
        strategies.append(strategy)
        flash(f"Strategy '{strategy['name']}' created successfully.")
        return redirect(url_for("manage_strategies"))

    return render_template("strategies.html", strategies=strategies)

@app.route("/place_order", methods=["POST"])
def place_order():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
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
    return redirect(url_for("trade"))

@app.route("/orders")
def orders():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    api = get_api()
    resp = api.get_order_list()
    return render_template("order_list.html", orders=resp.get("data", []))

if __name__ == "__main__":
    # Start the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(execute_strategies, 'interval', minutes=1)
    scheduler.start()
    
    # To run the app, set your credentials and run this file:
    # export DHAN_CLIENT_ID=your_id
    # export DHAN_ACCESS_TOKEN=your_token
    # python webapp/app.py
    app.run(debug=True)