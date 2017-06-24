# -*- coding: utf-8 -*-
"""Common things for doorstate client and server."""

import argparse
import hmac
from datetime import datetime
from enum import Enum

import requests
from dateutil import tz


class DoorState(Enum):
    """Valid door state values."""

    opened = 'opened'
    closed = 'closed'


def to_timestamp(time):
    """Return time as integer timestamp."""
    return int(time.timestamp())


def add_key_arg(parser):
    """Add the --key argument to an argparser."""
    parser.add_argument(
        '--key',
        type=argparse.FileType(mode='rb'),
        required=True,
        help='Path to HMAC key file',
    )


def add_debug_arg(parser):
    """Add the --debug argument to an argparser."""
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Enable debug output',
    )


def add_url_arg(parser, default):
    """Add the --url argument to an argparser."""
    parser.add_argument(
        '--url',
        type=str,
        default=default,
        help='URL to API endpoint',
    )


def add_time_arg(parser):
    """Add the --time argument to an argparser."""
    parser.add_argument(
        '--time',
        type=int,
        default=to_timestamp(datetime.utcnow()),
        help='UTC timestamp since state changed (default now)',
    )


def add_outfile_arg(parser):
    """Add the --out argument to an argparser."""
    parser.add_argument(
        '--out',
        type=argparse.FileType(mode='wb'),
        required=True,
        help='The file to write the image',
    )


def add_plot_type_arg(parser):
    """Add the --plot-type argument to an argparser."""
    parser.add_argument(
        '--plot-type',
        type=str,
        choices={'by-week', 'by-hour'},
        required=True,
        help='The type of the graph to plot',
    )


def add_state_arg(parser):
    """Add the --state argument to an parser."""
    parser.add_argument(
        '--state',
        type=str,
        choices=DoorState.__members__.keys(),
        required=True,
        help='New state',
    )


def add_host_arg(parser):
    """Add the --host argument to an parser."""
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to listen on (default 0.0.0.0)',
    )


def add_port_arg(parser):
    """Add the --port argument to an parser."""
    parser.add_argument(
        '--port',
        type=int,
        default=8888,
        help='Port to listen on (default 8888)',
    )


def add_sql_arg(parser):
    """Add the --sql argument to an parser."""
    parser.add_argument(
        '--sql',
        type=str,
        default='sqlite:///:memory:',
        help='SQL connection string',
    )


def parse_args_and_read_key(parser):
    """Run ArgumentParser.parse_args and read the --key file."""
    args = parser.parse_args()
    if hasattr(args, 'key'):
        args.key = args.key.read().strip()
        if not args.key:
            raise ValueError('The key file is empty')

    return args


def calculate_hmac(time, state, key):
    """Return the hexdigest of the hmac of 'time:state' with key."""
    our_hmac = hmac.new(key, digestmod='md5')
    our_hmac.update('{}:{}'.format(time, state).encode('utf8'))
    return our_hmac.hexdigest()


def human_time_since(time_from, time_to=None):
    """
    Return a german human readable string to describe the duration since time.

    The text fits in a phrase like "Das FabLab war vor ... geöffnet"
    Param time_from: beginning of the time delta in UTC
    Param time_to: end of the time delta in UTC
    """
    diff = (time_to or datetime.utcnow()) - time_from

    if diff.total_seconds() < 60:
        return "wenigen Sekunden"
    elif diff.total_seconds() < 60 * 2:
        return "einer Minute"
    elif diff.total_seconds() < 60 * 60:
        return "{} Minuten".format(int(diff.total_seconds() // 60))
    elif diff.total_seconds() < 60 * 60 * 2:
        return "einer Stunde"
    elif diff.total_seconds() < 60 * 60 * 24:
        return "{} Stunden".format(int(diff.total_seconds() // (60 * 60)))
    elif diff.total_seconds() < 60 * 60 * 24 * 2:
        return "einem Tag"
    elif diff.total_seconds() < 60 * 60 * 24 * 7:
        return "{} Tagen".format(int(diff.total_seconds() // (60 * 60 * 24)))
    elif diff.total_seconds() < 60 * 60 * 24 * 7 * 2:
        return "einer Woche"
    else:
        return "{} Wochen".format(int(diff.total_seconds() // (60 * 60 * 24 * 7)))


def utc_to_local(time):
    """Convert a utc or naive date(time) object to local timezone."""
    if time.tzinfo is not None and time.tzinfo != tz.tzlocal():
        raise ValueError('Time is neither naive nor utc but {}.'.format(time.tzname()))

    return time.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())


def json_response_error_handling(response):
    """Return the response json of a request after error handling."""
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        print('Error', err.response.status_code)
        try:
            response_json = response.json()
            print(response_json)
        except Exception:
            print(err)

        exit(1)

    return response.json()
