#!/bin/bash
# Set up the door sensor on a Raspberry Pi (Raspberry Pi OS / Debian).
# Run as root from the checkout in /home/tuerstatus/spaceapi:
#   sudo ./misc/install-sensor.sh
set -euo pipefail

USER_NAME="tuerstatus"
HOME_DIR="/home/${USER_NAME}"
REPO_DIR="${HOME_DIR}/spaceapi"
NTP_SERVER="ntp0.fau.de"

if [ "$(id -u)" != 0 ]; then
	echo "[!] Please run as root (sudo)" 1>&2
	exit 1
fi

if [ "$(cd "$(dirname "${0}")/.." && pwd)" != "${REPO_DIR}" ]; then
	echo "[!] The repository has to be checked out in ${REPO_DIR}" 1>&2
	exit 1
fi

# dependencies: the sensor only uses the "update" action, so no matplotlib
apt-get update
apt-get install -y gpiod python3-requests python3-dateutil unattended-upgrades

# dedicated user with access to the GPIO pins
id "${USER_NAME}" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "${USER_NAME}"
usermod -aG gpio "${USER_NAME}"
chown -R "${USER_NAME}:" "${REPO_DIR}"

# HMAC key, has to be identical to the key of the server
if [ ! -e "${HOME_DIR}/door.key" ]; then
	install -m 600 -o "${USER_NAME}" -g "${USER_NAME}" "${REPO_DIR}/misc/door.key.example" "${HOME_DIR}/door.key"
	echo "[!] Put the real key into ${HOME_DIR}/door.key" 1>&2
fi

# ramdisk for the success marker, has to be writable by the sensor user
mkdir -p /mnt/ramdisk
sed -i '\# /mnt/ramdisk #d' /etc/fstab
echo "tmpfs /mnt/ramdisk tmpfs defaults,noexec,nosuid,nodev,size=1m,uid=${USER_NAME},gid=${USER_NAME},mode=0755 0 0" >> /etc/fstab
systemctl daemon-reload
mountpoint -q /mnt/ramdisk || mount /mnt/ramdisk

# NTP: the Pi has no RTC
mkdir -p /etc/systemd/timesyncd.conf.d
printf '[Time]\nNTP=%s\n' "${NTP_SERVER}" > /etc/systemd/timesyncd.conf.d/fau.conf
systemctl restart systemd-timesyncd

# automatic updates: Raspbian has no separate security suite, so take all updates of the release
# (and of the Raspberry Pi archive for kernel and firmware), reboot at night if needed
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
cat > /etc/apt/apt.conf.d/51fablab-unattended-upgrades <<'EOF'
// installed by spaceapi/misc/install-sensor.sh
Unattended-Upgrade::Origins-Pattern {
	"origin=Raspbian,codename=${distro_codename},label=Raspbian";
	"origin=Raspberry Pi Foundation,codename=${distro_codename},label=Raspberry Pi Foundation";
};
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
EOF

# timer
install -m 644 "${REPO_DIR}"/misc/update_doorstate.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now update_doorstate.timer
systemctl list-timers update_doorstate.timer --no-pager
