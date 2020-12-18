from enum import Enum, auto
from io import BufferedRandom
from pathlib import Path
from typing import Callable

from numpy import array


class FileMgr:
    # class static vars
    file_index: array
    event_listener: dict

    def __init__(self, working_dir: Path):
        pass
        # init file index

    def run(self):
        pass
        # spawn file watcher

    def stop(self):
        pass
        # stop file watcher
        # stop file hash

    def set_event_listener(self, event: str, callback: Callable):
        pass

    async def scan_dir(self, dir: Path):
        pass
        # list content in dir
        # if file:
        # get file meta
        # add file to index
        # set file status to HASHING
        # calculate file hash
        # add hash to file index
        # set file status to ADDED
        # if dir:
        # add dir to file index
        # call self

    async def file_change_handler(self, file: Path, last_modified: int):
        pass
        # update last_modified
        # call event listener

    async def get_file_handler(self, file: Path, mode: str) -> BufferedRandom:
        pass
        # if node is write:
        # set file status to WRITING
        # return file handler

    async def complete_write_file(self, file: Path):
        pass
        # set file status to ADDED

    # new proc
    def file_watcher(self, on_file_change: Callable):
        pass
        # copy file_index to reference var
        # loop:
        # scan dir
        # compare array
        # for each difference, invoke callback

    @staticmethod
    async def get_file_meta(file: Path) -> tuple:
        pass
        # return file size and last modification time

    # new proc
    @staticmethod
    def calc_file_hash(file: Path, blk_begin: int, blk_end: int) -> bytes:
        pass
        # return file block md5


class FileStatus(Enum):
    ADDED = auto()
    HASHING = auto()
    WRITING = auto()
