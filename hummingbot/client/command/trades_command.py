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
from hummingbot.core.data_type.common import OpenOrder
from hummingbot.client.performance import smart_round
from hummingbot.client.command.history_command import get_timestamp
from hummingbot.client.config.global_config_map import global_config_map

s_float_0 = float(0)
s_decimal_0 = Decimal("0")

if TYPE_CHECKING:
    from hummingbot.client.hummingbot_application import HummingbotApplication


class TradesCommand:
    def trades(self,  # type: HummingbotApplication
               days: float,
               market: str,
               open_order_markets: bool):
        if threading.current_thread() != threading.main_thread():
            self.ev_loop.call_soon_threadsafe(self.trades, days, market, open_order_markets)
            return
        safe_ensure_future(self.trades_report(days, market, open_order_markets))

    async def trades_report(self,  # type: HummingbotApplication
                            days: float,
                            market: str,
                            open_order_markets: bool):
        connector = await self.get_binance_connector()
        if connector is None:
            self._notify("This command supports only binance (for now), please first connect to binance.")
            return
        self._notify(f"<pre>Starting: {datetime.fromtimestamp(get_timestamp(days)).strftime('%Y-%m-%d %H:%M:%S')}\n"
                     f"Ending: {datetime.fromtimestamp(get_timestamp(0)).strftime('%Y-%m-%d %H:%M:%S')}</pre>")
        self._notify("Retrieving trades....")
        if market is not None:
            markets = {market.upper()}
        elif open_order_markets:
            orders: List[OpenOrder] = await connector.get_open_orders()
            markets = {o.trading_pair for o in orders}
        else:
            markets = set(global_config_map["binance_markets"].value.split(","))
        markets = sorted(markets)
        for market in markets:
            await self.market_trades_report(connector, days, market)

    async def market_trades_report(self,  # type: HummingbotApplication
                                   connector,
                                   days: float,
                                   market: str):
        trades: List[Trade] = await connector.get_my_trades(market, days)
        if not trades:
            self._notify(f"There is no trade on {market}.")
            return
        data = []
        columns = ["Time", " Side", " Price", "Amount"]
        trades = sorted(trades, key=lambda x: (x.trading_pair, x.timestamp))

        for trade in trades:
            time = f"{datetime.fromtimestamp(trade.timestamp / 1e3).strftime('%H:%M:%S')} "
            side = "BUY" if trade.side is TradeType.BUY else "SELL"
            data.append([time, side, smart_round(trade.price), smart_round(trade.amount)])

        lines = []
        df: pd.DataFrame = pd.DataFrame(data=data, columns=columns)
        lines.extend([f"<b>{market.upper()}</b>"])
        for line in df.to_string(index=False).split("\n"):
            lines.append("<pre>" + line + "</pre>")
        self._notify("\n" + "\n".join(lines))
