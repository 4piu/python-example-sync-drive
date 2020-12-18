import threading
from pathlib import Path

from sync_drive.FileMgr import FileMgr
from sync_drive.PeerMgr import PeerMgr


class App(threading.Thread):
    running: bool = True
    _file_mgr: FileMgr
    _peer_mgr: PeerMgr

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._file_mgr = FileMgr(Path(kwargs["working_dir"]))
        self._peer_mgr = PeerMgr(kwargs["peer_ips"], encryption=kwargs["encryption"], psk=kwargs["psk"])

    def run(self) -> None:
        self._file_mgr.run()
        self._peer_mgr.run()
        while self.running:
            pass
        print("App stopped")

    def stop(self):
        print("\nStopping app")
        self._file_mgr.stop()
        self._peer_mgr.stop()
        self.running = False
