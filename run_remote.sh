#! /bin/bash

set -e

IP=192.168.0.101
ssh $IP -t "mkdir -p ~/ble"
scp *.py $IP:~/ble
scp enable_advert.sh $IP:~/ble
# sudo systemctl disable G08_ble.service
ssh $IP -t "sudo systemctl stop G08_ble.service" || true
ssh $IP -t "chmod +x ~/ble/enable_advert.sh"
ssh $IP -t "sudo ~/ble/enable_advert.sh"
ssh $IP -t "cd ~/ble && sudo python3 main.py"