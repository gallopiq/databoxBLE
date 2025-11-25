import dbus
from definitions import *
from characteristic import Characteristic, NotifyCharacteristic, Advertisement

from service import Service

class ExampleCharacteristic(Characteristic):
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
        print("ExampleCharacteristic ReadValue")
        return dbus.ByteArray(self.value)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print(f"ExampleCharacteristic WriteValue: {bytes(value)}")
        self.value = bytes(value)


class ExampleService(Service):
    """
    Custom service containing:
      - EXAMPLE_CHRC_UUID: read/write
      - EXAMPLE_NOTIFY_CHRC_UUID: read/notify
    """

    EXAMPLE_SVC_UUID = 'e68de724-46d7-49eb-8635-0f6762da8957'
    EXAMPLE_CHRC_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11737'
    EXAMPLE_NOTIFY_CHRC_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11738'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.EXAMPLE_SVC_UUID, True)

        # characteristic used by read_char() in your app
        self.add_characteristic(
            ExampleCharacteristic(bus, 0, self.EXAMPLE_CHRC_UUID, self)
        )

        # characteristic used by startNotifications(..., charlongUUID, ...)
        self.add_characteristic(
            NotifyCharacteristic(bus, 1, self.EXAMPLE_NOTIFY_CHRC_UUID, self)
        )

class ExampleAdvertisement(Advertisement):
    """
    Advertises the custom ExampleService UUID so scanners can discover it.
    """

    def __init__(self, bus, index=0, local_name="ExampleGATT"):
        super().__init__(bus, index, advertising_type='peripheral')
        self.add_service_uuid(ExampleService.EXAMPLE_SVC_UUID)
        self.include_tx_power = True
        self.local_name = local_name