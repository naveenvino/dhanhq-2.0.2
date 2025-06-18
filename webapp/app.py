import os
import pandas as pd
from datetime import datetime, time, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from dhanhq.dhanhq import dhanhq

# --- App and Database Configuration ---
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config['SECRET_KEY'] = 'a_very_secret_key'
# Use an absolute path for the database file
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'strategies.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Global Variables ---
# Load the security master file for instrument lookups
try:
    # Use low_memory=False to address the DtypeWarning
    instrument_df = pd.read_csv('https://images.dhan.co/api-data/api-scrip-master.csv', low_memory=False)
except Exception as e:
    print(f"Error loading instrument file: {e}")
    instrument_df = pd.DataFrame() # Create an empty DataFrame on failure

# --- Database Model ---
class Strategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    entry_time = db.Column(db.Time, nullable=False)
    exit_time = db.Column(db.Time, nullable=False)
    call_strike_offset = db.Column(db.Integer, default=0) # e.g., 0 for ATM, 1 for 1 OTM
    put_strike_offset = db.Column(db.Integer, default=0)
    stop_loss_percent = db.Column(db.Float, default=0.0)
    target_profit_percent = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='inactive') # inactive, active, running, stopped
    
    # Fields to track live trades
    trade_active = db.Column(db.Boolean, default=False)
    entry_premium = db.Column(db.Float, default=0.0)
    call_order_id = db.Column(db.String(50))
    put_order_id = db.Column(db.String(50))

    def __repr__(self):
        return f'<Strategy {self.name}>'

# --- DhanHQ API Helper ---
def get_api():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if not client_id or not access_token:
        print("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set as environment variables.")
        return None
    return dhanhq(client_id, access_token)

# --- Core Trading Logic ---
def execute_strategies():
    with app.app_context():
        # This is a holiday/weekend, so we don't run the strategy
        if date.today().weekday() > 4: 
             return

        api = get_api()
        if not api:
            print("Scheduler: Cannot get API instance. Check credentials.")
            return

        print(f"[{datetime.now()}] --- Running Strategy Executor ---")
        
        active_strategies = Strategy.query.filter_by(status='active').all()
        
        for strategy in active_strategies:
            current_time = datetime.now().time()

            # 1. Check for Strategy Entry
            if current_time >= strategy.entry_time and not strategy.trade_active:
                print(f"Entering trade for strategy: {strategy.name}")
                
                # --- Get Nifty Spot and ATM Strike ---
                nifty_spot_data = api.quote_data(securities={"IDX_I": ["13"]}) # 13 is securityId for NIFTY 50 Index
                if nifty_spot_data['status'] != 'success' or not nifty_spot_data.get('data'):
                    print(f"Could not fetch Nifty Spot price for {strategy.name}")
                    continue
                
                nifty_ltp = nifty_spot_data['data']['13']['LTP']
                atm_strike = round(nifty_ltp / 50) * 50
                print(f"Nifty Spot: {nifty_ltp}, ATM Strike: {atm_strike}")

                # --- Determine Strike Prices and Expiry ---
                call_strike = atm_strike + (strategy.call_strike_offset * 50)
                put_strike = atm_strike - (strategy.put_strike_offset * 50)
                
                today = date.today()
                days_to_thursday = (3 - today.weekday() + 7) % 7
                expiry_date = today + timedelta(days=days_to_thursday)
                expiry_str = expiry_date.strftime('%d%b%y').upper() # e.g., 20JUN24

                # --- Find Security IDs for Options ---
                call_symbol = f"NIFTY {expiry_str} {call_strike} CE"
                put_symbol = f"NIFTY {expiry_str} {put_strike} PE"

                try:
                    call_security_id = instrument_df[instrument_df['SEM_TRADING_SYMBOL'] == call_symbol]['SEM_SMST_SECURITY_ID'].iloc[0]
                    put_security_id = instrument_df[instrument_df['SEM_TRADING_SYMBOL'] == put_symbol]['SEM_SMST_SECURITY_ID'].iloc[0]
                except IndexError:
                    print(f"Could not find security IDs for {call_symbol} or {put_symbol}")
                    continue

                print(f"Selling {call_symbol} (ID: {call_security_id}) and {put_symbol} (ID: {put_security_id})")

                # --- Place Sell Orders (Short Strangle) ---
                call_order = api.place_order(
                    security_id=str(call_security_id), exchange_segment=api.FNO,
                    transaction_type=api.SELL, quantity=50, order_type=api.MARKET,
                    product_type=api.INTRA, price=0
                )
                put_order = api.place_order(
                    security_id=str(put_security_id), exchange_segment=api.FNO,
                    transaction_type=api.SELL, quantity=50, order_type=api.MARKET,
                    product_type=api.INTRA, price=0
                )

                if call_order.get('status') == 'success' and put_order.get('status') == 'success':
                    strategy.trade_active = True
                    strategy.status = 'running'
                    strategy.call_order_id = call_order.get('data', {}).get('orderId')
                    strategy.put_order_id = put_order.get('data', {}).get('orderId')
                    db.session.commit()
                    print(f"Trade placed successfully for {strategy.name}.")
                else:
                    print(f"Failed to place trades for {strategy.name}. Call: {call_order}, Put: {put_order}")

            # 2. Check for Strategy Exit (Time-based)
            if current_time >= strategy.exit_time and strategy.trade_active:
                print(f"Exit time reached for {strategy.name}. Squaring off.")
                strategy.trade_active = False
                strategy.status = 'stopped'
                db.session.commit()

            # 3. P&L Monitoring (Placeholder)
            if strategy.status == 'running':
                pass

# --- Flask Routes ---
@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("manage_strategies"))
    return render_template("index.html")

@app.post("/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if username == "admin" and password == "admin@123":
        session["logged_in"] = True
        return redirect(url_for("manage_strategies"))
    flash("Invalid credentials")
    return redirect(url_for("index"))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route("/strategies", methods=["GET", "POST"])
def manage_strategies():
    if not session.get("logged_in"):
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            entry_time_val = datetime.strptime(request.form["entry_time"], '%H:%M').time()
            exit_time_val = datetime.strptime(request.form["exit_time"], '%H:%M').time()
            
            new_strategy = Strategy(
                name=request.form["name"],
                entry_time=entry_time_val, exit_time=exit_time_val,
                call_strike_offset=int(request.form["call_strike_offset"]),
                put_strike_offset=int(request.form["put_strike_offset"]),
                stop_loss_percent=float(request.form["stop_loss_percent"]),
                target_profit_percent=float(request.form["target_profit_percent"]),
                status='active'
            )
            db.session.add(new_strategy)
            db.session.commit()
            flash(f"Strategy '{new_strategy.name}' created successfully.", 'success')
        except Exception as e:
            flash(f"Error creating strategy: {e}", 'danger')
        
        return redirect(url_for("manage_strategies"))

    all_strategies = Strategy.query.all()
    return render_template("strategies.html", strategies=all_strategies)

@app.route("/strategy/delete/<int:strategy_id>", methods=["POST"])
def delete_strategy(strategy_id):
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    strategy_to_delete = Strategy.query.get_or_404(strategy_id)
    try:
        db.session.delete(strategy_to_delete)
        db.session.commit()
        flash(f"Strategy '{strategy_to_delete.name}' deleted.", 'success')
    except Exception as e:
        flash(f"Error deleting strategy: {e}", 'danger')
        
    return redirect(url_for("manage_strategies"))
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    scheduler = BackgroundScheduler()
    scheduler.add_job(execute_strategies, 'interval', minutes=1)
    scheduler.start()
    
    print("Scheduler started. The app is running.")
    app.run(debug=True, use_reloader=False)
