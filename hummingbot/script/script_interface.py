from typing import Dict, List
from decimal import Decimal
from hummingbot.core.event.events import OrderBookTradeEvent

child_queue = None


def set_child_queue(queue):
    global child_queue
    child_queue = queue


class StrategyParameter(object):
    """
    A strategy parameter class that is used as a property for the collection class with its get and set method.
    The set method detects if there is a value change it will put itself into the child queue.
    """
    def __init__(self, attr):
        self.name = attr
        self.attr = "_" + attr
        self.updated_value = None

    def __get__(self, obj, objtype):
        return getattr(obj, self.attr)

    def __set__(self, obj, value):
        global child_queue
        old_value = getattr(obj, self.attr)
        if (old_value is not None and old_value != value):
            self.updated_value = value
            child_queue.put(self)
        setattr(obj, self.attr, value)

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class PMMParameters:
    """
    A collection of pure market making strategy parameters which are configurable through script.
    The members names need to match the property names of PureMarketMakingStrategy.
    """
    def __init__(self):
        self._buy_levels = None
        self._sell_levels = None
        self._order_levels = None
        self._bid_spread = None
        self._ask_spread = None
        self._minimum_spread = None
        self._order_amount = None
        self._order_level_spread = None
        self._order_level_amount = None
        self._order_refresh_time = None
        self._order_refresh_tolerance_pct = None
        self._filled_order_delay = None
        self._hanging_orders_enabled = None
        self._hanging_orders_cancel_pct = None
        self._inventory_skew_enabled = None
        self._inventory_target_base_pct = None
        self._inventory_range_multiplier = None
        self._order_override = None
        self._order_optimization_enabled = None
        self._ask_order_optimization_depth = None
        self._bid_order_optimization_depth = None
        self._minimum_bid_depth = None
        self._minimum_ask_depth = None

        # These below parameters are yet to open for the script

        # self._add_transaction_costs_to_orders = None
        # self._price_ceiling = None
        # self._price_floor = None
        # self._ping_pong_enabled = None

    buy_levels = StrategyParameter("buy_levels")
    sell_levels = StrategyParameter("sell_levels")
    order_levels = StrategyParameter("order_levels")
    bid_spread = StrategyParameter("bid_spread")
    ask_spread = StrategyParameter("ask_spread")
    minimum_spread = StrategyParameter("minimum_spread")
    order_amount = StrategyParameter("order_amount")
    order_level_spread = StrategyParameter("order_level_spread")
    order_level_amount = StrategyParameter("order_level_amount")
    order_refresh_time = StrategyParameter("order_refresh_time")
    order_refresh_tolerance_pct = StrategyParameter("order_refresh_tolerance_pct")
    filled_order_delay = StrategyParameter("filled_order_delay")
    hanging_orders_enabled = StrategyParameter("hanging_orders_enabled")
    hanging_orders_cancel_pct = StrategyParameter("hanging_orders_cancel_pct")
    inventory_skew_enabled = StrategyParameter("inventory_skew_enabled")
    inventory_target_base_pct = StrategyParameter("inventory_target_base_pct")
    inventory_range_multiplier = StrategyParameter("inventory_range_multiplier")
    order_override = StrategyParameter("order_override")
    order_optimization_enabled = StrategyParameter("order_optimization_enabled")
    ask_order_optimization_depth = StrategyParameter("ask_order_optimization_depth")
    bid_order_optimization_depth = StrategyParameter("bid_order_optimization_depth")
    minimum_bid_depth = StrategyParameter("minimum_bid_depth")
    minimum_ask_depth = StrategyParameter("minimum_ask_depth")

    # add_transaction_costs_to_orders = PMMParameter("add_transaction_costs_to_orders")
    # price_ceiling = PMMParameter("price_ceiling")
    # price_floor = PMMParameter("price_floor")
    # ping_pong_enabled = PMMParameter("ping_pong_enabled")

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class PmmMarketInfo:
    def __init__(self, exchange: str,
                 trading_pair: str,):
        self.exchange = exchange
        self.trading_pair = trading_pair

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class ActiveOrder:
    def __init__(self, price: float, amount: float, is_buy: bool):
        self.price = price
        self.amount = amount
        self.is_buy = is_buy

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class OnTick:
    def __init__(self,
                 timestamp,
                 mid_price: Decimal,
                 pmm_parameters: PMMParameters,
                 all_total_balances: Dict[str, Dict[str, Decimal]],
                 all_available_balances: Dict[str, Dict[str, Decimal]],
                 orders: List[ActiveOrder],
                 trades: List[OrderBookTradeEvent]
                 ):
        self.timestamp = timestamp
        self.mid_price = mid_price
        self.pmm_parameters = pmm_parameters
        self.all_total_balances = all_total_balances
        self.all_available_balances = all_available_balances
        self.orders = orders
        self.trades = trades

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class OnStatus:
    pass


class OnRefresh:
    pass


class OnCommand:
    def __init__(self, cmd: str, args: List[str]):
        self.cmd = cmd
        self.args = args

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class CallNotify:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class CallSendImage:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class CallLog:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class CallStop:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.__dict__)}"


class ScriptError:
    def __init__(self, error: Exception, traceback: str):
        self.error = error
        self.traceback = traceback

    def __repr__(self):
        return f"{self.__class__.__name__} {str(self.error)} \nTrace back: {self.traceback}"


class CallForceRefresh:
    pass


class OrderRefreshComplete:
    pass
