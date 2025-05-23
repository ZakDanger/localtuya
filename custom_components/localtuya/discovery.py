"""Discovery module for Tuya devices.

Entirely based on tuya-convert.py from tuya-convert:

https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py
"""
import asyncio
import json
import logging
from hashlib import md5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

DEFAULT_TIMEOUT = 6.0


def decrypt_udp(message):
    """Decrypt encrypted UDP broadcasts."""

    def _unpad(data):
        return data[: -ord(data[len(data) - 1 :])]

    cipher = Cipher(algorithms.AES(UDP_KEY), modes.ECB(), default_backend())
    decryptor = cipher.decryptor()
    return _unpad(decryptor.update(message) + decryptor.finalize()).decode()


class TuyaDiscovery(asyncio.DatagramProtocol):
    """Datagram handler listening for Tuya broadcast messages."""

    def __init__(self, callback=None):
        """Initialize a new BaseDiscovery."""
        self.devices = {}
        self._listeners = []
        self._callback = callback

    async def start(self):
        """Start discovery by listening to broadcasts."""
        loop = asyncio.get_running_loop()
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666), reuse_port=True
        )
        encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6667), reuse_port=True
        )

        self._listeners = await asyncio.gather(listener, encrypted_listener)
        _LOGGER.debug("Listening to broadcasts on UDP port 6666 and 6667")

    def close(self):
        """Stop discovery."""
        self._callback = None
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        """Handle received broadcast message."""
        data = data[20:-8]
        try:
            data = decrypt_udp(data)
        except Exception:  # pylint: disable=broad-except
            data = data.decode()

        decoded = json.loads(data)
        self.device_found(decoded)

    def device_found(self, device):
        """Discover a new device."""
        if device.get("gwId") not in self.devices:
            self.devices[device.get("gwId")] = device
            _LOGGER.debug("Discovered device: %s", device)

        if self._callback:
            self._callback(device)
    
    def load_from_file(self, fn="localtuya-discovery.json"):
        """Load devices from config file."""
        _LOGGER.info("TuyaDiscovery.load_from_file(%s)", fn)
        with open(fn, "rt", encoding="utf8") as f:
            _LOGGER.info("TuyaDiscovery.load_from_file() opened file ok")
            data = f.read()
            #_LOGGER.info("TuyaDiscovery.load_from_file() read data as %s", data)
            decoded = json.loads(data)
            _LOGGER.info("TuyaDiscovery.load_from_file() decoded data as %s", decoded)
            for device in decoded:
                _LOGGER.info("TuyaDiscovery.load_from_file() found device %s", device)
                self.device_found(device)
        _LOGGER.info("TuyaDiscovery.load_from_file(%s) DONE", fn)

# discover devices for 6 seconds
# then return those devices
async def discover():
    """Discover and return devices on local network."""
    discovery = TuyaDiscovery()
    try:
        await discovery.start()
        await asyncio.sleep(DEFAULT_TIMEOUT)
    finally:
        discovery.close()
    discovery.load_from_file()
    return discovery.devices
