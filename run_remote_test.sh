#! /bin/bash

set -e

IP=192.168.0.100
ssh $IP -t "mkdir -p ~/ble"
scp *.py $IP:~/ble
ssh $IP -t "cd ~/ble && sudo python3 shm_test.py"