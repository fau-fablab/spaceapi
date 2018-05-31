#!/bin/bash
set +e

cd "$(dirname "${0}")"

KEY="$HOME/door.key"
DOORSTATE_USER="tuerstatus"
# invert logic?
# false: switch closed = door closed
# true: switch open = door closed 
DOORSTATE_INVERTED="true"

if [ "${USER}" != "${DOORSTATE_USER}" ]; then
    echo "[!] Please run this script as user ${DOORSTATE_USER}" 1>&2
    exit 1
fi

function update_status() {
        ../spaceapi/doorstate_client.py update --key "${KEY}" --state "${1}"
        touch /mnt/ramdisk/tuerstatus.success
}

# is door open?
# echo "1" if open, "0" otherwise
# return 1 on error
function is_open() {
	{
        if $DOORSTATE_INVERTED; then
            RETURN_SWITCH_OPEN="0"
            RETURN_SWITCH_CLOSED="1"
        else
            RETURN_SWITCH_OPEN="1"
            RETURN_SWITCH_CLOSED="0"
        fi
        RETURN_ERROR="0"
		sleep 1
		# send "MOEP", check response
		# read returns its prompt on stderr, therefore the redirect below.
		read -t 1 -n4 -p "MOEP" ans || { echo $RETURN_SWITCH_OPEN; return 0; }
		if [ "a$ans" == "aMOEP" ]; then
			# response is MOEP -- switch is closed
			echo $RETURN_SWITCH_CLOSED
			return 0
		fi;
		# error
		echo $RETURN_ERROR
		return 1;
	} < /dev/ttyS0 2> /dev/ttyS0
}

# retry ten times
n=0
for i in `seq 0 9`; do
	n=$(($n + `is_open`))
done
#  check if more than 7 times out of 10 the result is "opened"
if [ $n -gt 7 ]; then
	update_status "opened"
else
	update_status "closed"
fi

