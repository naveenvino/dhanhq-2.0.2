import argparse
import json
import os
import sqlite3
from datetime import datetime

import pandas as pd

from .dhanhq import dhanhq


def _db_path():
    return os.getenv(
        "STRATEGIES_DB",
        os.path.join(os.path.dirname(__file__), "..", "webapp", "strategies.db"),
    )


def _session_file():
    return os.getenv(
        "PAPER_SESSION_FILE",
        os.path.join(os.path.dirname(__file__), "..", "paper_session.txt"),
    )


def run_backtest(path):
    """Very simple backtest that calculates profit from OHLC data."""
    df = pd.read_csv(path)
    if "close" not in df.columns:
        raise ValueError("CSV must contain a 'close' column")
    profit = float(df["close"].iloc[-1] - df["close"].iloc[0])
    return {"profit": profit}


def start_paper():
    with open(_session_file(), "w") as f:
        f.write("running")
    return {"status": "started"}


def stop_paper():
    with open(_session_file(), "w") as f:
        f.write("stopped")
    return {"status": "stopped"}


def upload_strategy(path):
    with open(path) as f:
        data = json.load(f)

    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO strategy (
            name, product_type, entry_time, exit_time, lots,
            call_transaction_type, call_strike_offset,
            put_transaction_type, put_strike_offset,
            stop_loss_amount, target_profit_amount, status, trade_active
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            data["name"],
            data.get("product_type", "INTRADAY"),
            data["entry_time"],
            data["exit_time"],
            int(data.get("lots", 1)),
            data.get("call_transaction_type", "SELL"),
            int(data.get("call_strike_offset", 0)),
            data.get("put_transaction_type", "SELL"),
            int(data.get("put_strike_offset", 0)),
            float(data.get("stop_loss_amount", 0.0)),
            float(data.get("target_profit_amount", 0.0)),
            "active",
            False,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"status": "uploaded", "id": new_id}


def parse_args():
    parser = argparse.ArgumentParser(description="CLI for DhanHQ API")
    parser.add_argument("client_id", help="Dhan client id")
    parser.add_argument("access_token", help="Dhan access token")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-orders", help="List today's orders")

    get_order = subparsers.add_parser("get-order", help="Get order by id")
    get_order.add_argument("order_id")

    place = subparsers.add_parser("place-order", help="Place a simple order")
    place.add_argument("security_id")
    place.add_argument("exchange_segment")
    place.add_argument("transaction_type")
    place.add_argument("quantity", type=int)
    place.add_argument("order_type")
    place.add_argument("product_type")
    place.add_argument("price", type=float)

    subparsers.add_parser("positions", help="Get open positions")

    backtest = subparsers.add_parser("backtest", help="Run backtest on data file")
    backtest.add_argument("data_file")

    subparsers.add_parser("paper-start", help="Start paper trading session")
    subparsers.add_parser("paper-stop", help="Stop paper trading session")

    upload = subparsers.add_parser(
        "upload-strategy", help="Upload strategy parameters from JSON file"
    )
    upload.add_argument("json_file")

    return parser.parse_args()


def main():
    args = parse_args()
    api = dhanhq(args.client_id, args.access_token)

    if args.command == "list-orders":
        resp = api.get_order_list()
    elif args.command == "get-order":
        resp = api.get_order_by_id(args.order_id)
    elif args.command == "place-order":
        resp = api.place_order(
            security_id=args.security_id,
            exchange_segment=args.exchange_segment,
            transaction_type=args.transaction_type,
            quantity=args.quantity,
            order_type=args.order_type,
            product_type=args.product_type,
            price=args.price,
        )
    elif args.command == "positions":
        resp = api.get_positions()
    elif args.command == "backtest":
        resp = run_backtest(args.data_file)
    elif args.command == "paper-start":
        resp = start_paper()
    elif args.command == "paper-stop":
        resp = stop_paper()
    elif args.command == "upload-strategy":
        resp = upload_strategy(args.json_file)
    else:
        return

    print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()
