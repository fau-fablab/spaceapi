# SpaceAPI

Our Implementation of the [SpaceAPI](http://spaceapi.net/).

## Server

Serve the [SpaceAPI](http://spaceapi.net/) and some door API end nodes.

### Installation:

```sh
pip3 install --upgrade -r ./requirements-server.txt
```

### Usage:

```
usage: Small script to serve the SpaceAPI JSON API. [-h] [--debug] --key KEY [--host HOST] [--port PORT] [--sql SQL]

optional arguments:
  -h, --help   show this help message and exit
  --debug      Enable debug output
  --key KEY    Path to HMAC key file
  --host HOST  Host to listen on (default 0.0.0.0)
  --port PORT  Port to listen on (default 8888)
  --sql SQL    SQL connection string
```

### Example:

```sh
./spaceapi/spaceapi.py --key /etc/machine-id --host 0.0.0.0 --port 1337 --debug --sql "mysql+pymysql://user:password@host/database"
```

Notes:

- for usage with MySQL you need a MySQL driver like
  [`PyMySQL`](http://docs.sqlalchemy.org/en/latest/dialects/mysql.html#module-sqlalchemy.dialects.mysql.pymysql) installed.
- it is tested with SQLite3 and MySQL but may work with other SQL databases, too. See http://docs.sqlalchemy.org/en/latest/dialects/
- default driver is `sqlite3` with database `sqlite:///:memory:` (does not persists during restarts of the server)
- You can also make *some* configurations for the server script in `/etc/spaceapi.py` or as
  environment variable
  - the config file syntax is a key value py file syntax
  - you can't configure the key there (for reasons)
  - example environment variables: `SPACEAPI_SQL="sqlite:///db.db"`, `SPACEAPI_HOST="0.0.0.0"`
  - example config file:
```py
SQL = "sqlite:///db.db"
HOST = "192.168.1.1"
```

### HMAC key

The HMAC key is a shared secret: the server and every client that updates the door state
(e.g. the door sensor Pi) must use the same key file.

In production the key is stored on the server at `brain.fablab.fau.de:/mnt/secrets/spaceapi/key`.
[brain-docker-config](https://github.com/fau-fablab/brain-docker-config) mounts that directory into the
server container (`spaceapi.add_volume(secrets_prefix + "/spaceapi/", ...)` in `kastenwesen_config.py`),
and the `Dockerfile` starts the server with `--key /mnt/secrets/spaceapi/key`.

## Client

Can update entries of SpaceAPI server and plot opening hour graphs.

### Installation:

```sh
pip3 install --upgrade -r ./requirements-client.txt
```

### Usage:

```
usage: Client script to update the doorstate on our website or to make plots. [-h] {update,plot} ...

optional arguments:
  -h, --help     show this help message and exit

actions:
  {update,plot}
    update       update door state
    plot         Plot history
```

```
usage: Client script to update the doorstate on our website or to make plots. update
       [-h] [--debug] [--url URL] --key KEY [--time TIME] --state {opened,closed}

optional arguments:
  -h, --help            show this help message and exit
  --debug               Enable debug output
  --url URL             URL to API endpoint
  --key KEY             Path to HMAC key file
  --time TIME           Timestamp since state changed (default now)
  --state {opened,closed}
                        New state
```

```
usage: Client script to update the doorstate on our website or to make plots. plot
       [-h] [--url URL] [--debug] --plot-type {by-hour,by-week} --out OUT

optional arguments:
  -h, --help            show this help message and exit
  --url URL             URL to API endpoint
  --debug               Enable debug output
  --plot-type {by-hour,by-week}
                        The type of the graph to plot
  --out OUT             The file to write the image
```

### Example:

```sh
./spaceapi/doorstate_client.py update --key /etc/machine-id --url http://127.0.0.1:1337/spaceapi/door/ --debug --state open
./spaceapi/doorstate_client.py plot --url http://127.0.0.1:1337/spaceapi/door/all/ --debug --plot-type by-hour --out image.png
```

Notes:

- Only data from within 365 days and at most 2000 entries will be used for plotting

![example by hour plot](./example_by_hour_plot.png)

![example by week plot](./example_by_week_plot.png)

## Installation on Raspberry Pi

We have a Raspberry Pi to query the door state using GPIO pins.
It is located on top of the display shelf next to the door to the FSV room.
It uses the script `misc/update-status.sh`.
Connect 3V3 and GPIO17 to the sensor, and add a 10k resistor from GPIO17 to GND.
While not required, adding a 1k resistor before GPIO17 is recommended.
It acts as a failsafe, protecting the RPi in case of configuration problems.
The script reads the pin with `gpioget` from libgpiod, so it also works on current
Raspberry Pi OS (Debian 13 "trixie"), where the old sysfs GPIO interface is gone.
`DOORSTATE_INVERTED` in the script is `true` for our sensor, where the pin reads 1 while the door is closed
(check with `gpioget -c gpiochip0 --numeric 17`). Set it to `false` if your sensor reads 0 when closed.

Setup: check out this repository in `/home/tuerstatus/spaceapi` and run the install script:

```sh
sudo git clone https://github.com/fau-fablab/spaceapi.git /home/tuerstatus/spaceapi
sudo /home/tuerstatus/spaceapi/misc/install-sensor.sh
```

It installs `gpiod`, `python3-requests` and `python3-dateutil` (the sensor does not need
matplotlib), creates the user `tuerstatus` in the `gpio` group, adds `/home/tuerstatus/door.key`
from `misc/door.key.example`, mounts a tmpfs on
`/mnt/ramdisk` for the success marker `tuerstatus.success`, sets the NTP server to `ntp0.fau.de`
(the Pi has no RTC) and enables the timer.

Afterwards replace the placeholder in `/home/tuerstatus/door.key` with the shared secret of the
server (see [HMAC key](#hmac-key)), e.g. by copying `brain.fablab.fau.de:/mnt/secrets/spaceapi/key`.
Until then the server rejects the updates of the sensor.

The script is run every minute by the systemd timer in `misc/`.

## Embed on Website

We embed the door state information provided by `/spaceapi/door/` on our WordPress website using
the widget in https://github.com/fau-fablab/wp-fau-fablab-mods/

## License

[GPLv3](LICENSE)
