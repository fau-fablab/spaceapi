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
       [-h] [--debug] [--url URL] --key KEY [--time TIME] --state {open,closed}

optional arguments:
  -h, --help            show this help message and exit
  --debug               Enable debug output
  --url URL             URL to API endpoint
  --key KEY             Path to HMAC key file
  --time TIME           UTC timestamp since state changed (default now)
  --state {open,closed}
                        New state
```

```
usage: Client script to update the doorstate on our website or to make plots. plot
       [-h] [--url URL] [--debug] --plot-type {by-week,by-hour} --out OUT

optional arguments:
  -h, --help            show this help message and exit
  --url URL             URL to API endpoint
  --debug               Enable debug output
  --plot-type {by-week,by-hour}
                        The type of the graph to plot
  --out OUT             The file to write the image
```

### Example:

```sh
./spaceapi/doorstate_client.py update --key /etc/machine-id --url http://127.0.0.1:1337/door/ --debug --state open
./spaceapi/doorstate_client.py plot --url http://127.0.0.1:1337/door/all/ --debug --plot-type by-hour --out image.png
```

Notes:

- Only data from within 365 days and at most 2000 entries will be used for plotting

![example by hour plot](./example_by_hour_plot.png)

![example by week plot](./example_by_week_plot.png)

## License

[GPLv3](LICENSE)
