#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small script to serve the SpaceAPI JSON API."""

import hmac
import json
import os
from datetime import datetime

from bottle import (
    HTTP_CODES, error, get, post, request, response, run, static_file
)

from lib_doorstate import calculate_hmac, parse_args

VALID_DOOR_STATES = {'open', 'close'}
ARGS = None  # command line args


@get('/')
def spaceapi():
    URL = 'https://fablab.fau.de/'
    ADDRESS = 'Raum U1.239\nErwin-Rommel-Straße 60\n91058 Erlangen\nGermany'
    LAT = 49.574
    LON = 11.03
    OPEN_URL = 'https://fablab.fau.de/spaceapi/static/logo_open.png'
    CLOSED_URL = 'https://fablab.fau.de/spaceapi/static/logo_closed.png'
    PHONE = '+49 9131 85 28013'
    open = False  # TODO
    state_last_change = 1497711681  # TODO
    state_message = 'you can call us, maybe someone is here'

    # TODO add compatibility with older space api versions

    return {
        'api': '0.13',
        'space': 'FAU FabLab',
        'logo': URL + 'spaceapi/static/logo_transparentbg.png',
        'url': URL,
        'address': ADDRESS,
        'lat': LAT,
        'lon': LON,
        'open': open,
        'status': state_message,
        'lastchange': state_last_change,
        'phone': PHONE,
        'location': {
            'address': ADDRESS,
            'lat': LAT,
            'lon': LON,
        },
        'spacefed': {
            'spacenet': False,
            'spacesaml': False,
            'spacephone': False,
        },
        'state': {
            'lastchange': state_last_change,
            'open': open,
            'message': state_message,
            'icon': {
                'open': OPEN_URL,
                'closed': CLOSED_URL,
            },
        },
        'cache': {
            'schedule': "m.05",
        },
        'projects': {
            '0': URL + 'project/',
            '1': "https://github.com/fau-fablab/",
        },
        'issue_report_channels': {
            '0': "twitter",
            '1': "ml",
        },
        'contact': {
            'phone': PHONE,
            'twitter': "@FAUFabLab",
            'ml': "fablab-aktive@fablab.fau.de",
            'facebook': "FAUFabLab",
            'google': {
                'plus': "+FAUFabLabErlangen",
            },
        },
        'icon': {
            'open': OPEN_URL,
            'closed': CLOSED_URL,
        }
    }


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
    print(state, time)

    return {'state': state, 'time': time}


@get('/static/<filename>')
def server_static(filename):
    return static_file(filename, root=os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../static/',
    ))


@error(404)
@error(405)
@error(500)
def error404(error):
    response.content_type = 'application/json'
    return json.dumps({
        'error_code': error.status_code,
        'error_message': HTTP_CODES[error.status_code],
    })



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
