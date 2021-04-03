import importlib
import inspect
import os
from decimal import Decimal
from typing import Dict, List

from hummingbot.script.script_base import ScriptBase
from hummingbot.script.script_interface import (
    PMMParameters,
    ActiveOrder,
    PmmMarketInfo
)
from hummingbot.core.event.events import (
    OrderFilledEvent,
    BuyOrderCompletedEvent,
    SellOrderCompletedEvent,
    OrderBookTradeEvent
)
from .script_interface import set_iterator


# this class sits between ScriptIterator and ScriptBase to break circular dependency
class ScriptAdapter:

    def __init__(self):
        self.script = None

    def load_script(self, iterator, script_file_name: str):
        script_class = self.import_script_sub_class(script_file_name)
        self.script = script_class()
        self.script.iterator = iterator
        set_iterator(iterator)

    def import_script_sub_class(self, script_file_name: str):
        name = os.path.basename(script_file_name).split(".")[0]
        spec = importlib.util.spec_from_file_location(name, script_file_name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for x in dir(module):
            obj = getattr(module, x)
            if inspect.isclass(obj) and issubclass(obj, ScriptBase) and obj.__name__ != "ScriptBase":
                return obj

    def start(self, item: PmmMarketInfo):
        if self.script is not None:
            self.script.pmm_market_info = item

    def tick(self,
             mid_price: Decimal,
             pmm_parameters: PMMParameters,
             all_total_balances: Dict[str, Dict[str, Decimal]],
             all_available_balances: Dict[str, Dict[str, Decimal]],
             orders: List[ActiveOrder],
             trades: List[OrderBookTradeEvent]):
        if self.script is not None:
            self.script.tick(mid_price, pmm_parameters, all_total_balances, all_total_balances,
                             orders, trades)

    def order_filled(self, event: OrderFilledEvent):
        if self.script is not None:
            self.script.on_order_filled(event)

    def buy_order_completed(self, event: BuyOrderCompletedEvent):
        if self.script is not None:
            self.script.on_buy_order_completed(event)

    def sell_order_completed(self, event: SellOrderCompletedEvent):
        if self.script is not None:
            self.script.on_sell_order_completed(event)

    def order_refresh(self):
        if self.script is not None:
            self.script.on_order_refresh()

    def command(self, cmd: str, args: List[str]):
        if self.script is not None:
            self.script.on_command(cmd, args)

    def status(self):
        if self.script is not None:
            status_msg = self.script.on_status()
            if status_msg:
                from hummingbot.client.hummingbot_application import HummingbotApplication
                HummingbotApplication.main_application()._notify(status_msg)
