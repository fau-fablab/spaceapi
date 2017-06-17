#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small client script to update the doorstate on our website."""

from datetime import datetime

import requests

from lib_doorstate import calculate_hmac, parse_args

VALID_DOOR_STATES = {'open', 'close'}
ARGS = None  # command line args


def update_doorstate(args):
    """Update doorstate (open, close, ...)."""
    resp = requests.post(args.url, data={
        'time': args.time,
        'state': args.state,
        'hmac': calculate_hmac(args.time, args.state, args.key)
    })
    resp.raise_for_status()
    resp_json = resp.json()
    if resp_json['time'] == args.time and resp_json['state'] == args.state:
        print('OK')
    else:
        print('The API missunderstood our request.')



if __name__ == '__main__':
    ARGS = parse_args(
        {
            'argument': '--url',
            'type': str,
            'default': 'https://fablab.fau.de/spaceapi/update_doorstate/',
            'help': 'URL to API endpoint',
        },
        {
            'argument': '--time',
            'type': int,
            'default': int(datetime.now().timestamp()),
            'help': 'Timestamp since state changed (default now)',
        },
        {
            'argument': '--state',
            'type': str,
            'choices': VALID_DOOR_STATES,
            'required': True,
            'help': 'New state',
        },
    )
    update_doorstate(ARGS)
