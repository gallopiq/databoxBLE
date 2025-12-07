import dbus
import time
import struct
import subprocess


from characteristic import Characteristic
from definitions import *

class DataboxTimeCharacteristic(Characteristic):

    
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
        incoming = struct.unpack("<Q", bytes(value))[0]
        now = int(time.time())
        diff = incoming - now
        

        
        if abs(diff) <= self.TIME_THRESHOLD:
            print(f"[Time] Time not updated (|diff| <= {self.TIME_THRESHOLD}s).")
            return
        
        try:
            # `date -s @<timestamp>`
            subprocess.run(["sudo", "date", "-s", f"@{incoming}"], check=True)
            print("System time updated.")
            print(f"[Time] Old system time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}")
            print(f"[Time]   New timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(incoming))}")

        except Exception as e:
            print(f"Failed to set system time: {e}")
            return

        try:
            subprocess.run(
                ["sudo", "hwclock", "--systohc"],
                check=True
            )
            print("RTC updated from system time.")
        except Exception as e:
            print(f"Failed to update RTC: {e}")

        return

