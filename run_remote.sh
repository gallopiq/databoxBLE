#! /bin/bash

set -e

IP=192.168.0.100
ssh $IP -t "mkdir -p ~/ble"
scp *.py $IP:~/ble
# sudo systemctl disable G08_ble.service
ssh $IP -t "sudo systemctl stop G08_ble.service" || true
ssh $IP -t "cd ~/ble && sudo python main.py"