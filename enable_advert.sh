#!/usr/bin/env bash
# Initialize Bluetooth and start LE advertising

bluetoothctl << EOF
advertise off
power off
power on
agent NoInputOutput
default-agent
pairable on
discoverable on
EOF