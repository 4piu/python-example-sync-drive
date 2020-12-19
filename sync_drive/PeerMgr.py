import asyncio
import pickle
import zlib
from asyncio import StreamWriter, StreamReader
from asyncio.base_events import Server
from enum import Enum
from io import BufferedRandom
from pathlib import Path
from typing import Callable


class MsgType(Enum):
    REQ_INDEX = 0
    REQ_INDEX_UPDATE = 1
    REQ_FILE = 2
    RES_INDEX = 3
    RES_INDEX_UPDATE = 4
    RES_FILE = 5


class PeerMgr:
    _server: Server
    _encryption: bool
    _compression: bool
    _psk: bytes
    _peers: dict
    _event_listener: dict
    _listen_port: int

    def __init__(self, peers: list, listen_port: int, compression: bool = True, encryption: bool = False,
                 psk: bytes = None):
        self._encryption = encryption
        self._compression = compression
        self._psk = psk
        self._event_listener = {
            "on_request_index": None,
            "on_request_index_update": None,
            "on_request_file": None
        }
        self._listen_port = listen_port
        self._peers = dict()
        # init peer sockets
        for ip in peers:
            self._peers[ip] = {"is_online": False}

    def run(self):
        loop = asyncio.get_event_loop()
        # start server listening
        self._server = loop.run_until_complete(
            asyncio.start_server(self._conn_handler, host="0.0.0.0", port=self._listen_port))
        print(f"Server listen on 0.0.0.0:{self._listen_port}")

    def stop(self):
        print("Stopping PeerMgr")
        # stop server
        self._server.close()
        asyncio.get_event_loop().run_until_complete(self._server.wait_closed())

    def set_event_listener(self, event: str, callback: Callable):
        self._event_listener[event] = callback

    async def _get_peer_conn(self, ip: str) -> (StreamReader, StreamWriter):
        try:
            reader, writer = await asyncio.open_connection(host=ip, port=self._listen_port)
            self._peers[ip].update({
                "is_online": True
            })
            print(f"Connected to {ip} successfully")
            return reader, writer
        except Exception as e:
            self._peers[ip].update({
                "is_online": False
            })
            print(f"Connect to {ip} failed")
            raise e

    async def _conn_handler(self, reader: StreamReader, writer: StreamWriter):
        client_ip = writer.get_extra_info('peername')
        if client_ip not in self._peers.keys():  # only allow connection from peers
            writer.close()
            print(f"Refuse connection from {client_ip}")
        print(f"Connection from {client_ip}")
        # update online status
        self._peers[client_ip].update({
            "is_online": True
        })
        # get message
        msg_type = MsgType(int.from_bytes(await reader.read(1), "big"))
        msg_length = int.from_bytes(await reader.read(8), "big")
        if msg_type == MsgType.REQ_INDEX and self._event_listener["on_request_index"]:
            client_index = pickle.loads(await reader.read(msg_length))
            await self._event_listener["on_request_index"](reader, writer, client_index)
        elif msg_type == MsgType.REQ_INDEX_UPDATE and self._event_listener["on_request_index_update"]:
            client_index = pickle.loads(await reader.read(msg_length))
            await self._event_listener["on_request_index_update"](reader, writer, client_index)
        elif msg_type == MsgType.REQ_FILE and self._event_listener["on_request_file"]:
            msg = pickle.loads(await reader.read(msg_length))
            await self._event_listener["on_request_file"](reader, writer, msg["file_path"], msg["block_index"])
        else:
            writer.close()
            print(f"Invalid message from {client_ip}")

    async def request_index(self, ip: str, index: dict) -> dict:
        # send message
        reader, writer = await self._get_peer_conn(ip)
        writer.write(int.to_bytes(MsgType.REQ_INDEX.value, 1, "big"))
        data = pickle.dumps(index)
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        await writer.drain()
        # receive response
        msg_type = MsgType(int.from_bytes(await reader.read(1), "big"))
        msg_length = int.from_bytes(await reader.read(8), "big")
        if msg_type != MsgType.RES_INDEX:
            writer.close()
            print(f"Invalid response from {ip}")
            raise Exception("Invalid response")
        file_index = pickle.loads(await reader.read(msg_length))
        writer.close()
        return file_index

    async def request_index_update(self, ip: str, index: dict):
        # send message
        reader, writer = await self._get_peer_conn(ip)
        writer.write(int.to_bytes(MsgType.REQ_INDEX_UPDATE.value, 1, "big"))
        data = pickle.dumps(index)
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        await writer.drain()
        # receive response
        msg_type = MsgType(int.from_bytes(await reader.read(1), "big"))
        msg_length = int.from_bytes(await reader.read(8), "big")
        if msg_type != MsgType.RES_INDEX_UPDATE:
            writer.close()
            print(f"Invalid response from {ip}")
            raise Exception("Invalid response")
        _ = await reader.read(msg_length)
        writer.close()

    async def request_file(self, ip: str, file: Path,
                           output_file_handle: BufferedRandom,
                           block_index: int, block_size: int):
        # send message
        reader, writer = await self._get_peer_conn(ip)
        writer.write(int.to_bytes(MsgType.REQ_FILE.value, 1, "big"))
        data = pickle.dumps({
            "file_path": str(file),
            "block_index": block_index
        })
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        await writer.drain()
        # receive response
        msg_type = MsgType(int.from_bytes(await reader.read(1), "big"))
        msg_length = int.from_bytes(await reader.read(8), "big")
        if msg_type != MsgType.RES_INDEX_UPDATE:
            writer.close()
            print(f"Invalid response from {ip}")
            raise Exception("Invalid response")
        output_file_handle.seek(block_index * block_size)
        data = await reader.read(block_size)
        if self._compression:
            data = zlib.decompress(data)
        output_file_handle.write(data)
        output_file_handle.close()
        writer.close()
