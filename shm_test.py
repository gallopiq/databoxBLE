#!/usr/bin/env python3
from shm_read import ShmRead
import time

shm = ShmRead()

while(True):
    shm.update_data()
    print(shm.get_state())
    time.sleep(1)