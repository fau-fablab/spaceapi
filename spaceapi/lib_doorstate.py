# -*- coding: utf-8 -*-
"""Common things for doorstate client and server."""

import argparse
import hmac


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
    our_hmac = hmac.new(key)
    our_hmac.update('{}:{}'.format(time, state).encode('utf8'))
    return our_hmac.hexdigest()
