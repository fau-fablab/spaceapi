# -*- coding: utf-8 -*-
"""Common things for doorstate client and server."""

import argparse
import hmac
from datetime import datetime
from enum import Enum


class DoorState(Enum):
    """Valid door state values."""
    open = 'open'
    closed = 'closed'


def parse_args(*extra_args):
    """Return parsed command line args."""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '--key',
        type=argparse.FileType(mode='rb'),
        required=True,
        help='Path to HMAC key file',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Enable debug output',
    )
    for arg_spec in extra_args:
        argument = arg_spec.pop('argument')
        parser.add_argument(argument, **arg_spec)

    # read key
    args = parser.parse_args()
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
    """
    diff = (time_to or datetime.now()) - time_from

    if diff.total_seconds() < 60:
        return "wenigen Sekunden"
    elif diff.total_seconds() < 60 * 2:
        return "einer Minute"
    elif diff.total_seconds() < 60 * 60:
        return "{} Minuten".format(diff.total_seconds() // 60)
    elif diff.total_seconds() < 60 * 60 * 2:
        return "einer Stunde"
    elif diff.total_seconds() < 60 * 60 * 24:
        return "{} Stunden".format(diff.total_seconds() // (60 * 60))
    elif diff.total_seconds() < 60 * 60 * 24 * 2:
        return "einem Tag"
    elif diff.total_seconds() < 60 * 60 * 24 * 7:
        return "{} Tagen".format(diff.total_seconds() // (60 * 60 * 24))
    elif diff.total_seconds() < 60 * 60 * 24 * 7 * 2:
        return "einer Woche"
    else:
        return "{} Wochen".format(diff.total_seconds() // (60 * 60 * 24 * 7))
