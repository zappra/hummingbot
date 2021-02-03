import asyncio
from multiprocessing import Queue
from typing import List, Optional, Dict, Any, Callable
from decimal import Decimal
from statistics import mean, median
from operator import itemgetter
from .script_interface import OnTick, OnStatus, OnCommand, OnRefresh, PMMParameters, CallNotify, CallSendImage, CallLog, CallStop, CallForceRefresh
from hummingbot.core.event.events import (
    OrderFilledEvent,
    BuyOrderCompletedEvent,
    SellOrderCompletedEvent
)


class ScriptBase:
    """
    ScriptBase provides functionality which a script can use to interact with the main HB application.
    A user defined script should derive from this base class to get all its functionality.
    """
    def __init__(self):
        self._parent_queue: Queue = None
        self._child_queue: Queue = None
        self._queue_check_interval: float = 0.0
        self._mid_price: Decimal = Decimal("0")
        self.pmm_parameters: PMMParameters = None
        # all_total_balances stores balances in {exchange: {token: balance}} format
        # for example {"binance": {"BTC": Decimal("0.1"), "ETH": Decimal("20"}}
        self.all_total_balances: Dict[str, Dict[str, Decimal]] = None

    def assign_init(self, parent_queue: Queue, child_queue: Queue, queue_check_interval: float):
        self._parent_queue = parent_queue
        self._child_queue = child_queue
        self._queue_check_interval = queue_check_interval

    @property
    def mid_price(self):
        """
        The current market mid price (the average of top bid and top ask)
        """
        return self._mid_price

    async def run(self):
        asyncio.ensure_future(self.listen_to_parent())

    async def listen_to_parent(self):
        while True:
            if self._parent_queue.empty():
                await asyncio.sleep(self._queue_check_interval)
                continue
            item = self._parent_queue.get()
            # print(f"child gets {str(item)}")
            if item is None:
                # print("child exiting..")
                asyncio.get_event_loop().stop()
                break
            if isinstance(item, OnTick):
                self._mid_price = item.mid_price
                self.pmm_parameters = item.pmm_parameters
                self.all_total_balances = item.all_total_balances
                self.on_tick()
            elif isinstance(item, OrderFilledEvent):
                self.on_order_filled(item)
            elif isinstance(item, BuyOrderCompletedEvent):
                self.on_buy_order_completed(item)
            elif isinstance(item, SellOrderCompletedEvent):
                self.on_sell_order_completed(item)
            elif isinstance(item, OnStatus):
                status_msg = self.on_status()
                if status_msg:
                    self.notify(f"Script status: {status_msg}")
            elif isinstance(item, OnCommand):
                self.on_command(item.cmd, item.args)
            elif isinstance(item, OnRefresh):
                self.on_order_refresh()

    def notify(self, msg: str):
        """
        Notifies the user, the message will appear on top left panel of HB application.
        If Telegram integration enabled, the message will also be sent to the telegram user.
        :param msg: The message.
        """
        self._child_queue.put(CallNotify(msg))

    def send_image(self, image: str):
        """
        Send image via notifiers
        """
        self._child_queue.put(CallSendImage(image))

    def log(self, msg: str):
        """
        Logs message to the strategy log file and display it on Running Logs section of HB.
        :param msg: The message.
        """
        self._child_queue.put(CallLog(msg))

    def request_stop(self, reason: str):
        """
        Request stop command on main strategy in the event of error or custom kill switch type condition
        :param reason: Reason, which will be logged by main application
        """
        self._child_queue.put(CallStop(reason))
    
    def force_order_refresh(self):
        """
        Force an order refresh cycle to occur
        """
        self._child_queue.put(CallForceRefresh())

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

