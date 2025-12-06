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

import time
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib


from service_databox import DataboxService, DataboxAdvertisement

from definitions import *

MAIN_LOOP = None


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 implementation
    """

    def __init__(self, bus):
        self.path = '/databox/app'
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
    app.add_service(DataboxService(bus, 0))

    advertisement = DataboxAdvertisement(bus, 0)

    MAIN_LOOP = GLib.MainLoop()

    print("Registering advertisement FIRST...")
    advertising_manager.RegisterAdvertisement(
        advertisement.get_path(),
        {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb
    )

    # Critical: allow BlueZ to fully activate advertising
    time.sleep(0.3)

    print("Registering GATT application...")
    service_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=make_register_app_cb(app),
        error_handler=register_app_error_cb
    )

    try:
        MAIN_LOOP.run()
    except KeyboardInterrupt:
        print("GATT server stopped")
    finally:
        unregister_advertisement(advertising_manager, advertisement)


if __name__ == '__main__':
    main()
