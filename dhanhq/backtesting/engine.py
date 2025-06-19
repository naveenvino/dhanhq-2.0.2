"""Simple backtesting engine for DhanHQ."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Position:
    """Represents a trading position."""

    security_id: str
    quantity: int
    avg_price: float

    def update(self, qty: int, price: float) -> None:
        total_qty = self.quantity + qty
        if total_qty == 0:
            self.avg_price = 0
            self.quantity = 0
            return
        self.avg_price = ((self.avg_price * self.quantity) + (price * qty)) / total_qty
        self.quantity = total_qty

    def pnl(self, current_price: float) -> float:
        return (current_price - self.avg_price) * self.quantity


class BacktestEngine:
    """Very small simulator for order placement and P&L tracking."""

    def __init__(self, candles: List[Dict[str, float]]):
        self.candles = candles
        self.index = 0
        self.orders: List[Dict] = []
        self.positions: Dict[str, Position] = {}

    @property
    def current_price(self) -> float:
        if not self.candles:
            return 0.0
        return float(self.candles[self.index].get("close", 0))

    def step(self) -> None:
        if self.index < len(self.candles) - 1:
            self.index += 1

    def place_order(self, security_id: str, side: str, quantity: int) -> Dict:
        price = self.current_price
        order = {
            "order_id": str(len(self.orders) + 1),
            "security_id": security_id,
            "side": side,
            "quantity": quantity,
            "price": price,
        }
        self.orders.append(order)
        multiplier = 1 if side.upper() == "BUY" else -1
        pos = self.positions.get(security_id)
        if not pos:
            pos = Position(security_id, 0, price)
            self.positions[security_id] = pos
        pos.update(multiplier * quantity, price)
        return order

    def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    def total_pnl(self) -> float:
        price = self.current_price
        return sum(pos.pnl(price) for pos in self.positions.values())
