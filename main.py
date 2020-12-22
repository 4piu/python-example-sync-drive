import sys
import traceback

import config
from sync_drive.App import App


def main():
    try:
        # parse args
        ips: list = sys.argv[sys.argv.index("--ip") + 1].split(",")
        encryption: bool = "--encryption" in sys.argv and sys.argv[sys.argv.index("--encryption") + 1].lower() in [
            "yes", "y", "true", "on"]
        # start main app loop
        app = App(peer_ips=ips, working_dir="./share", encryption=encryption, psk=config.pre_shared_key)
        app.run()
    except:
        traceback.print_exc()
        print("\nUsage example: main.py --ip 192.168.1.101,192.168.1.102 --encryption yes")


if __name__ == '__main__':
    main()
