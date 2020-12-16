from pathlib import Path


class FileMgr:
    event_listeners = {
        "on_file_change": None
    }

    def __init__(self, working_dir: Path):
        pass