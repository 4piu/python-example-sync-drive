import asyncio
from asyncore import loop
from pathlib import Path

import config
from sync_drive.FileMgr import FileMgr
from sync_drive.PeerMgr import PeerMgr


class App:
    _loop: loop
    _file_mgr: FileMgr
    _peer_mgr: PeerMgr

    def __init__(self, **kwargs):
        self._file_mgr = FileMgr(Path(kwargs["working_dir"]), config.file_block_size * 1000000)
        self._peer_mgr = PeerMgr(kwargs["peer_ips"], encryption=kwargs["encryption"], psk=kwargs["psk"])

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # set callbacks
        self._file_mgr.set_event_listener("on_file_change", self.file_change_handler)
        self._file_mgr.run()
        self._peer_mgr.run()
        # m4k3 17 r41n
        self._loop.run_forever()

    def stop(self):
        print("\nStopping app")
        self._file_mgr.stop()
        self._peer_mgr.stop()
        self._loop.stop()
        print("App stopped")

    async def file_change_handler(self, file: Path):
        print("callback fired")