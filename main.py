#!/usr/bin/env python3
#
# Simple BlueZ D-Bus BLE GATT server example
#
# Requirements:
#   - bluez >= 5.42 (with experimental features enabled for some APIs)
#   - python3-dbus
#
# This script:
#   - Registers a GATT service 12345678-1234-5678-1234-56789abcdef0
#   - With one characteristic 12345678-1234-5678-1234-56789abcdef1
#   - Responds to Read/Write requests over BLE
#

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'

DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

MAIN_LOOP = None


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 implementation
    """

    def __init__(self, bus):
        self.path = '/example/app'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE,
                         out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        managed_objects = {}
        for service in self.services:
            managed_objects[service.get_path()] = service.get_properties()
            for chrc in service.get_characteristics():
                managed_objects[chrc.get_path()] = chrc.get_properties()
                for desc in chrc.get_descriptors():
                    managed_objects[desc.get_path()] = desc.get_properties()
        return managed_objects


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 implementation
    """

    def __init__(self, bus, index, uuid, primary):
        self.path = f'/example/service{index}'
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    [chrc.get_path() for chrc in self.characteristics],
                    signature='o'
                ),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristics(self):
        return self.characteristics


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 implementation
    """

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.get_path() + f'/char{index}'
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

class NotifyCharacteristic(Characteristic):
    """
    Notify/read characteristic used by the app as charlongUUID
    """

    def __init__(self, bus, index, uuid, service):
        # supports read + notify
        Characteristic.__init__(self, bus, index, uuid,
                                ['read', 'notify'], service)
        self.value = b"Initial notification"
        self.notifying = False
        self._notify_source_id = None

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

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        if self.notifying:
            return

        print("NotifyCharacteristic StartNotify")
        self.notifying = True

        # send one immediately
        self._notify()
        # and then every second
        self._notify_source_id = GLib.timeout_add(1000, self._notify)

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        if not self.notifying:
            return

        print("NotifyCharacteristic StopNotify")
        self.notifying = False

        if self._notify_source_id is not None:
            GLib.source_remove(self._notify_source_id)
            self._notify_source_id = None

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        print("NotifyCharacteristic ReadValue")
        return dbus.ByteArray(self.value)

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


class Advertisement(dbus.service.Object):
    """
    org.bluez.LEAdvertisement1 implementation
    """

    PATH_BASE = '/example/advertisement'

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


class ExampleAdvertisement(Advertisement):
    """
    Advertises the custom ExampleService UUID so scanners can discover it.
    """

    def __init__(self, bus, index=0, local_name="ExampleGATT"):
        super().__init__(bus, index, advertising_type='peripheral')
        self.add_service_uuid(ExampleService.EXAMPLE_SVC_UUID)
        self.include_tx_power = True
        self.local_name = local_name


def find_adapter(bus):
    obj = bus.get_object(BLUEZ_SERVICE_NAME, "/")
    om = dbus.Interface(obj, DBUS_OM_IFACE)
    objects = om.GetManagedObjects()
    for path, interfaces in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in interfaces and GATT_MANAGER_IFACE in interfaces:
            return path
    return None


def log_active_services(app):
    print("Active GATT services and characteristics:")
    for service in app.services:
        print(f"  Service {service.uuid} at {service.get_path()}")
        for chrc in service.get_characteristics():
            flags = ",".join(chrc.flags)
            print(f"    Characteristic {chrc.uuid} ({flags}) at {chrc.get_path()}")
            for desc in chrc.get_descriptors():
                desc_uuid = getattr(desc, "uuid", "<unknown>")
                print(f"      Descriptor {desc_uuid} at {desc.get_path()}")


def make_register_app_cb(app):
    def _cb():
        print("GATT application registered")
        log_active_services(app)
    return _cb


def register_ad_cb():
    print("Advertisement registered (service UUID will appear in scan results)")


def register_ad_error_cb(error):
    print(f"Failed to register advertisement: {error}")
    if MAIN_LOOP:
        MAIN_LOOP.quit()


def unregister_advertisement(manager, advertisement):
    try:
        manager.UnregisterAdvertisement(advertisement.get_path())
        print("Advertisement unregistered")
    except Exception as exc:
        print(f"Warning: failed to unregister advertisement: {exc}")


def register_app_error_cb(error):
    print(f"Failed to register application: {error}")
    MAIN_LOOP.quit()


def main():
    global MAIN_LOOP

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print("BLE adapter with GATT Manager not found")
        return

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        GATT_MANAGER_IFACE
    )
    advertising_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        LE_ADVERTISING_MANAGER_IFACE
    )

    app = Application(bus)
    app.add_service(ExampleService(bus, 0))

    advertisement = ExampleAdvertisement(bus, 0)

    MAIN_LOOP = GLib.MainLoop()

    print("Registering GATT application...")
    service_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=make_register_app_cb(app),
        error_handler=register_app_error_cb
    )

    print("Registering advertisement...")
    advertising_manager.RegisterAdvertisement(
        advertisement.get_path(), {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb
    )

    try:
        MAIN_LOOP.run()
    except KeyboardInterrupt:
        print("GATT server stopped")
    finally:
        unregister_advertisement(advertising_manager, advertisement)


if __name__ == '__main__':
    main()
