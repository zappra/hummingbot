from decimal import Decimal
import pandas as pd
import threading
from typing import (
    TYPE_CHECKING,
    List,
)
from datetime import datetime
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.core.data_type.trade import Trade, TradeType
from hummingbot.client.performance import smart_round
from hummingbot.client.config.global_config_map import global_config_map

s_float_0 = float(0)
s_decimal_0 = Decimal("0")

if TYPE_CHECKING:
    from hummingbot.client.hummingbot_application import HummingbotApplication


class TradesCommand:
    def trades(self,  # type: HummingbotApplication
               num: int = 10,
               side: str = None):
        if threading.current_thread() != threading.main_thread():
            self.ev_loop.call_soon_threadsafe(self.trades, num, side)
            return
        safe_ensure_future(self.trades_report(num, side))

    async def trades_report(self,  # type: HummingbotApplication
                            num, side):
        connector = await self.get_binance_connector()
        if connector is None:
            self._notify("This command supports only binance (for now), please first connect to binance.")
            return
        self._notify("Retrieving trades....")

        markets = set(global_config_map["binance_markets"].value.split(","))
        markets = sorted(markets)
        for market in markets:
            await self.market_trades_report(connector, market, num, side)

    async def market_trades_report(self,  # type: HummingbotApplication
                                   connector,
                                   market: str,
                                   num: int,
                                   side: str):
        trades: List[Trade] = await connector.get_my_trades(market, 1)
        if not trades:
            self._notify(f"There is no trade on {market}.")
            return
        data = []
        columns = ["Time", " Side", " Price", "Amount"]
        trades = sorted(trades, key=lambda x: (x.trading_pair, x.timestamp))

        filter_side = side.upper() if side is not None else None

        for trade in trades:
            time = f"{datetime.fromtimestamp(trade.timestamp / 1e3).strftime('%H:%M:%S')} "
            side = "BUY" if trade.side is TradeType.BUY else "SELL"
            if filter_side is None or side == filter_side:
                data.append([time, side, smart_round(trade.price), smart_round(trade.amount)])

        lines = []
        df: pd.DataFrame = pd.DataFrame(data=data, columns=columns)
        df_lines = df.to_string(index=False).split("\n")

        lines.extend([f"<b>{market.upper()}</b>"])
        for i in range(-min(int(num), len(trades)), 0):
            lines.append("<pre>" + df_lines[i] + "</pre>")
        self._notify("\n" + "\n".join(lines))
