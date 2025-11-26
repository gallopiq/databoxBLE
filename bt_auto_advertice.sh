#!/usr/bin/env bash
# Initialize Bluetooth and start LE advertising

bluetoothctl << EOF
advertise off
power off
EOF

sleep 0.1

bluetoothctl << EOF
power on
agent NoInputOutput
default-agent
pairable on
discoverable on
EOF


sleep 0.1
