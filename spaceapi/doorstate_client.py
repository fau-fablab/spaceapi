#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small client script to update the doorstate on our website."""

from datetime import datetime

import requests

from lib_doorstate import calculate_hmac, parse_args, DoorState

ARGS = None  # command line args


def update_doorstate(args):
    """Update doorstate (open, close, ...)."""
    resp = requests.post(args.url, data={
        'time': int(args.time),
        'state': args.state,
        'hmac': calculate_hmac(args.time, args.state, args.key)
    })
    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        print('Error', err.response.status_code)
        try:
            resp_json = resp.json()
            print(resp_json)
        except Exception:
            print(err)

        exit(1)

    resp_json = resp.json()
    if not 'time' in resp_json or not 'state' in resp_json:
        print("Invalid response from API:", resp_json)
    elif resp_json['time'] == args.time and resp_json['state'] == args.state:
        print('OK', args.time, args.state)
    else:
        print(
            'The API missunderstood our request. Sent:',
            args.time, args.state,
            'API response: ', resp_json['time'], resp_json['state']
        )



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
            'choices': DoorState.__members__.keys(),
            'required': True,
            'help': 'New state',
        },
    )
    update_doorstate(ARGS)
