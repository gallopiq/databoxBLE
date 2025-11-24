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


class ExampleService(Service):
    """
    Example custom service containing one characteristic
    """

    EXAMPLE_SVC_UUID = '12345678-1234-5678-1234-56789abcdef0'
    EXAMPLE_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef1'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.EXAMPLE_SVC_UUID, True)
        self.add_characteristic(
            ExampleCharacteristic(bus, 0, self.EXAMPLE_CHRC_UUID, self)
        )


def find_adapter(bus):
    obj = bus.get_object(BLUEZ_SERVICE_NAME, "/")
    om = dbus.Interface(obj, DBUS_OM_IFACE)
    objects = om.GetManagedObjects()
    for path, interfaces in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in interfaces and GATT_MANAGER_IFACE in interfaces:
            return path
    return None


def register_app_cb():
    print("GATT application registered")


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

    app = Application(bus)
    app.add_service(ExampleService(bus, 0))

    MAIN_LOOP = GLib.MainLoop()

    print("Registering GATT application...")
    service_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb
    )

    try:
        MAIN_LOOP.run()
    except KeyboardInterrupt:
        print("GATT server stopped")


if __name__ == '__main__':
    main()
