#! /bin/bash

set -e

IP=192.168.0.102
ssh $IP -t "mkdir -p ~/ble"
scp *.py $IP:~/ble
scp bt_auto_advertice.sh $IP:~/ble
# sudo systemctl disable G08_ble.service
ssh $IP -t "sudo systemctl stop G08_ble.service" || true
ssh $IP -t "sudo systemctl restart bluetooth"
ssh $IP -t "chmod +x ~/ble/bt_auto_advertice.sh"
ssh $IP -t "sudo ~/ble/bt_auto_advertice.sh"
ssh $IP -t "cd ~/ble && sudo python3 main.py"