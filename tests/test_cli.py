import os
import sys
import json
import shutil
import sqlite3
import tempfile

import pandas as pd
import dhanhq.cli as cli


def run_cli(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["prog"] + args)
    out = []

    def fake_print(s):
        out.append(s)

    monkeypatch.setattr("builtins.print", fake_print)
    cli.main()
    return json.loads(out[0]) if out else None


def test_backtest_command(tmp_path, monkeypatch):
    data = pd.DataFrame({"close": [100, 120]})
    csv = tmp_path / "data.csv"
    data.to_csv(csv, index=False)
    result = run_cli(monkeypatch, ["CID", "TOKEN", "backtest", str(csv)])
    assert result["profit"] == 20


def test_paper_session_commands(tmp_path, monkeypatch):
    session_file = tmp_path / "session.txt"
    monkeypatch.setenv("PAPER_SESSION_FILE", str(session_file))
    run_cli(monkeypatch, ["CID", "TOKEN", "paper-start"])
    assert session_file.read_text() == "running"
    run_cli(monkeypatch, ["CID", "TOKEN", "paper-stop"])
    assert session_file.read_text() == "stopped"


def test_upload_strategy_command(tmp_path, monkeypatch):
    db_copy = tmp_path / "strategies.db"
    shutil.copyfile(os.path.join("webapp", "strategies.db"), db_copy)
    monkeypatch.setenv("STRATEGIES_DB", str(db_copy))
    json_file = tmp_path / "params.json"
    params = {
        "name": "test",
        "entry_time": "09:15",
        "exit_time": "15:15",
        "lots": 1,
        "call_transaction_type": "SELL",
        "call_strike_offset": 0,
        "put_transaction_type": "SELL",
        "put_strike_offset": 0,
        "stop_loss_amount": 0,
        "target_profit_amount": 0,
        "product_type": "INTRADAY",
    }
    json_file.write_text(json.dumps(params))
    result = run_cli(monkeypatch, ["CID", "TOKEN", "upload-strategy", str(json_file)])
    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()
    cur.execute("SELECT name FROM strategy WHERE id=?", (result["id"],))
    row = cur.fetchone()
    conn.close()
    assert row and row[0] == "test"
