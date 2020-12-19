import asyncio
import hashlib
from enum import Enum, auto
from multiprocessing import Pool
from pathlib import Path
from typing import Callable


class FileStatus(Enum):
    ADDED = auto()
    HASHING = auto()
    WRITING = auto()


class FileMgr:
    _proc_pool: Pool
    _working_dir: Path
    _file_block_size: int
    _event_listener: dict
    _file_index: dict

    def __init__(self, working_dir: Path, file_block_size: int):
        self._event_listener = {
            "on_file_change": None
        }
        # init file index
        self._file_index = dict()
        self._proc_pool = Pool()
        self._working_dir = working_dir
        self._file_block_size = file_block_size

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._scan_dir())  # build index
        loop.create_task(self._scan_change())
        print("File watcher started")

    def stop(self):
        # stop file hash task
        self._proc_pool.close()
        self._proc_pool.terminate()
        self._proc_pool.join()

    def set_event_listener(self, event: str, callback: Callable):
        self._event_listener[event] = callback

    async def _scan_dir(self):
        # list content in dir
        for item in self._working_dir.rglob("*"):
            if item.is_dir():
                # add dir to index
                self._file_index[str(item)] = {
                    "is_file": False
                }
            elif item.is_file():
                # add file to index
                self._file_index[str(item)] = {
                    "is_file": True,
                    "size": item.stat().st_size,
                    "modified_time": item.stat().st_mtime,
                    "status": FileStatus.HASHING
                }
                # hash file (don't wait)
                asyncio.get_event_loop().create_task(self._hash_file(item))

    async def _hash_file(self, file: Path):
        def split_number(number: int, size: int) -> list:
            ret = list()
            if number <= size:
                ret.append((0, number))
            else:
                i = 0
                while i < number:
                    i_next = i + size - 1 if i + size - 1 < number else number
                    ret.append((i, i_next))
                    i = i_next + 1
            return ret

        # calculate file hash
        args = list()
        for blk in split_number(file.stat().st_size, self._file_block_size):
            args.append((file, blk[0], blk[1]))
        # add hash to file index
        self._file_index[str(file)].update({
            "hash": self._proc_pool.starmap(get_file_hash, args),
            "status": FileStatus.ADDED
        })

    async def set_file_status(self, file: Path, status: FileStatus):
        self._file_index[str(file)]["status"] = status

    async def _scan_change(self):
        while True:
            for item in self._working_dir.rglob("*"):
                flag = False
                path = str(item)
                # compare index
                if path not in self._file_index.keys():  # new item
                    print(f"Found new item: {path}")
                    flag = True
                    if item.is_file():
                        self._file_index[path] = {
                            "is_file": True,
                            "size": item.stat().st_size,
                            "modified_time": item.stat().st_mtime,
                            "status": FileStatus.HASHING
                        }
                    elif item.is_dir():
                        self._file_index[path] = {
                            "is_file": False
                        }
                else:
                    local = self._file_index[path]
                    if local["is_file"] and local["status"] != FileStatus.WRITING and local[
                        "modified_time"] < item.stat().st_mtime:  # modified item
                        print(f"Found modified item: {path}")
                        flag = True
                        local.update({
                            "status": FileStatus.HASHING,
                            "size": item.stat().st_size,
                            "modified_time": item.stat().st_mtime
                        })
                        # hash file (don't wait)
                        asyncio.get_event_loop().create_task(self._hash_file(item))
                # invoke callback if item changed
                if flag and self._event_listener["on_file_change"]:
                    asyncio.get_event_loop().create_task(self._event_listener["on_file_change"](item))
            await asyncio.sleep(.1)


# multi proc
def get_file_hash(file: Path, blk_begin: int, blk_end: int) -> bytes:
    with open(file, "rb") as f:
        f.seek(blk_begin)
        return hashlib.md5(f.read(blk_end - blk_begin + 1)).digest()
