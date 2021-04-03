# distutils: language=c++

from typing import List
import asyncio
import logging
import traceback
from multiprocessing import Process, Queue
from hummingbot.core.clock cimport Clock
from hummingbot.core.clock import Clock
from hummingbot.strategy.pure_market_making import PureMarketMakingStrategy
from hummingbot.core.event.events import (
    OrderFilledEvent,
    BuyOrderCompletedEvent,
    SellOrderCompletedEvent,
    MarketEvent,
    OrderBookEvent,
    OrderBookTradeEvent
)
from hummingbot.core.data_type.composite_order_book import CompositeOrderBook
from hummingbot.core.data_type.composite_order_book cimport CompositeOrderBook
from hummingbot.core.event.event_listener cimport EventListener
from hummingbot.core.event.event_forwarder import SourceInfoEventForwarder
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.script.script_adapter import ScriptAdapter
from hummingbot.script.script_interface import (
    StrategyParameter,
    PMMParameters,
    ActiveOrder,
    PmmMarketInfo
)

sir_logger = None

cdef class OrderBookTradeListener(EventListener):

    cdef list _events

    def __init__(self):
        super().__init__()
        self._events = []

    cdef c_call(self, object event_object):
        try:
            self._events.append(event_object)
        except Exception as e:
            self.logger().error("Error call trade listener.", exc_info=True)

    def get_and_reset_trades(self):
        trades = self._events
        self._events = []
        return trades


cdef class ScriptIterator(TimeIterator):
    ORDER_BOOK_TRADE_EVENT_TAG = OrderBookEvent.TradeEvent.value

    @classmethod
    def logger(cls):
        global sir_logger
        if sir_logger is None:
            sir_logger = logging.getLogger(__name__)
        return sir_logger

    def __init__(self,
                 script_file_path: str,
                 markets: List[ExchangeBase],
                 strategy: PureMarketMakingStrategy,
                 queue_check_interval: float = 0.01,
                 is_unit_testing_mode: bool = False):
        super().__init__()
        self._script_file_path = script_file_path
        self._markets = markets
        self._strategy = strategy
        self._is_unit_testing_mode = is_unit_testing_mode
        self._queue_check_interval = queue_check_interval
        self._order_filled_forwarder = SourceInfoEventForwarder(self._order_filled)
        self._did_complete_buy_order_forwarder = SourceInfoEventForwarder(self._did_complete_buy_order)
        self._did_complete_sell_order_forwarder = SourceInfoEventForwarder(self._did_complete_sell_order)
        self._event_pairs = [
            (MarketEvent.OrderFilled, self._order_filled_forwarder),
            (MarketEvent.BuyOrderCompleted, self._did_complete_buy_order_forwarder),
            (MarketEvent.SellOrderCompleted, self._did_complete_sell_order_forwarder)
        ]
        self._ev_loop = asyncio.get_event_loop()

        self._live_updates = False
        self._order_book_trade_listener = None

        self.logger().info(f"Loading script: {script_file_path}")
        self._script_adapter = ScriptAdapter()
        # any exception here is handled by calling code
        self._script_adapter.load_script(self, script_file_path)

    @property
    def strategy(self):
        return self._strategy

    @property
    def live_updates(self):
        return self._live_updates

    @live_updates.setter
    def live_updates(self, value: bool):
        self._live_updates = value

    cdef c_start(self, Clock clock, double timestamp):
        TimeIterator.c_start(self, clock, timestamp)
        for market in self._markets:
            for event_pair in self._event_pairs:
                market.add_listener(event_pair[0], event_pair[1])
        try:
            self._script_adapter.start(PmmMarketInfo(
                self._strategy.market_info.market.name,
                self._strategy.trading_pair))
        except Exception:
            self.handle_exception('c_start')

    cdef c_stop(self, Clock clock):
        TimeIterator.c_stop(self, clock)

    cdef c_tick(self, double timestamp):
        TimeIterator.c_tick(self, timestamp)
        if not self._strategy.all_markets_ready():
            return
        elif self._order_book_trade_listener is None:
            self._order_book_trade_listener = OrderBookTradeListener()
            order_book = self.strategy.market_info.order_book
            (<CompositeOrderBook>order_book).c_add_listener(
                self.ORDER_BOOK_TRADE_EVENT_TAG,
                self._order_book_trade_listener)

        cdef object pmm_strategy = PMMParameters()
        for attr in PMMParameters.__dict__.keys():
            if attr[:1] != '_':
                param_value = getattr(self._strategy, attr)
                setattr(pmm_strategy, attr, param_value)

        orders = []
        for order in self.strategy.active_orders:
            active_order = ActiveOrder(order.price, order.quantity, order.is_buy)
            orders.append(active_order)

        try:
            self._script_adapter.tick(self.strategy.get_mid_price(),
                                      pmm_strategy,
                                      self.all_total_balances(),
                                      self.all_available_balances(),
                                      orders,
                                      self._order_book_trade_listener.get_and_reset_trades())
        except Exception:
            self.handle_exception('c_tick')

    def _order_filled(self,
                      event_tag: int,
                      market: ExchangeBase,
                      event: OrderFilledEvent):
        try:
            self._script_adapter.order_filled(event)
        except Exception:
            self.handle_exception('_order_filled')

    def _did_complete_buy_order(self,
                                event_tag: int,
                                market: ExchangeBase,
                                event: BuyOrderCompletedEvent):
        try:
            self._script_adapter.buy_order_completed(event)
        except Exception:
            self.handle_exception('_did_complete_buy_order')

    def _did_complete_sell_order(self,
                                 event_tag: int,
                                 market: ExchangeBase,
                                 event: SellOrderCompletedEvent):
        try:
            self._script_adapter.sell_order_completed(event)
        except Exception:
            self.handle_exception('_did_complete_sell_order')

    def set_strategy_parameter(self, item: StrategyParameter):
        setattr(self._strategy, item.name, item.updated_value)

    def notify(self, msg: str):
        # ignore this on unit testing as the below import will mess up unit testing.
        if not self._is_unit_testing_mode:
            from hummingbot.client.hummingbot_application import HummingbotApplication
            HummingbotApplication.main_application()._notify(msg)

    def set_live_text(self, text: str):
        # ignore this on unit testing as the below import will mess up unit testing.
        if not self._is_unit_testing_mode:
            from hummingbot.client.hummingbot_application import HummingbotApplication
            if self.live_updates is True:
                HummingbotApplication.main_application().app.set_live_text(text)

    def send_image(self, image: str):
        if not self._is_unit_testing_mode:
            from hummingbot.client.hummingbot_application import HummingbotApplication
            HummingbotApplication.main_application()._send_image(image)

    def request_stop(self, reason: str):
        if not self._is_unit_testing_mode:
            msg = 'Stop request has been received from script\n'
            msg += f"Reason: {reason}"
            from hummingbot.client.hummingbot_application import HummingbotApplication
            hb = HummingbotApplication.main_application()
            hb._notify(msg)
            hb.stop()

    def force_order_refresh(self):
        self._strategy.force_order_refresh()

    def log(self, msg: str):
        self.logger().info(f"script - {msg}")

    def handle_exception(self, location: str):
        lines = traceback.format_exc().splitlines()
        msg = f'<b>Script exception in function \'{location}\':</b>\n'
        for line in lines:
            self.log(f'  {line}')
            msg += f'<pre>  {line}</pre>\n'
        self.notify(msg)
        self.request_stop('Exception')

    def request_status(self):
        try:
            self._script_adapter.status()
        except Exception:
            self.handle_exception('request_status')

    def command(self, cmd: str, args: List[str]):
        try:
            self._script_adapter.command(cmd, args)
        except Exception:
            self.handle_exception('command')

    def order_refresh(self):
        try:
            self._script_adapter.order_refresh()
        except Exception:
            self.handle_exception('order_refresh')

    def all_total_balances(self):
        all_bals = {m.name: m.get_all_balances() for m in self._markets}
        return {exchange: {token: bal for token, bal in bals.items() if bal > 0} for exchange, bals in all_bals.items()}

    def all_available_balances(self):
        all_bals = self.all_total_balances()
        ret_val = {}
        for exchange, balances in all_bals.items():
            connector = [c for c in self._markets if c.name == exchange][0]
            ret_val[exchange] = {token: connector.get_available_balance(token) for token in balances.keys()}
        return ret_val
