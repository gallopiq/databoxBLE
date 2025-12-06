import dbus


import zlib
import struct
import threading
from collections import deque
from shm_read import ShmRead
from characteristic import NotifyCharacteristic
from definitions import *


class DataboxNotificationChar(NotifyCharacteristic):
    def __init__(self, bus, index, uuid, service):
        super().__init__(bus, index, uuid, service)
        self.shm = ShmRead()
        self.toSend=deque()
        self.dataid=0
        self.packets=[]
        self.set_interval(40)
    
    def _async_update(self):
        self.shm.update_data()
        self.set_data(self.shm.get_packet())
        self.StartNotify()

    @dbus.service.method(GATT_CHRC_IFACE,in_signature='aya{sv}')
    def WriteValue(self, value, options):
        if bytes(value) == b"\xff\xff\xff\xff":
            threading.Thread(target=self._async_update, daemon=True).start()
        return

    
    def set_data(self,data):
        self.split_into_packets(data)
    
    def get_paket_nr(self,section_id,packet_id):
        return section_id*256+packet_id
    
    def split_into_packets(self,data_blob, packet_size=100):
        self.packets = []
        self.dataid = self.dataid+1
        if(self.dataid>250):
            self.dataid=0
            # reserve 251-255
        
        # packet: 8 byte meta, then data
        # 0-3 uint32: CRC
        #  4  uint8: dataid
        # 5-6 uint16: section id
        # 7  uint8: paketid
        # 8 .... data
        section_id = 0
        paket_id = 1
        
        last_section = 0
        last_paket = 1
        
        crc_full = zlib.crc32(data_blob) & 0xFFFFFFFF        
        
        for i in range(0, len(data_blob), packet_size):
            chunk = bytearray()
            chunk += struct.pack('<B', self.dataid) # uint8
            chunk += struct.pack('<H', section_id) # uint16
            chunk += struct.pack('<B', paket_id) # uint8
            chunk += data_blob[i:i + packet_size]
            
            # Compute CRC32 of this chunk
            crc = zlib.crc32(chunk) & 0xFFFFFFFF            
            # Append CRC to the chunk (4 bytes)
            pLen =  2 + len(chunk) + 4
            packet =struct.pack('<H', pLen) +  chunk + crc.to_bytes(4, byteorder="little")
                    
            self.packets.append(packet)
            
            last_section = section_id
            last_paket = paket_id
            
            paket_id = paket_id+1
            if(paket_id>255):
                section_id = section_id+1
                paket_id =0
        
        chunk = bytearray()        
        chunk += struct.pack('<B', self.dataid) # uint8
        chunk += struct.pack('<H', 0) # uint16 section id 0
        chunk += struct.pack('<B', 0) # uint16 paket id 0
        chunk += struct.pack('<H', last_section) # uint16 last section
        chunk += struct.pack('<B', last_paket) # uint16 last paket
        chunk += crc_full.to_bytes(4, byteorder="little")
        crc = zlib.crc32(chunk) & 0xFFFFFFFF        
        pLen =  2 + len(chunk) + 4
        packet =struct.pack('<H', pLen) +  chunk + crc.to_bytes(4, byteorder="little")
        
        self.packets.insert(0, packet)        
        
        
        self.toSend = deque(range(len(self.packets)))
        # print(f"got {len(self.packets)} packets")
    
    
    def get_next_paket_to_send(self):
        if not self.toSend or len(self.toSend)<1:            
            return None
                
        idx = self.toSend.popleft()   # O(1)
        return self.packets[idx], idx
    
    
    def _notify(self):
        """
        Called periodically by GLib.timeout_add to push notifications.
        """
        result = self.get_next_paket_to_send()
        if result is None:
            # nothing to send anymore: stop notifications
            self.StopNotify()
            return False  # stop the timeout

        paket, idx = result
        # print(f"send packet {idx}")
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {'Value': dbus.ByteArray(paket)},
            []
        )
        return True  # keep the timeout running
