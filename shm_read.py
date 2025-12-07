import os
import mmap
import struct
import threading
import msgpack


def decode_header(raw):        
        
        (
            hb_sec, hb_usec,
            ts_sec, ts_usec,
            ms_sec, ms_usec,
            num_devices,
            diskspace_mb,
            diskspace_percent,
            bat_mv,
            usb_mV,
            bat_percent
        ) = ShmRead.ShmHeader.unpack(raw[:ShmRead.ShmHeader.size])

        return {
            "heartbeat":       (hb_sec, hb_usec),
            "shm_timestamp":   (ts_sec, ts_usec),
            "measure_start":   (ms_sec, ms_usec),
            "num_devices":     num_devices,
            "diskspace_mb":    diskspace_mb,
            "diskspace_percent": diskspace_percent,
            "usb_mV":          usb_mV,
            "bat_mv":          bat_mv,
            "bat_percent":     bat_percent,
        }


def decode_device_data(raw, offset):
    
    offset_bytes = ShmRead.ShmHeader.size + offset * ShmRead.ShmDevice.size
    (
        serial,
        online,
        measurement,
        x_min,
        x_max,
        y_min,
        y_max,
        z_min,
        z_max,
        n_missing_pkgs,
        bat_mV,
        usb_mV,
        rssi
    ) = ShmRead.ShmDevice.unpack(
        raw[offset_bytes:offset_bytes + ShmRead.ShmDevice.size]
    )

    return {
        "serial": serial,
        "online": online,
        "measurement": measurement,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "z_min": z_min,
        "z_max": z_max,
        "n_missing_pkgs": n_missing_pkgs,
        "bat_mV": bat_mV,
        "usb_mV": usb_mV,
        "rssi": rssi
    }

class ShmRead:
    SHM_ADDRESS = "gallopiq_shm"
    SHM_SIZE = 1024
    ShmHeader = struct.Struct("<qqqqqqBIBhhB")
    ShmDevice = struct.Struct("<I??hhhhhhIhhb")
    
    def __init__(self):
        self.path = f"/dev/shm/{self.SHM_ADDRESS}"
        self._lock = threading.Lock()
        self.databox = {}
        self.sensors = []
        self.packet = b"42"
        self.serial = self.get_databox_serial()

        self.fd = os.open(self.path, os.O_RDONLY)

        self.mm = mmap.mmap(
            self.fd,
            self.SHM_SIZE,
            access=mmap.ACCESS_READ
        )

    def get_bytes(self, n=SHM_SIZE):
        """Return first n bytes of the shared memory."""
        return self.mm[:n]
    
    def check_online_backend(self):        
        with open("/tmp/online.status", 'r') as f:
            state= f.read()        
            return state.startswith("Online")
        return False

    def get_databox_serial(self):        
        with open("/etc/gallopiq/databox_sn", 'r') as f:
            state = int(f.read())
            return state 
        return 0





    def encode_ble(self):
        # Prepare sensors list in msgpack-friendly structure
        sensors = []
        for i in range(self.databox['num_devices']):
            s = self.sensors[i]
            sensors.append({
                "serial": s['serial'],
                "online": bool(s['online']),
                "measurement": bool(s['measurement']),
                "bat_mV": int(s['bat_mV']),      # same conversion as before
                "usb_connected": s['usb_mV'] > 4300,
                "rssi": s['rssi'],
                "missing_pkgs": s['n_missing_pkgs'],
            })

        # Prepare top-level packet structure
        packet_dict = {
            "serial": self.serial,
            "measure_start": list(self.databox['measure_start']),
            "num_devices": self.databox['num_devices'],
            "diskspace_percent": self.databox['diskspace_percent'],
            "usb_connected": self.databox['usb_mV'] > 4300,
            "bat_mv": self.databox['bat_mv'],
            "online": self.databox['online'],
            "sensors": sensors,
        }

        # Encode using msgpack
        packet = msgpack.packb(packet_dict, use_bin_type=True)

        return packet

    def update_data(self):
        """Decode header + devices and update cached dicts atomically."""
        self.raw = self.get_bytes()

        databox = decode_header(self.raw)
        databox['online'] = self.check_online_backend()
        sensors = [
            decode_device_data(self.raw, i)
            for i in range(databox["num_devices"])
        ]

        with self._lock:
            self.databox = databox
            self.sensors = sensors
            self.packet = self.encode_ble()

    def get_state(self):
        """Return a snapshot of (databox, sensors) safely."""
        with self._lock:
            return dict(self.databox), list(self.sensors)
        
    def get_packet(self):
        return self.packet

    def close(self):
        self.mm.close()
        os.close(self.fd)
