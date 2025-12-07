import dbus
import time
import struct
import threading
import socket

from characteristic import Characteristic
from definitions import *


def send_measure_stop(host='127.0.0.1', port=4242) -> str:
    with socket.create_connection((host, port)) as sock:
        sock.sendall(b'measure_stop\n')
        response = sock.recv(4096)  # Adjust size as needed
        return response.decode('utf-8')

def send_measure_start(host='127.0.0.1', port=4242) -> str:
    with socket.create_connection((host, port)) as sock:
        sock.sendall(b'measure_start\n')
        response = sock.recv(4096)  # Adjust size as needed
        return response.decode('utf-8')
    

class DataboxMeasureCharacteristic(Characteristic):

    
    TIME_THRESHOLD = 120  # seconds (2 minutes)
    
    def __init__(self, bus, index, uuid, service):
        Characteristic.__init__(self, bus, index, uuid,
                                ['read', 'write'], service)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    
    def ReadValue(self, options):
        now = int(time.time())
        print(f"[TimeCharacteristic] ReadValue → {now}")

        # pack time_t (64-bit LE)
        data = struct.pack("<Q", now)
        return dbus.ByteArray(data)

    @dbus.service.method(GATT_CHRC_IFACE,in_signature='aya{sv}')
    def WriteValue(self, value, options):
        if bytes(value) == b"\xff\xff\xff\x01":
            threading.Thread(target=send_measure_start, daemon=True).start()
        if bytes(value) == b"\xff\xff\xff\x00":
            threading.Thread(target=send_measure_stop, daemon=True).start()
        return

