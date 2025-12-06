import dbus


from characteristic import Characteristic
from definitions import *

class DataboxTimeCharacteristic(Characteristic):
    """
    Simple read/write characteristic
    """

    def __init__(self, bus, index, uuid, service):
        Characteristic.__init__(self, bus, index, uuid,
                                ['read', 'write'], service)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    
    def ReadValue(self, options):
        print("read triggered")        
        return dbus.ByteArray(self.shm.get_packet())

    @dbus.service.method(GATT_CHRC_IFACE,in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print(f"Databox Time WriteValue: {value}")
        return

