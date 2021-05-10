from typing import List, Optional, Any, Callable
from decimal import Decimal
from statistics import mean, median
from operator import itemgetter

from hummingbot.core.event.events import (
    OrderFilledEvent,
    BuyOrderCompletedEvent,
    SellOrderCompletedEvent,
    OrderBookTradeEvent,
    FundingPaymentCompletedEvent
)
from .script_iterator import ScriptIterator


class StrategyParameters:
    def __init__(self, strategy, strategy_name):
        super().__setattr__("strategy", strategy)
        super().__setattr__("strategy_name", strategy_name)

    def __getattr__(self, name):
        try:
            value = getattr(self.strategy, name)
        except AttributeError:
            raise AttributeError(f'Strategy {self.strategy_name} has no attribute {name}')

        return value

    def __setattr__(self, name, value):
        try:
            setattr(self.strategy, name, value)
        except AttributeError:
            raise AttributeError(f'Strategy {self.strategy_name} has no attribute {name}')


class ScriptBase:
    """
    ScriptBase provides functionality which a script can use to interact with the main HB application.
    A user defined script should derive from this base class to get all its functionality.
    """
    def __init__(self):
        self.iterator: ScriptIterator = None
        self.strategy_parameters: StrategyParameters = None

        # list of trades recorded since last tick
        self.trades: List[OrderBookTradeEvent] = None

    def init(self, iterator):
        self.iterator = iterator

        from hummingbot.client.hummingbot_application import HummingbotApplication
        hb = HummingbotApplication.main_application()
        strategy_name = hb.strategy_name
        self.strategy_parameters = StrategyParameters(iterator.strategy, strategy_name)

    @property
    def strategy(self):
        return self.iterator.strategy

    @property
    def strategy_name(self):
        from hummingbot.client.hummingbot_application import HummingbotApplication
        hb = HummingbotApplication.main_application()
        return hb.strategy_name

    @property
    def all_total_balances(self):
        return self.iterator.all_total_balances

    @property
    def all_available_balances(self):
        return self.iterator.all_available_balances

    @property
    def active_orders(self):
        return self.iterator.active_orders

    @property
    def active_positions(self):
        return self.iterator.active_positions

    @property
    def mid_price(self):
        """
        The current market mid price (the average of top bid and top ask)
        """
        return self.iterator.strategy.get_mid_price()

    @property
    def live_updates(self):
        return self.iterator.live_updates

    def tick(self, trades: List[OrderBookTradeEvent]):
        self.trades = trades
        self.on_tick()

    def notify(self, msg: str):
        """
        Notifies the user, the message will appear on top left panel of HB application.
        If Telegram integration enabled, the message will also be sent to the telegram user.
        :param msg: The message.
        """
        self.iterator.notify(msg)

    def set_live_text(self, text: str):
        """
        Set text for live ui
        :param text: Live text
        """
        self.iterator.set_live_text(text)

    def send_image(self, image: str):
        """
        Send image via notifiers
        """
        self.iterator.send_image(image)

    def log(self, msg: str):
        """
        Logs message to the strategy log file and display it on Running Logs section of HB.
        :param msg: The message.
        """
        self.iterator.log(msg)

    def request_stop(self, reason: str):
        """
        Request stop command on main strategy in the event of error or custom kill switch type condition
        :param reason: Reason, which will be logged by main application
        """
        self.iterator.request_stop(reason)

    def force_order_refresh(self):
        """
        Force an order refresh cycle to occur
        """
        self.iterator.force_order_refresh()

    def avg_mid_price(self, interval: int, length: int) -> Optional[Decimal]:
        """
        Calculates average (mean) of the stored mid prices.
        Mid prices are stored for each tick (second).
        Examples: To get the average of the last 100 minutes mid prices = avg_mid_price(60, 100)
        :param interval: The interval (in seconds) in which to sample the mid prices.
        :param length: The number of the samples to calculate the average.
        :returns None if there is not enough samples, otherwise the average mid price.
        """
        pass

        """
        samples = self.take_samples(self.mid_prices, interval, length)
        if samples is None:
            return None
        return mean(samples)
        """

    def avg_price_volatility(self, interval: int, length: int) -> Optional[Decimal]:
        """
        Calculates average (mean) price volatility, volatility is a price change compared to the previous
        cycle regardless of its direction, e.g. if price changes -3% (or 3%), the volatility is 3%.
        Examples: To get the average of the last 10 changes on a minute interval = avg_price_volatility(60, 10)
        :param interval: The interval (in seconds) in which to sample the mid prices.
        :param length: The number of the samples to calculate the average.
        :returns None if there is not enough samples, otherwise the average mid price change.
        """
        return self.locate_central_price_volatility(interval, length, mean)

    def median_price_volatility(self, interval: int, length: int) -> Optional[Decimal]:
        """
        Calculates the median (middle value) price volatility, volatility is a price change compared to the previous
        cycle regardless of its direction, e.g. if price changes -3% (or 3%), the volatility is 3%.
        Examples: To get the median of the last 10 changes on a minute interval = median_price_volatility(60, 10)
        :param interval: The interval (in seconds) in which to sample the mid prices.
        :param length: The number of the samples to calculate the average.
        :returns None if there is not enough samples, otherwise the median mid price change.
        """
        return self.locate_central_price_volatility(interval, length, median)

    def locate_central_price_volatility(self, interval: int, length: int, locate_function: Callable) \
            -> Optional[Decimal]:
        """
        Calculates central location of the price volatility, volatility is a price change compared to the previous cycle
        regardless of its direction, e.g. if price changes -3% (or 3%), the volatility is 3%.
        Examples: To get mean of the last 10 changes on a minute interval locate_central_price_volatility(60, 10, mean)
        :param interval: The interval in which to sample the mid prices.
        :param length: The number of the samples.
        :param locate_function: The function used to calculate the central location, e.g. mean, median, geometric_mean
         and many more which are supported by statistics library.
        :returns None if there is not enough samples, otherwise the central location of mid price change.
        """
        pass

        """
        # We need sample size of length + 1, as we need a previous value to calculate the change
        samples = self.take_samples(self.mid_prices, interval, length + 1)
        if samples is None:
            return None
        changes = []
        for index in range(1, len(samples)):
            changes.append(max(samples[index], samples[index - 1]) / min(samples[index], samples[index - 1]) - 1)
        return locate_function(changes)
        """

    @staticmethod
    def round_by_step(a_number: Decimal, step_size: Decimal):
        """
        Rounds the number down by the step size, e.g. round_by_step(1.8, 0.25) = 1.75
        :param a_number: A number to round
        :param step_size: The step size.
        :returns rounded number.
        """
        return (a_number // step_size) * step_size

    @staticmethod
    def take_samples(a_list: List[Any], interval: int, length: int) -> Optional[List[any]]:
        """
        Takes samples out of a given list where the last item is the most recent,
        Examples: a list = [1, 2, 3, 4, 5, 6, 7] an interval of 3 and length of 2 will return you [4, 7],
        for an interval of 2 and length of 4, you'll get [1, 3, 5, 7]
        :param a_list: A list which to take samples from
        :param interval: The interval at which to take sample, starting from the last item on the list.
        :param length: The number of the samples.
        :returns None if there is not enough samples to satisfy length, otherwise the sample list.
        """
        index_list = list(range(len(a_list) - 1, -1, -1 * interval))
        index_list = sorted(index_list)
        index_list = index_list[-1 * length:]
        if len(index_list) < length:
            return None
        if len(index_list) == 1:
            # return a list with just 1 item in it.
            return [a_list[index_list[0]]]
        samples = list(itemgetter(*index_list)(a_list))
        return samples

    def on_tick(self):
        """
        Is called upon OnTick message received, which is every second on normal HB configuration.
        It is intended to be implemented by the derived class of this class.
        """
        pass

    def on_order_filled(self, event: OrderFilledEvent):
        """
        Called when order is filled
        """
        pass

    def on_buy_order_completed(self, event: BuyOrderCompletedEvent):
        """
        Is called upon a buy order is completely filled.
        It is intended to be implemented by the derived class of this class.
        """
        pass

    def on_sell_order_completed(self, event: SellOrderCompletedEvent):
        """
        Is called upon a sell order is completely filled.
        It is intended to be implemented by the derived class of this class.
        """
        pass

    def on_funding_payment_completed(self, event: FundingPaymentCompletedEvent):
        """
        Called for funding payments on derivative connectors
        """
        pass

    def on_status(self) -> str:
        """
        Is called upon `status` command is issued on the Hummingbot application.
        It is intended to be implemented by the derived class of this class.
        :returns status message.
        """
        return f"{self.__class__.__name__} is active."

    def on_command(self, cmd: str, args: List[str]):
        """
        Called when 'script' command is issued on the Hummingbot application
        """
        pass

    def on_order_refresh(self):
        """
        Called when order cycle is refreshing
        TODO: default implementation should make some parameter change such that main process won't stall
        """
        pass
