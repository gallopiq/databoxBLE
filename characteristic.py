import dbus

import dbus.service
from gi.repository import GLib
from definitions import *
from exceptions import *

class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 implementation
    """

    def __init__(self, bus, path, uuid, flags, service):
        self.path = service.get_path() + f'/{path}'
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': dbus.Array(self.flags, signature='s'),
                'Descriptors': dbus.Array(
                    [desc.get_path() for desc in self.descriptors],
                    signature='o'
                ),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='ss',
                         out_signature='v')
    def Get(self, interface, prop):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        props = self.get_properties()[GATT_CHRC_IFACE]
        if prop not in props:
            raise InvalidArgsException()
        return props[prop]

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='ssv')
    def Set(self, interface, name, value):
        # Not implemented
        raise NotSupportedException()

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        print("Default ReadValue called")
        return dbus.Array([], signature='y')

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print("Default WriteValue called")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print("StartNotify not implemented")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print("StopNotify not implemented")
        raise NotSupportedException()



class NotifyCharacteristic(Characteristic):
    """
    Notify/read characteristic used by the app as charlongUUID
    """

    def __init__(self, bus, index, uuid, service):
        # supports read + notify
        Characteristic.__init__(self, bus, index, uuid,
                                ['write', 'notify'], service)
        self.value = b"Initial notification"
        self.notifying = False
        self._notify_source_id = None
        self.interval_ms=1000

    def _notify(self):
        """
        Called periodically by GLib.timeout_add to push notifications.
        """
        if not self.notifying:
            return False  # stop the timeout

        print("NotifyCharacteristic sending notification")
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {'Value': dbus.ByteArray(self.value)},
            []
        )
        return True  # keep the timeout running

    def set_interval(self,interval_ms):
        self.interval_ms=interval_ms


    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        if self.notifying:
            return

        # print("NotifyCharacteristic StartNotify")
        self.notifying = True

        # send one immediately
        self._notify()
        # and then every second
        self._notify_source_id = GLib.timeout_add(self.interval_ms, self._notify)

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        if not self.notifying:
            return

        # print("NotifyCharacteristic StopNotify")
        self.notifying = False

        if self._notify_source_id is not None:
            GLib.source_remove(self._notify_source_id)
            self._notify_source_id = None

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        # print("NotifyCharacteristic ReadValue")
        return dbus.ByteArray(self.value)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        # print("Default WriteValue called")
        raise NotSupportedException()

class Advertisement(dbus.service.Object):
    """
    org.bluez.LEAdvertisement1 implementation
    """

    PATH_BASE = '/databox/advertisement'

    def __init__(self, bus, index, advertising_type='peripheral'):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = []
        self.manufacturer_data = {}
        self.solicit_uuids = []
        self.service_data = {}
        self.local_name = None
        self.include_tx_power = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties[LE_ADVERTISEMENT_IFACE] = {
            'Type': self.ad_type,
            'ServiceUUIDs': dbus.Array(self.service_uuids, signature='s'),
            'SolicitUUIDs': dbus.Array(self.solicit_uuids, signature='s'),
            'ManufacturerData': dbus.Dictionary(self.manufacturer_data, signature='qv'),
            'ServiceData': dbus.Dictionary(self.service_data, signature='sv'),
            'IncludeTxPower': self.include_tx_power,
            'MinInterval': dbus.UInt32(0x00100),
            'MaxInterval': dbus.UInt32(0x00200),
        }

        if self.local_name:
            properties[LE_ADVERTISEMENT_IFACE]['LocalName'] = self.local_name

        return properties

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        self.service_data[uuid] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='ss',
                         out_signature='v')
    def Get(self, interface, prop):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()

        properties = self.get_properties()[LE_ADVERTISEMENT_IFACE]
        if prop not in properties:
            raise InvalidArgsException()
        return properties[prop]

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE)
    def Release(self):
        print(f"{self.path}: Released")