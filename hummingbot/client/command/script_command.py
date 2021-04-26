from typing import List
import asyncio
import threading
from hummingbot.core.utils.async_utils import safe_ensure_future


class ScriptCommand:

    def script_command(self,  # HummingbotApplication
                       cmd: str = None,
                       args: List[str] = None):
        if threading.current_thread() != threading.main_thread():
            self.ev_loop.call_soon_threadsafe(self.script_command, cmd, args)
            return

        if self._script_iterator is not None:
            if cmd == 'live':
                # script doesn't process this command, just sets a flag on the iterator
                safe_ensure_future(self.script_live_updates(), loop=self.ev_loop)
            else:
                self._script_iterator.command(cmd, args)
        else:
            self._notify('No script is active, command ignored')

        return True

    async def script_live_updates(self):
        await self.stop_live_update()
        self.app.live_updates = True
        self._script_iterator.live_updates = True
        while self.app.live_updates:
            await asyncio.sleep(1)
        if self._script_iterator is not None:
            self._script_iterator.live_updates = False
        self._notify("Stopped script live update.")
