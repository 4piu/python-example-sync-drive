class PeerMgr:
    peers: list
    encryption: bool
    psk: bytes

    def __init__(self, peers: list, encryption: bool = False, psk: bytes = None):
        self.peers = peers
        self.encryption = encryption
        self.psk = psk
