#!/bin/bash
set +e

cd "$(dirname "${0}")"

###
# configuration
###

KEY="$HOME/door.key"

DOORSTATE_USER="tuerstatus"

# GPIO input pin that reads from the sensor
GPIO_IN_PIN="2"

# invert logic?
# false: switch closed = door closed
# true: switch open = door closed 
DOORSTATE_INVERTED="true"

# GPIO output pin. Set to 0 to disable (for example, if sensor is connected to 3V3)
GPIO_OUT_PIN="27"
# What value should be set on the output pin (ignored if $OUT_GPIO_PIN is 0)
GPIO_OUT_VALUE="0"

###
# script
###

if [ "${USER}" != "${DOORSTATE_USER}" ]; then
	echo "[!] Please run this script as user ${DOORSTATE_USER}" 1>&2
	exit 1
fi

if $DOORSTATE_INVERTED; then
	RETURN_SWITCH_OPEN="0"
	RETURN_SWITCH_CLOSED="1"
else
	RETURN_SWITCH_OPEN="1"
	RETURN_SWITCH_CLOSED="0"
fi
RETURN_ERROR="0"

function update_status() {
	../spaceapi/doorstate_client.py update --key "${KEY}" --state "${1}"
	touch /mnt/ramdisk/tuerstatus.success
}

# is door open?
# echo "1" if open, "0" otherwise
# return 0 on error
function is_open() {
	sleep 1

	if [ $(cat /sys/class/gpio/gpio$GPIO_IN_PIN/value) == 0 ]; then
		echo "${RETURN_SWITCH_CLOSED}"
		return 0
	else
		echo "${RETURN_SWITCH_OPEN}"
		return 0
	fi
	# error
	echo "${RETURN_ERROR}"
	return 1
}

# retry ten times
n=0
for i in `seq 0 9`; do
	n=$(($n + $(is_open)))
done

# check if more than 7 times out of 10 the result is "opened"
if [ $n -gt 7 ]; then
	update_status "opened"
else
	update_status "closed"
fi

