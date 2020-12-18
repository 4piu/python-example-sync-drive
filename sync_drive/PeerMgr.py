from io import BufferedRandom
from pathlib import Path
from typing import Callable

from numpy import array


class PeerMgr:
    _encryption: bool
    _psk: bytes
    # class static var
    _peers: array
    _event_listener: dict

    def __init__(self, peers: list, encryption: bool = False, psk: bytes = None):
        self.encryption = encryption
        self.psk = psk
        # init peer sockets

    def run(self):
        pass
        # start server listening

    def stop(self):
        pass
        # stop server

    def set_event_listener(self, event: str, callback: Callable):
        pass

    async def _server_listen(self):
        pass

    async def _peer_online_handler(self):
        pass
        # invoke callback

    async def _incoming_conn_handler(self, conn: tuple):
        pass
        # update peer online status
        # handle logic
        # invoke callback

    async def _connection_reset_handler(self, peer: str):
        pass
        # update peer online status
        # invoke callback

    async def request_index(self, peer: str, index: array) -> array:
        pass
        # send message

    async def request_index_update(self, peer: str):
        pass
        # send message

    async def request_file(self, peer: str, file: Path, output_file_handle: BufferedRandom,
                           blk_start: int = None, blk_end: int = None):
        pass
        # send message

    async def response_index(self, conn: tuple, index: array):
        pass
        # send message

    async def response_file(self, conn: tuple, file: BufferedRandom):
        pass
        # send message
