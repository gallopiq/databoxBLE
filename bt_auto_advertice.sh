#!/usr/bin/env bash
# Initialize Bluetooth and start LE advertising
power_off() {
    bluetoothctl << EOF
advertise off
power off
EOF
    sleep 0.1
}

# Try up to 3 times with 0.5s delay if busy
power_on() {
    bluetoothctl << EOF
power on
default-agent
pairable on
discoverable on
EOF
    sleep 0.1
}


check_state() {
    out="$(bluetoothctl show)"
    echo "$out" | grep -q "Powered: yes"      || { echo "not Powered: yes"; return 1; }
    echo "$out" | grep -q "Discoverable: yes" || { echo "not Discoverable: yes"; return 1; }
    echo "Bluetooth state OK"
}


main() {
    for i in 1 2 3; do
        echo "main attempt $i"
        power_off
        sleep 0.1
        power_on
        sleep 0.1
        if check_state; then
            echo "main: success"
            return 0
        fi
        echo "main: retry $i"
        sleep 0.5
    done
    echo "main: failed after 3 attempts"
    return 1
}

main "$@"