import asyncio
import pickle
import zlib
from asyncio import StreamWriter, StreamReader
from asyncio.base_events import Server
from enum import Enum
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
    peers: dict
    _event_listener: dict
    _listen_port: int

    def __init__(self, peers: list, listen_port: int, compression: bool = True, encryption: bool = False,
                 psk: bytes = None):
        self._encryption = encryption
        self._compression = compression
        self._psk = psk
        self._event_listener = {
            "on_started": None,
            # "on_file_written": None,
            "on_request_index": None,
            "on_request_index_update": None,
            "on_request_file": None
        }
        self._listen_port = listen_port
        self.peers = dict()
        # init peer sockets
        for ip in peers:
            self.peers[ip] = {"is_online": False}

    def run(self):
        loop = asyncio.get_event_loop()
        # start server listening
        self._server = loop.run_until_complete(
            asyncio.start_server(self._conn_handler, host="0.0.0.0", port=self._listen_port))
        print(f"Server listen on 0.0.0.0:{self._listen_port}")
        if self._event_listener["on_started"]:
            loop.run_until_complete(self._event_listener["on_started"]())

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
            self.peers[ip].update({
                "is_online": True
            })
            return reader, writer
        except Exception as e:
            self.peers[ip].update({
                "is_online": False
            })
            raise e

    async def _conn_handler(self, reader: StreamReader, writer: StreamWriter):
        client_ip = writer.get_extra_info('peername')[0]
        if client_ip not in self.peers:  # only allow connection from peers
            writer.close()
            print(f"Refuse connection from {client_ip}")
        # update online status
        self.peers[client_ip].update({
            "is_online": True
        })
        # get message
        msg_type = MsgType(int.from_bytes(await reader.readexactly(1), "big"))
        msg_length = int.from_bytes(await reader.readexactly(8), "big")
        if msg_type == MsgType.REQ_INDEX and self._event_listener["on_request_index"]:
            client_index = pickle.loads(await reader.readexactly(msg_length))
            print(f"{client_ip} request index exchange")
            await self._event_listener["on_request_index"](writer, client_index)
        elif msg_type == MsgType.REQ_INDEX_UPDATE and self._event_listener["on_request_index_update"]:
            client_index = pickle.loads(await reader.readexactly(msg_length))
            print(f"{client_ip} request index update")
            await self._event_listener["on_request_index_update"](writer, client_index)
        elif msg_type == MsgType.REQ_FILE and self._event_listener["on_request_file"]:
            msg = pickle.loads(await reader.readexactly(msg_length))
            print(f"{client_ip} request file {msg['file_path']} blk:{msg['block_index']}")
            await self._event_listener["on_request_file"](writer, msg["file_path"], msg["block_index"])
        else:
            writer.close()
            print(f"Invalid message from {client_ip}")

    async def request_index(self, ip: str, local_index: dict) -> dict:
        print(f"Request index exchange with {ip}")
        # send message
        reader, writer = await self._get_peer_conn(ip)
        writer.write(int.to_bytes(MsgType.REQ_INDEX.value, 1, "big"))
        data = pickle.dumps(local_index)
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        # await writer.drain()
        # receive response
        msg_type = MsgType(int.from_bytes(await reader.readexactly(1), "big"))
        msg_length = int.from_bytes(await reader.readexactly(8), "big")
        if msg_type != MsgType.RES_INDEX:
            writer.close()
            print(f"Invalid response from {ip}")
            raise Exception("Invalid response")
        file_index = pickle.loads(await reader.readexactly(msg_length))
        writer.close()
        return file_index

    async def request_index_update(self, ip: str, changed_index: dict):
        print(f"Request index update of {ip}")
        # send message
        reader, writer = await self._get_peer_conn(ip)
        writer.write(int.to_bytes(MsgType.REQ_INDEX_UPDATE.value, 1, "big"))
        data = pickle.dumps(changed_index)
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        # await writer.drain()
        # receive response
        msg_type = MsgType(int.from_bytes(await reader.readexactly(1), "big"))
        msg_length = int.from_bytes(await reader.readexactly(8), "big")
        if msg_type != MsgType.RES_INDEX_UPDATE:
            writer.close()
            print(f"Invalid response from {ip}")
            raise Exception("Invalid response")
        _ = await reader.readexactly(msg_length)
        writer.close()

    async def request_file(self, ip: str, file: str, block_index: int, block_size: int):
        print(f"Request {file} blk:{block_index} from {ip}")
        # send message
        reader, writer = await self._get_peer_conn(ip)
        writer.write(int.to_bytes(MsgType.REQ_FILE.value, 1, "big"))
        data = pickle.dumps({
            "file_path": file,
            "block_index": block_index
        })
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        # await writer.drain()
        # receive response
        msg_type = MsgType(int.from_bytes(await reader.readexactly(1), "big"))
        msg_length = int.from_bytes(await reader.readexactly(8), "big")
        if msg_type != MsgType.RES_FILE:
            writer.close()
            print(f"Invalid response from {ip}")
            raise Exception("Invalid response")
        # write file
        with open(file, mode="r+b") as f:
            f.seek(block_index * block_size)
            data = await reader.readexactly(msg_length)
            # print(f"message_length: {msg_length} received: {len(data)}")
            if self._compression:
                data = zlib.decompress(data)
            f.write(data)
            f.close()
        # on file written callback
        # if self._event_listener["on_file_written"]:
        #     await self._event_listener["on_file_written"](file)
        writer.close()
