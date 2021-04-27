import asyncio
import platform
import threading
from typing import TYPE_CHECKING
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.core.utils.eth_gas_station_lookup import EthGasStationLookup
if TYPE_CHECKING:
    from hummingbot.client.hummingbot_application import HummingbotApplication


class StopCommand:
    def stop(self,  # type: HummingbotApplication
             skip_order_cancellation: bool = False):
        if threading.current_thread() != threading.main_thread():
            self.ev_loop.call_soon_threadsafe(self.stop, skip_order_cancellation)
            return
        safe_ensure_future(self.stop_loop(skip_order_cancellation), loop=self.ev_loop)

    async def stop_loop(self,  # type: HummingbotApplication
                        skip_order_cancellation: bool = False):
        self.logger().info("stop command initiated.")
        self._notify("\nWinding down...")

        # Restore App Nap on macOS.
        if platform.system() == "Darwin":
            import appnope
            appnope.nap()

        if self._trading_required and not skip_order_cancellation:
            if self.strategy_name == 'perpetual_market_making':
                # ensure no new orders are created
                self.strategy.exiting = True

                # cancel outstanding orders
                success = await self._cancel_outstanding_orders()

                # now go ahead and cancel any open positions
                self._notify("Closing open positions...")
                # Give some time for cancellation events to trigger
                await asyncio.sleep(1.0)
                while True:
                    if len(self.strategy.active_positions) == 0:
                        break
                    await asyncio.sleep(0.1)

                # give some time for script fill notifications
                await asyncio.sleep(1.0)
                self._notify("All positions closed.")

                self.markets = {}
            else:
                # Remove the strategy from clock
                if self.clock:
                    self.clock.remove_iterator(self.strategy)
                success = await self._cancel_outstanding_orders()
                # Give some time for cancellation events to trigger
                await asyncio.sleep(0.5)

                if success:
                    # Only erase markets when cancellation has been successful
                    self.markets = {}

        if self._script_iterator is not None:
            self._script_iterator.stop(self.clock)
            self._script_iterator = None

        if self.strategy_task is not None and not self.strategy_task.cancelled():
            self.strategy_task.cancel()

        if EthGasStationLookup.get_instance().started:
            EthGasStationLookup.get_instance().stop()

        if self.markets_recorder is not None:
            self.markets_recorder.stop()

        if self.kill_switch is not None:
            self.kill_switch.stop()

        self.wallet = None
        self.strategy_task = None
        self.strategy = None
        self.market_pair = None
        self.clock = None
        self.markets_recorder = None
        self.market_trading_pairs_map.clear()
