import os
import pandas as pd
from datetime import datetime, time, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from dhanhq.dhanhq import dhanhq
import logging

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- App and Database Configuration ---
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config['SECRET_KEY'] = 'a_very_secret_key'
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'strategies.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Global Variables ---
try:
    instrument_df = pd.read_csv('https://images.dhan.co/api-data/api-scrip-master.csv', low_memory=False)
    logging.info("Successfully loaded security master file.")
except Exception as e:
    logging.error(f"FATAL: Could not load instrument file: {e}")
    instrument_df = pd.DataFrame()

# --- Database Model ---
class Strategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    product_type = db.Column(db.String(20), default='INTRADAY', nullable=False)
    entry_time = db.Column(db.Time, nullable=False)
    exit_time = db.Column(db.Time, nullable=False)
    
    call_transaction_type = db.Column(db.String(4), default='SELL', nullable=False)
    call_strike_offset = db.Column(db.Integer, default=0)
    
    put_transaction_type = db.Column(db.String(4), default='SELL', nullable=False)
    put_strike_offset = db.Column(db.Integer, default=0)

    lots = db.Column(db.Integer, default=1, nullable=False)
    stop_loss_amount = db.Column(db.Float, default=0.0)
    target_profit_amount = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default='inactive')
    trade_active = db.Column(db.Boolean, default=False)
    call_security_id = db.Column(db.String(20))
    put_security_id = db.Column(db.String(20))

    trades = db.relationship('TradeResult', backref='strategy', lazy=True)

    def __repr__(self):
        return f'<Strategy {self.name}>'


class TradeResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    pnl = db.Column(db.Float, default=0.0)
    reason = db.Column(db.String(50))


class DailyPnL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Date, unique=True)
    pnl = db.Column(db.Float, default=0.0)

# --- DhanHQ API Helper ---
def get_api():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if not client_id or not access_token:
        logging.error("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set as environment variables.")
        return None
    return dhanhq(client_id, access_token)

# --- Core Trading Logic ---
def get_opposite_transaction(transaction_type):
    return "BUY" if transaction_type == "SELL" else "SELL"

def square_off_position(api, strategy, reason="", pnl=None):
    """Helper function to square off a strategy's open positions and record results."""
    logging.info(f"Squaring off position for {strategy.name}. Reason: {reason}")
    quantity = 50 * strategy.lots
    
    # Place opposite orders to close the positions
    call_exit_transaction = get_opposite_transaction(strategy.call_transaction_type)
    put_exit_transaction = get_opposite_transaction(strategy.put_transaction_type)
    
    api.place_order(security_id=strategy.call_security_id, exchange_segment=api.FNO,
                    transaction_type=call_exit_transaction, quantity=quantity, order_type=api.MARKET,
                    product_type=strategy.product_type, price=0)
    api.place_order(security_id=strategy.put_security_id, exchange_segment=api.FNO,
                    transaction_type=put_exit_transaction, quantity=quantity, order_type=api.MARKET,
                    product_type=strategy.product_type, price=0)

    # Determine pnl if not provided
    if pnl is None:
        pos = api.get_positions()
        if pos.get('status') == 'success' and pos.get('data'):
            df = pd.DataFrame(pos['data'])
            call_pos = df[df['securityId'] == strategy.call_security_id]
            put_pos = df[df['securityId'] == strategy.put_security_id]
            if not call_pos.empty and not put_pos.empty:
                pnl = call_pos.iloc[0]['unrealizedProfit'] + put_pos.iloc[0]['unrealizedProfit']
            else:
                pnl = 0.0
        else:
            pnl = 0.0

    # Record trade result and update daily PnL
    trade = TradeResult(strategy_id=strategy.id, pnl=pnl, reason=reason)
    db.session.add(trade)
    day = date.today()
    daily = DailyPnL.query.filter_by(day=day).first()
    if not daily:
        daily = DailyPnL(day=day, pnl=pnl)
        db.session.add(daily)
    else:
        daily.pnl += pnl

    strategy.trade_active = False
    strategy.status = f'stopped ({reason})'
    db.session.commit()

def execute_strategies():
    with app.app_context():
        if date.today().weekday() > 4: return

        api = get_api()
        if not api: return

        logging.info("--- Running Strategy Executor ---")
        current_time = datetime.now().time()
        
        # P&L Monitoring for running strategies
        running_strategies = Strategy.query.filter_by(status='running').all()
        if running_strategies:
            positions = api.get_positions()
            if positions.get('status') == 'success' and positions.get('data'):
                positions_df = pd.DataFrame(positions['data'])
                for strategy in running_strategies:
                    call_pos = positions_df[positions_df['securityId'] == strategy.call_security_id]
                    put_pos = positions_df[positions_df['securityId'] == strategy.put_security_id]
                    
                    if not call_pos.empty and not put_pos.empty:
                        pnl = call_pos.iloc[0]['unrealizedProfit'] + put_pos.iloc[0]['unrealizedProfit']
                        logging.info(f"Strategy: {strategy.name}, Current P&L: ₹{pnl:.2f}")

                        if pnl >= strategy.target_profit_amount > 0:
                            square_off_position(api, strategy, reason="TP Hit", pnl=pnl)
                        elif pnl <= -abs(strategy.stop_loss_amount):
                            square_off_position(api, strategy, reason="SL Hit", pnl=pnl)
        
        # Entry and Time-based Exit Logic
        strategies_to_check = Strategy.query.filter(Strategy.status.in_(['active', 'running'])).all()
        for strategy in strategies_to_check:
            # Entry Logic
            if strategy.status == 'active' and current_time >= strategy.entry_time and not strategy.trade_active:
                logging.info(f"Entering trade for strategy: {strategy.name}")
                nifty_spot_data = api.quote_data(securities={"IDX_I": ["13"]})
                if nifty_spot_data.get('status') != 'success': continue
                nifty_ltp = nifty_spot_data['data']['13']['LTP']
                atm_strike = round(nifty_ltp / 50) * 50
                
                call_strike = atm_strike + (strategy.call_strike_offset * 50)
                put_strike = atm_strike - (strategy.put_strike_offset * 50)
                
                today = date.today()
                days_to_thursday = (3 - today.weekday() + 7) % 7
                expiry_date = today + timedelta(days=days_to_thursday)
                expiry_str = expiry_date.strftime('%d%b%y').upper()

                call_symbol = f"NIFTY {expiry_str} {call_strike} CE"
                put_symbol = f"NIFTY {expiry_str} {put_strike} PE"

                try:
                    call_sec_id = str(instrument_df[instrument_df['SEM_TRADING_SYMBOL'] == call_symbol]['SEM_SMST_SECURITY_ID'].iloc[0])
                    put_sec_id = str(instrument_df[instrument_df['SEM_TRADING_SYMBOL'] == put_symbol]['SEM_SMST_SECURITY_ID'].iloc[0])
                except IndexError:
                    logging.error(f"Could not find security IDs for {call_symbol} or {put_symbol}")
                    continue

                quantity = 50 * strategy.lots
                call_order = api.place_order(security_id=call_sec_id, exchange_segment=api.FNO, transaction_type=strategy.call_transaction_type, quantity=quantity, order_type=api.MARKET, product_type=strategy.product_type, price=0)
                put_order = api.place_order(security_id=put_sec_id, exchange_segment=api.FNO, transaction_type=strategy.put_transaction_type, quantity=quantity, order_type=api.MARKET, product_type=strategy.product_type, price=0)

                if call_order.get('status') == 'success' and put_order.get('status') == 'success':
                    strategy.trade_active = True
                    strategy.status = 'running'
                    strategy.call_security_id = call_sec_id
                    strategy.put_security_id = put_sec_id
                    db.session.commit()
                    logging.info(f"Trade placed successfully for {strategy.name}.")

            # Time-based Exit
            if strategy.status == 'running' and current_time >= strategy.exit_time:
                pnl = None
                positions = api.get_positions()
                if positions.get('status') == 'success' and positions.get('data'):
                    df = pd.DataFrame(positions['data'])
                    call_pos = df[df['securityId'] == strategy.call_security_id]
                    put_pos = df[df['securityId'] == strategy.put_security_id]
                    if not call_pos.empty and not put_pos.empty:
                        pnl = call_pos.iloc[0]['unrealizedProfit'] + put_pos.iloc[0]['unrealizedProfit']
                square_off_position(api, strategy, reason="Exit Time", pnl=pnl)

# --- Flask Routes ---
@app.route("/")
def index():
    if session.get("logged_in"): return redirect(url_for("manage_strategies"))
    return render_template("index.html")

@app.post("/login")
def login():
    if request.form.get("username") == "admin" and request.form.get("password") == "admin@123":
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
    if not session.get("logged_in"): return redirect(url_for("index"))

    if request.method == "POST":
        try:
            new_strategy = Strategy(
                name=request.form["name"],
                product_type=request.form["product_type"],
                entry_time=datetime.strptime(request.form["entry_time"], '%H:%M').time(),
                exit_time=datetime.strptime(request.form["exit_time"], '%H:%M').time(),
                lots=int(request.form["lots"]),
                call_transaction_type=request.form["call_transaction_type"],
                call_strike_offset=int(request.form["call_strike_offset"]),
                put_transaction_type=request.form["put_transaction_type"],
                put_strike_offset=int(request.form["put_strike_offset"]),
                stop_loss_amount=float(request.form["stop_loss_amount"]),
                target_profit_amount=float(request.form["target_profit_amount"]),
                status='active'
            )
            db.session.add(new_strategy)
            db.session.commit()
            flash(f"Strategy '{new_strategy.name}' created successfully.", 'success')
        except Exception as e:
            flash(f"Error creating strategy: {e}", 'danger')
        return redirect(url_for("manage_strategies"))

    all_strategies = Strategy.query.order_by(Strategy.id.desc()).all()
    return render_template("strategies.html", strategies=all_strategies)

@app.route("/strategy/delete/<int:strategy_id>", methods=["POST"])
def delete_strategy(strategy_id):
    if not session.get("logged_in"): return redirect(url_for("index"))
    strategy = Strategy.query.get_or_404(strategy_id)
    try:
        db.session.delete(strategy)
        db.session.commit()
        flash(f"Strategy '{strategy.name}' deleted.", 'success')
    except Exception as e:
        flash(f"Error deleting strategy: {e}", 'danger')
    return redirect(url_for("manage_strategies"))


@app.route('/trade')
def trade_page():
    if not session.get("logged_in"): return redirect(url_for("index"))
    return render_template('trading.html')


@app.route('/orders')
def orders_page():
    if not session.get("logged_in"): return redirect(url_for("index"))
    api = get_api()
    orders = []
    if api:
        try:
            orders = api.get_order_list().get('data', [])
        except Exception as e:
            logging.error(f"Error fetching orders: {e}")
    return render_template('order_list.html', orders=orders)


@app.route('/analytics')
def analytics_page():
    if not session.get("logged_in"): return redirect(url_for('index'))
    return render_template('analytics.html')


def _calc_drawdown(cum):
    dd = []
    max_val = float('-inf')
    for v in cum:
        max_val = max(max_val, v)
        dd.append(v - max_val)
    return dd


@app.route('/analytics/data')
def analytics_data():
    if not session.get("logged_in"): return {}
    daily = DailyPnL.query.order_by(DailyPnL.day).all()
    dates = [d.day.strftime('%Y-%m-%d') for d in daily]
    pnl = [d.pnl for d in daily]
    cumulative = []
    total = 0
    for p in pnl:
        total += p
        cumulative.append(total)
    drawdown = _calc_drawdown(cumulative)
    return {
        'dates': dates,
        'pnl': pnl,
        'cumulative': cumulative,
        'drawdown': drawdown,
    }


@app.route('/export/<log_type>')
def export_logs(log_type):
    if not session.get('logged_in'): return redirect(url_for('index'))
    if log_type == 'live':
        data = [
            {
                'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': t.strategy.name if t.strategy else '',
                'pnl': t.pnl,
                'reason': t.reason,
            }
            for t in TradeResult.query.order_by(TradeResult.timestamp).all()
        ]
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)
        return app.response_class(csv, mimetype='text/csv')
    elif log_type == 'backtest':
        path = os.path.join(app.root_path, 'backtest_logs.csv')
        if os.path.exists(path):
            return send_file(path, mimetype='text/csv', as_attachment=True, download_name='backtest_logs.csv')
        return app.response_class('', mimetype='text/csv')
    return '', 404
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(execute_strategies, 'interval', minutes=1)
    scheduler.start()
    
    logging.info("Scheduler started. The app is running.")
    app.run(debug=True, use_reloader=False)
