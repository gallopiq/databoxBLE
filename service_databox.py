import dbus
from definitions import *
from characteristic import Characteristic, NotifyCharacteristic, Advertisement

from service import Service

class DataboxCharacteristic(Characteristic):
    """
    Simple read/write characteristic
    """

    def __init__(self, bus, index, uuid, service):
        Characteristic.__init__(self, bus, index, uuid,
                                ['read', 'write'], service)
        self.value = b"Hello BLE"

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        print("DataboxCharacteristic ReadValue")
        return dbus.ByteArray(self.value)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print(f"DataboxCharacteristic WriteValue: {bytes(value)}")
        self.value = bytes(value)

        
class DataboxNotificationChar(NotifyCharacteristic):
    def __init__(self, bus, index, uuid, service):
        super().__init__(bus, index, uuid, service)
        self.value=0
    
    def _notify(self):
        """
        Called periodically by GLib.timeout_add to push notifications.
        """
        if not self.notifying:
            return False  # stop the timeout

        print(f"NotifyCharacteristic sending notification {self.value}")
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {'Value': dbus.ByteArray(self.value)},
            []
        )
        self.value=self.value+1
        return True  # keep the timeout running


class DataboxService(Service):
    """
    Custom service containing:
      - DATABOX_CHRC_UUID: read/write
      - DATABOX_NOTIFY_CHRC_UUID: read/notify
    """

    DATABOX_SVC_UUID = 'e68de724-46d7-49eb-8635-0f6762da8957'
    DATABOX_CHRC_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11737'
    DATABOX_NOTIFY_CHRC_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11738'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.DATABOX_SVC_UUID, True)

        # characteristic used by read_char() in your app
        self.add_characteristic(
            DataboxCharacteristic(bus, 0, self.DATABOX_CHRC_UUID, self)
        )

        # characteristic used by startNotifications(..., charlongUUID, ...)
        self.add_characteristic(
            DataboxNotificationChar(bus, 1, self.DATABOX_NOTIFY_CHRC_UUID, self)
        )
        

class DataboxAdvertisement(Advertisement):
    """
    Advertises the custom ExampleService UUID so scanners can discover it.
    """

    def __init__(self, bus, index=0, local_name="DataboxGATT"):
        super().__init__(bus, index, advertising_type='peripheral')
        self.add_service_uuid(DataboxService.DATABOX_SVC_UUID)
        self.include_tx_power = True
        self.local_name = local_name