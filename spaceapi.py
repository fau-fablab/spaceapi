#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small script to serve the SpaceAPI JSON API."""

import hmac
from datetime import datetime

from bottle import get, post, request, response, run

from lib_doorstate import calculate_hmac, parse_args

VALID_DOOR_STATES = {'open', 'close'}
ARGS = None  # command line args


@get('/')
def spaceapi():
    return {}


@post('/update_doorstate/')
def update_doorstate():
    """Update doorstate (open, close, ...)."""
    required_params = {'time', 'state', 'hmac'}
    response.content_type = 'application/json'

    data = request.json or request.POST

    # validate
    try:
        for param in required_params:
            if not data.get(param, None):
                raise ValueError(param, 'Parameter is missing')
        if not hmac.compare_digest(
            calculate_hmac(data['time'], data['state'], ARGS.key),
            data['hmac']
           ):
            raise ValueError('hmac', 'HMAC digest is wrong. Do you have the right key?')
        if not data['time'].isnumeric():
            raise ValueError('time', 'Time has to be an integer timestamp.')
        time = int(data['time'])
        if abs(datetime.fromtimestamp(time) - datetime.now()).total_seconds() > 60:
            raise ValueError('time', 'Time is too far in the future or past. Use ntp!')
        if data['state'] not in VALID_DOOR_STATES:
            raise ValueError('state', 'State has to be one of {}.'.format(', '.join(VALID_DOOR_STATES)))
        state = data['state']
    except ValueError as err:
        response.status = 400
        return {err.args[0]: err.args[1]}

    # update doorstate
    # TODO

    return {'state': state, 'time': time}



if __name__ == '__main__':
    ARGS = parse_args(
        {
            'argument': '--host',
            'type': str,
            'default': '0.0.0.0',
            'help': 'Host to listen on (default 0.0.0.0)',
        },
        {
            'argument': '--port',
            'type': int,
            'default': 8888,
            'help': 'Port to listen on (default 8888)',
        },
    )
    run(host=ARGS.host, port=ARGS.port, debug=ARGS.debug)
