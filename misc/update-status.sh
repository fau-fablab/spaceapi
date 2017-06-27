#!/bin/bash
set +e

cd "$(dirname "${0}")"

KEY="$HOME/door.key"
DOORSTATE_USER="tuerstatus"

if [ "${USER}" != "${DOORSTATE_USER}" ]; then
    echo "[!] Please run this script as user ${DOORSTATE_USER}" 1>&2
    exit 1
fi

function update_status() {
        ../spaceapi/doorstate_client.py update --key "${KEY}" --state "${1}"
        touch /mnt/ramdisk/tuerstatus.success
}

# Schauen ob die Türe offen ist
# Türe offen ==  Schalter von RX nach TX an ttyS0 geschlossen
# Ausgabe: Zahl (1=offen, 0=zu)
# Rückgabewert: 1 = Fehler, 0 = okay
function is_open() {
	{
		sleep 1
		# sende "MOEP", lese Antwort
		# read gibt den Prompt auf stderr aus, deshalb weiter unten die Umleitung von stderr und nicht von stdout
		read -t 1 -n4 -p "MOEP" ans || { echo "1"; return 0; }
		if [ "a$ans" == "aMOEP" ]; then
			# Antwort war MOEP -> Schalter  RX-TX  geschlossen
			echo "0"; return 0
		fi;
		#echo "Fehler beim Auslesen: Antwort war $ans" >&2;
		echo "0"
		return 1;
	} < /dev/ttyS0 2> /dev/ttyS0
}

# zehnmal auslesen, bei >7 mal keine Antwort gilt es als offen

n=0
for i in `seq 0 9`; do
	n=$(($n + `is_open`))
done
if [ $n -gt 7 ]; then
	update_status "opened"
else
	update_status "closed"
fi

