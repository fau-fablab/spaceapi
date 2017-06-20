#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small script to serve the SpaceAPI JSON API."""

import hmac
import os
from datetime import datetime

from bottle import (HTTP_CODES, error, get, install, json_dumps, post, request,
                    response, run, static_file)
from sqlalchemy import Column, DateTime, Enum, create_engine, desc
from sqlalchemy.ext.declarative import declarative_base

from bottle.ext import sqlalchemy
from lib_doorstate import DoorState, calculate_hmac, parse_args

WEBSITE_URL = 'https://fablab.fau.de/'
ADDRESS = 'Raum U1.239\nErwin-Rommel-Straße 60\n91058 Erlangen\nGermany'
LAT = 49.574
LON = 11.03
OPEN_URL = 'https://fablab.fau.de/spaceapi/static/logo_open.png'
CLOSED_URL = 'https://fablab.fau.de/spaceapi/static/logo_closed.png'
PHONE = '+49 9131 85 28013'

ARGS = None  # command line args

Base = declarative_base()


class DoorStateEntry(Base):
    """A door state changed entry in the database."""

    __tablename__ = 'doorstate'
    time = Column(DateTime(), primary_key=True)
    state = Column(Enum(DoorState), nullable=False)

    def __init__(self, time, state):
        self.time = time
        self.state = state

    def __repr__(self):
        return 'DoorStateEntry({}, {})'.format(self.time, self.state)

    @classmethod
    def get_latest_state(cls, db_connection):
        """Return the most up to date entry."""
        return db_connection.query(cls).order_by(desc(cls.time)).first()


@get('/')
def spaceapi(db):
    """
    Return the SpaceAPI JSON (spaceapi.net).

    This one is valid for version 0.8, 0.9, 0.11-0.13.
    """
    latest_door_state = DoorStateEntry.get_latest_state(db)
    open = latest_door_state is not None and latest_door_state.state == DoorState.open
    state_last_change = int(latest_door_state.time.timestamp()) if latest_door_state else 0
    state_message = 'you can call us, maybe someone is here'

    return {
        'api': '0.13',
        'space': 'FAU FabLab',
        'logo': WEBSITE_URL + 'spaceapi/static/logo_transparentbg.png',
        'url': WEBSITE_URL,
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
        'projects': [
            WEBSITE_URL + 'project/',
            "https://github.com/fau-fablab/",
        ],
        'issue_report_channels': [
            "twitter",
            "ml",
        ],
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
def update_doorstate(db):
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
        time = datetime.fromtimestamp(int(data['time']))
        if abs(time - datetime.now()).total_seconds() > 60:
            raise ValueError('time', 'Time is too far in the future or past. Use ntp!')
        if data['state'] not in DoorState.__members__:
            raise ValueError(
                'state',
                'State has to be one of {}.'.format(
                    ', '.join(DoorStateEntry.__members__.keys())
                )
            )
        state = DoorState[data['state']]
        latest_door_state = DoorStateEntry.get_latest_state(db)
        print(latest_door_state)
        if latest_door_state and latest_door_state.state == state:
            raise ValueError('state', 'Door is already {}'.format(state))
    except ValueError as err:
        response.status = 400
        return {err.args[0]: err.args[1]}

    # update doorstate
    db.add(DoorStateEntry(time=time, state=state))

    return {'state': state.name, 'time': int(time.timestamp())}


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
    return json_dumps({
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
        {
            'argument': '--sql',
            'type': str,
            'default': 'sqlite:///:memory:',
            'help': 'SQL connection string',
        },
    )
    install(sqlalchemy.Plugin(
        create_engine(ARGS.sql, echo=ARGS.debug),
        Base.metadata,
        create=True,
        commit=True,
    ))
    run(host=ARGS.host, port=ARGS.port, debug=ARGS.debug)
