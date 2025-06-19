from dhanhq.backtesting import BacktestEngine
from dhanhq.dhanhq import dhanhq


def test_engine_pnl():
    candles = [
        {"close": 100},
        {"close": 110},
    ]
    engine = BacktestEngine(candles)
    engine.place_order("1333", "BUY", 1)
    engine.step()
    pnl = engine.total_pnl()
    assert pnl == 10


def test_paper_trading_orders():
    api = dhanhq("CID", "TOKEN", paper_trading=True)
    resp = api.place_order(
        security_id="1",
        exchange_segment=api.NSE,
        transaction_type=api.BUY,
        quantity=1,
        order_type=api.MARKET,
        product_type=api.INTRA,
        price=100,
    )
    assert resp["status"] == "success"
    orders = api.get_order_list()
    assert orders["data"][0]["securityId"] == "1"
    positions = api.get_positions()
    assert positions["data"][0]["quantity"] == 1
