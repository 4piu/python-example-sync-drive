import asyncio
from asyncio import StreamWriter, StreamReader
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
        self._peer_mgr = PeerMgr(kwargs["peer_ips"], config.listen_port, compression=config.enable_gzip,
                                 encryption=kwargs["encryption"], psk=kwargs["psk"])

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # set callbacks
        self._file_mgr.set_event_listener("on_file_change", self.file_change_handler)
        self._peer_mgr.set_event_listener("on_request_index", self.request_index_handler)
        self._peer_mgr.set_event_listener("on_request_index_update", self.request_index_update_handler)
        self._peer_mgr.set_event_listener("on_request_file", self.request_file_handler)
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
        pass

    async def request_index_handler(self, reader: StreamReader, writer: StreamWriter, client_index: dict):
        pass

    async def request_index_update_handler(self, reader: StreamReader, writer: StreamWriter, client_index: dict):
        pass

    async def request_file_handler(self, reader: StreamReader, writer: StreamWriter, file_path: str, block_index: int):
        pass
