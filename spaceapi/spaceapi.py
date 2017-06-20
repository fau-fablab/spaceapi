#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small script to serve the SpaceAPI JSON API."""

import hmac
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy

from lib_doorstate import (DoorState, calculate_hmac, human_time_since,
                           parse_args)

WEBSITE_URL = 'https://fablab.fau.de/'
ADDRESS = 'Raum U1.239\nErwin-Rommel-Straße 60\n91058 Erlangen\nGermany'
LAT = 49.574
LON = 11.03
OPEN_URL = 'https://fablab.fau.de/spaceapi/static/logo_open.png'
CLOSED_URL = 'https://fablab.fau.de/spaceapi/static/logo_closed.png'
PHONE = '+49 9131 85 28013'

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
APP = Flask(__name__)
APP.config['SQLALCHEMY_DATABASE_URI'] = ARGS.sql
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(APP)


class DoorStateEntry(DB.Model):
    """A door state changed entry in the database."""

    __tablename__ = 'doorstate'
    time = DB.Column(DB.DateTime(), primary_key=True)
    state = DB.Column(DB.Enum(DoorState), nullable=False)

    def __init__(self, time, state):
        self.time = time
        self.state = state

    def __repr__(self):
        return 'DoorStateEntry({}, {})'.format(self.time, self.state)

    @property
    def timestamp(self):
        """Return the integer timestamp of this entry."""
        return int(self.time.timestamp())

    def to_dict(self):
        """Return a json serializable dict for this entry."""
        return {
            'state': self.state.name,
            'time': self.timestamp,
        }

    @classmethod
    def get_latest_state(cls):
        """Return the most up to date entry."""
        return DoorStateEntry.query.order_by(DB.desc(cls.time)).first()


@APP.route('/')
def spaceapi():
    """
    Return the SpaceAPI JSON (spaceapi.net).

    This one is valid for version 0.8, 0.9, 0.11-0.13.
    """
    latest_door_state = DoorStateEntry.get_latest_state()
    open = latest_door_state is not None and latest_door_state.state == DoorState.open
    state_last_change = latest_door_state.timestamp if latest_door_state else 0
    state_message = 'you can call us, maybe someone is here'

    return jsonify({
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
    })


@APP.route('/door/', methods=('GET', ))
def get_doorstate():
    """Return the current door state."""
    latest_door_state = DoorStateEntry.get_latest_state()
    if not latest_door_state:
        text = 'Keine aktuellen Informationen über den Türstatus vorhanden.'
    elif latest_door_state.state == DoorState.closed and \
            latest_door_state.time.day != datetime.today().day:
        text = 'Das FabLab war heute noch nicht geöffnet.'
    elif latest_door_state.state == DoorState.closed:
        text = 'Das FabLab war zuletzt vor {} geöffnet.'.format(
            human_time_since(latest_door_state.time)
        )
    elif latest_door_state.state == DoorState.open:
        text = 'Die FabLab-Tür ist seit {} offen.'.format(
            human_time_since(latest_door_state.time)
        )
    return jsonify({
        'state': latest_door_state.state.name if latest_door_state else 'unknown',
        'time': latest_door_state.timestamp if latest_door_state else 0,
        'text': text,
    })


@APP.route('/door/', methods=('POST', ))
def update_doorstate():
    """Update doorstate (open, close, ...)."""
    required_params = {'time', 'state', 'hmac'}

    data = request.json or request.form

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
        latest_door_state = DoorStateEntry.get_latest_state()
        if latest_door_state and latest_door_state.state == state:
            raise ValueError('state', 'Door is already {}'.format(state))
    except ValueError as err:
        abort(400, {err.args[0]: err.args[1]})

    # update doorstate
    new_entry = DoorStateEntry(time=time, state=state)
    APP.logger.debug('Updating door state: %(time)i: %(state)s', new_entry.to_dict())
    DB.session.add(new_entry)
    DB.session.commit()

    return jsonify(new_entry.to_dict())


@APP.route('/door/all/', methods=('GET', ))
def get_all_doorstate():
    """Return the current door state."""
    try:
        time_from = datetime.fromtimestamp(int(
            request.args.get(
                'from',
                (datetime.now() - timedelta(days=365)).timestamp(),
            )
        ))
        time_to = datetime.fromtimestamp(int(
            request.args.get(
                'to',
                datetime.now().timestamp(),
            )
        ))
    except ValueError:
        abort(400, 'From and to have to be timestamps')

    all_entries = DoorStateEntry.query.order_by(
        DB.asc(DoorStateEntry.time)
    ).filter(
        DoorStateEntry.time >= time_from, DoorStateEntry.time <= time_to,
    )
    return jsonify([entry.to_dict() for entry in all_entries])


@APP.errorhandler(400)
@APP.errorhandler(404)
@APP.errorhandler(405)
@APP.errorhandler(500)
def error(error):
    """JSON encode error messages."""
    return jsonify({
        'error_code': error.code,
        'error_name': error.name,
        'error_description': error.description,
    }), error.code



if __name__ == '__main__':
    DB.create_all()
    APP.run(host=ARGS.host, port=ARGS.port, debug=ARGS.debug)
