import asyncio
import os
import pickle
import zlib
from asyncio import StreamWriter
from asyncore import loop
from pathlib import Path

import config
from sync_drive.FileMgr import FileMgr, FileStatus
from sync_drive.PeerMgr import PeerMgr, MsgType


class App:
    _loop: loop
    _file_mgr: FileMgr
    _peer_mgr: PeerMgr

    def __init__(self, **kwargs):
        self._file_mgr = FileMgr(Path(kwargs["working_dir"]), config.file_block_size)
        self._peer_mgr = PeerMgr(kwargs["peer_ips"], config.listen_port, compression=config.enable_gzip,
                                 encryption=kwargs["encryption"], psk=kwargs["psk"])

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # set callbacks
        self._file_mgr.set_event_listener("on_file_change", self.file_change_handler)
        self._peer_mgr.set_event_listener("on_started", self.peer_mgr_started_handler)
        self._peer_mgr.set_event_listener("on_file_written", self.file_written_handler)
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

    async def file_change_handler(self, changed_items: list):
        # build file change list
        changed_index = dict()
        for file, operation in changed_items:
            if file.is_file():  # wait hash complete for modified file
                await self._file_mgr.till_hash_complete(str(file))
            changed_index[str(file)] = self._file_mgr.file_index[str(file)]
        # announce change to other peer
        for ip in self._peer_mgr.peers:
            try:
                await self._peer_mgr.request_index_update(ip, changed_index)
            except:
                print(f"Failed connect to {ip} for index update")

    async def peer_mgr_started_handler(self):
        for ip in self._peer_mgr.peers:
            try:
                index = await self._peer_mgr.request_index(ip, self._file_mgr.file_index)
                await self.sync(index, ip)
            except:
                print(f"Failed connect to {ip} for index exchange")

    async def file_written_handler(self, file: str):
        # set file modified time
        mod_time = self._file_mgr.file_index[file]["modified_time"]
        os.utime(file, (mod_time, mod_time))
        # set file index
        await self._file_mgr.update_file_index(file, {
            "status": FileStatus.ADDED
        })

    async def request_index_handler(self, writer: StreamWriter, client_index: dict):
        client_ip = writer.get_extra_info("peername")[0]
        # response with local index
        local_index = pickle.dumps(self._file_mgr.file_index)
        writer.write(int.to_bytes(MsgType.RES_INDEX.value, 1, "big"))
        writer.write(int.to_bytes(len(local_index), 8, "big"))
        writer.write(local_index)
        await writer.drain()
        writer.close()
        await self.sync(client_index, client_ip)

    async def sync(self, client_index: dict, client_ip: str):
        # compare file index
        new_folders = list()
        new_files = list()
        modified_files = list()
        for path, info in client_index.items():
            if path not in self._file_mgr.file_index:
                if info["is_file"]:  # peer has new file
                    new_files.append((path, info))
                else:  # peer has new folder
                    new_folders.append(path)
            elif info["is_file"] and info["modified_time"] > self._file_mgr.file_index[path]["modified_time"]:
                if info["size"] == self._file_mgr.file_index[path]["size"]:  # peer has modified file
                    index = list()
                    for i in range(len(info["hash"])):
                        if info["hash"][i] != self._file_mgr.file_index[path]["hash"][i]:
                            index.append(i)
                    modified_files.append((path, info, index))
                else:  # treat as new file
                    new_files.append((path, info))
        await self.sync_new_folder(new_folders)  # make new folders
        asyncio.get_event_loop().create_task(self.sync_new_file(new_files, client_ip))  # request missing files
        asyncio.get_event_loop().create_task(
            self.sync_modified_file(modified_files, client_ip))  # request modified files

    async def sync_new_folder(self, folders: list):
        for path in folders:
            print(f"Creating directory {path}")
            # create local folder
            Path(path).mkdir(parents=True, exist_ok=True)
            # add index
            await self._file_mgr.update_file_index(path, {"is_file": False})

    async def sync_new_file(self, files: list, client_ip: str):
        for path, info in files:
            # create empty file
            with open(path, "wb+") as f:
                f.truncate(info["size"])
            # add index
            await self._file_mgr.update_file_index(path, {
                "is_file": True,
                "size": info["size"],
                "modified_time": info["modified_time"],
                "status": FileStatus.WRITING,
                "hash": info["hash"]
            })
            for i in range(len(info["hash"])):
                await self._peer_mgr.request_file(client_ip, path, i, config.file_block_size)

    async def sync_modified_file(self, files: list, client_ip: str):
        for path, info, index in files:
            # update index
            await self._file_mgr.update_file_index(path, {
                "modified_time": info["modified_time"],
                "status": FileStatus.WRITING,
                "hash": info["hash"]
            })
            for i in index:
                await self._peer_mgr.request_file(client_ip, path, i, config.file_block_size)

    async def request_index_update_handler(self, writer: StreamWriter, client_index: dict):
        client_ip = writer.get_extra_info("peername")[0]
        # response
        data = b"OK"
        writer.write(int.to_bytes(MsgType.RES_INDEX_UPDATE.value, 1, "big"))
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        await writer.drain()
        writer.close()
        await self.sync(client_index, client_ip)

    async def request_file_handler(self, writer: StreamWriter, file_path: str, block_index: int):
        with open(file_path, mode="r+b") as f:
            f.seek(block_index * config.file_block_size)
            data = f.read(config.file_block_size)
        if config.enable_gzip:
            data = zlib.compress(data)
        writer.write(int.to_bytes(MsgType.RES_FILE.value, 1, "big"))
        writer.write(int.to_bytes(len(data), 8, "big"))
        writer.write(data)
        await writer.drain()
        writer.close()
