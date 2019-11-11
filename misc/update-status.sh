#!/bin/bash
set +e

cd "$(dirname "${0}")"

KEY="$HOME/door.key"

# crontab doesn't set $USER, so use $UID for checking
# 1001 = tuerstatus
DOORSTATE_USER="1001"

# invert logic?
# false: switch closed = door closed
# true: switch open = door closed 
DOORSTATE_INVERTED="true"

if [ "${UID}" != "${DOORSTATE_USER}" ]; then
	echo "[!] Please run this script as user ID ${DOORSTATE_USER}" 1>&2
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

	if [ $(cat /sys/class/gpio/gpio2/value) == 0 ]; then
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
#  check if more than 7 times out of 10 the result is "opened"
if [ $n -gt 7 ]; then
	update_status "opened"
else
	update_status "closed"
fi

