from typing import List
import asyncio
from hummingbot.core.utils.async_utils import safe_ensure_future


class ScriptCommand:

    def script_command(self,  # HummingbotApplication
                       cmd: str = None,
                       args: List[str] = None):
        if self._script_iterator is not None:
            self._script_iterator.request_command(cmd, args)
            if cmd == 'live':
                safe_ensure_future(self.script_live_updates(), loop=self.ev_loop)
        else:
            self._notify('No script is active, command ignored')

        return True

    async def script_live_updates(self):
        await self.stop_live_update()
        self.app.live_updates = True
        self._script_iterator.set_live_updates(True)
        while self.app.live_updates:
            await asyncio.sleep(1)
        if self._script_iterator is not None:
            self._script_iterator.set_live_updates(False)
        self._notify("Stopped script live update.")
