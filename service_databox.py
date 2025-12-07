import dbus

from definitions import *
from uuidDataboxStateChar import DataboxStateCharacteristic
from uuidDataboxTimeChar import DataboxTimeCharacteristic
from uuidDataboxMeasureChar import DataboxMeasureCharacteristic
from characteristic import Advertisement

from service import Service

class DataboxService(Service):
    """
    Custom service containing:
      - DATABOX_STATE_CHRC_UUID: read/write
      - DATABOX_STATE_NOTIFY_UUID: read/notify
    """

    DATABOX_SERVICE_UUID = 'e68de724-46d7-49eb-8635-0f6762da8957'
    
    DATABOX_STATE_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11738'
    DATABOX_TIME_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11739'
    DATABOX_MEASURE_UUID = 'f6dd9ec5-281f-4ad3-a1b3-c2957ad11740'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.DATABOX_SERVICE_UUID, True)
        self.add_characteristic(DataboxStateCharacteristic(bus, "state", self.DATABOX_STATE_UUID, self))
        self.add_characteristic(DataboxTimeCharacteristic(bus, "time", self.DATABOX_TIME_UUID, self))
        self.add_characteristic(DataboxMeasureCharacteristic(bus, "measure", self.DATABOX_MEASURE_UUID, self))

        

class DataboxAdvertisement(Advertisement):
    """
    Advertises the custom ExampleService UUID so scanners can discover it.
    """

    def __init__(self, bus, index=0):
        super().__init__(bus, index, advertising_type='peripheral')
        self.add_service_uuid(DataboxService.DATABOX_SERVICE_UUID)
        self.include_tx_power = True
        self.local_name = "CalvaraDev"
        with open("/etc/gallopiq/databox_sn", "r") as file:
            self.local_name = f"Calvara{file.read()}"