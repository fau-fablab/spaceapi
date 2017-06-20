#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small script to serve the SpaceAPI JSON API."""

import argparse
import hmac
from datetime import date, datetime, timedelta
from time import sleep

from flask import Flask, abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

from lib_doorstate import (DoorState, add_debug_arg, add_host_arg, add_key_arg,
                           add_port_arg, add_sql_arg, calculate_hmac,
                           human_time_since, parse_args_and_read_key,
                           utc_to_local)

WEBSITE_URL = 'https://fablab.fau.de/'
ADDRESS = 'Raum U1.239\nErwin-Rommel-Straße 60\n91058 Erlangen\nGermany'
LAT = 49.574
LON = 11.03
OPEN_URL = 'https://fablab.fau.de/spaceapi/static/logo_open.png'
CLOSED_URL = 'https://fablab.fau.de/spaceapi/static/logo_closed.png'
PHONE = '+49 9131 85 28013'


def parse_args():
    """Return parsed command line arguments."""
    parser = argparse.ArgumentParser(__doc__)

    add_debug_arg(parser)
    add_key_arg(parser)
    add_host_arg(parser)
    add_port_arg(parser)
    add_sql_arg(parser)

    return parse_args_and_read_key(parser)


ARGS = parse_args()
APP = Flask(__name__)
APP.config['SQLALCHEMY_DATABASE_URI'] = ARGS.sql
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(APP)


class DoorStateEntry(DB.Model):
    """A door state changed entry in the database."""

    __tablename__ = 'doorstate'
    time = DB.Column(DB.DateTime(), primary_key=True, index=True, default=datetime.utcnow)
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
    is_open = latest_door_state is not None and latest_door_state.state == DoorState.open
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
        'open': is_open,
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
            'open': is_open,
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
            utc_to_local(latest_door_state.time).date() != date.today():
        # date.today is local tz
        text = 'Das FabLab war heute noch nicht geöffnet.'
    elif latest_door_state.state == DoorState.closed:
        text = 'Das FabLab war zuletzt vor {} geöffnet.'.format(
            human_time_since(latest_door_state.time)  # everything UTC
        )
    elif latest_door_state.state == DoorState.open:
        text = 'Die FabLab-Tür ist seit {} offen.'.format(
            human_time_since(latest_door_state.time)  # everything UTC
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
        time = datetime.fromtimestamp(int(data['time']))  # data['time'] is UTC
        if abs(time - datetime.utcnow()).total_seconds() > 60:
            raise ValueError('time', 'Time is too far in the future or past. Use NTP and UTC!')
        if data['state'] not in DoorState.__members__:
            raise ValueError(
                'state',
                'State has to be one of {}.'.format(
                    ', '.join(DoorStateEntry.__members__.keys())
                )
            )
        state = DoorState[data['state']]
        latest_door_state = DoorStateEntry.get_latest_state()
        if latest_door_state:
            if latest_door_state.state == state:
                raise ValueError('state', 'Door is already {}'.format(state.name))
            elif latest_door_state.timestamp >= time.timestamp():
                raise ValueError('time', 'New entry must be newer than latest entry.')
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
                (datetime.utcnow() - timedelta(days=365)).timestamp(),
            )
        ))  # from and fallback are both UTC
        time_to = datetime.fromtimestamp(int(
            request.args.get(
                'to',
                datetime.utcnow().timestamp(),
            )
        ))  # to and fallback are both UTC
    except ValueError:
        abort(400, 'From and to have to be timestamps')

    all_entries = DoorStateEntry.query.order_by(
        DB.asc(DoorStateEntry.time)
    ).filter(
        DoorStateEntry.time >= time_from, DoorStateEntry.time <= time_to,
    ).limit(2000).all()
    return jsonify([entry.to_dict() for entry in all_entries])


@APP.errorhandler(400)
@APP.errorhandler(404)
@APP.errorhandler(405)
@APP.errorhandler(500)
def errorhandler(error):
    """JSON encode error messages."""
    return jsonify({
        'error_code': error.code,
        'error_name': error.name,
        'error_description': error.description,
    }), error.code


if __name__ == '__main__':
    # try 10 times to connect to database then fail
    DB_CONNECTION_RETRIES = 20
    for retry in range(1, DB_CONNECTION_RETRIES + 1):
        try:
            DB.create_all()
            break
        except OperationalError as err:
            APP.logger.error(
                'Failed to connect to database: Try %i of %i', retry, DB_CONNECTION_RETRIES
            )
            if retry == DB_CONNECTION_RETRIES:
                raise err
            sleep(1)
    APP.run(host=ARGS.host, port=ARGS.port, debug=ARGS.debug)
