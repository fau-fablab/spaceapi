#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small script to serve the SpaceAPI JSON API."""

import argparse
import hmac
from datetime import datetime, timedelta
from time import sleep

from dateutil.tz import tzlocal
from flask import Flask, abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

from lib_doorstate import (DoorState, add_debug_arg, add_host_arg, add_key_arg,
                           add_port_arg, add_sql_arg, calculate_hmac,
                           human_time_since, parse_args_and_read_key,
                           to_timestamp)

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


class OpeningPeriod(DB.Model):
    """An entry for a time duration when the FabLab door was opened."""

    __tablename__ = 'openingperiod'
    opened = DB.Column(DB.DateTime(timezone=True), primary_key=True, index=True, default=datetime.utcnow)
    closed = DB.Column(DB.DateTime(timezone=True), nullable=True)

    def __init__(self, opened, closed=None):
        self.opened = opened
        self.closed = closed

    def __repr__(self):
        return 'OpeningPeriod({}, {})'.format(self.opened, self.closed)

    @property
    def opened_timestamp(self):
        """Return the integer timestamp for the opened time of this entry."""
        return to_timestamp(self.opened)

    @property
    def closed_timestamp(self):
        """Return the integer timestamp for the closed time of this entry."""
        return to_timestamp(self.closed) if self.closed else None

    @property
    def is_open(self):
        """Return True if this entry has no closed entry."""
        return self.closed is None

    @property
    def state(self):
        """Return DoorState.opened if self.is_open else DoorState.closed."""
        return DoorState.opened if self.is_open else DoorState.closed

    @property
    def last_change_timestamp(self):
        """Return the timestamp of the last change of this entry."""
        return to_timestamp(self.opened if self.is_open else self.closed)

    def to_dict(self):
        """Return a json serializable dict for this entry."""
        return {
            'opened': self.opened_timestamp,
            'closed': self.closed_timestamp,
        }

    @classmethod
    def get_latest_state(cls):
        """Return the most up to date entry."""
        return OpeningPeriod.query.order_by(DB.desc(cls.opened)).first()


@APP.route('/')
def spaceapi():
    """
    Return the SpaceAPI JSON (spaceapi.net).

    This one is valid for version 0.8, 0.9, 0.11-0.13.
    """
    latest_door_state = OpeningPeriod.get_latest_state()
    is_open = latest_door_state is not None and latest_door_state.is_open
    state_last_change = (
        0 if not latest_door_state else latest_door_state.last_change_timestamp
    )
    state_message = 'door is open' if is_open else 'door is closed'

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
    latest_door_state = OpeningPeriod.get_latest_state()
    if not latest_door_state:
        text = 'Keine aktuellen Informationen über den Türstatus vorhanden.'
    elif not latest_door_state.is_open and \
            latest_door_state.closed.date() != datetime.now(tzlocal()).date():
        text = 'Das FabLab war heute noch nicht geöffnet.'
    elif not latest_door_state.is_open:
        text = 'Das FabLab war zuletzt vor {} geöffnet.'.format(
            human_time_since(latest_door_state.closed)
        )
    elif latest_door_state.is_open:
        text = 'Die FabLab-Tür ist seit {} offen.'.format(
            human_time_since(latest_door_state.opened)
        )
    return jsonify({
        'state': latest_door_state.state.name if latest_door_state else 'unknown',
        'time': latest_door_state.opened_timestamp if latest_door_state else 0,
        'text': text,
    })


@APP.route('/door/', methods=('POST', ))
def update_doorstate():
    """Update doorstate (opened, close, ...)."""
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
        time = datetime.fromtimestamp(int(data['time']), tzlocal())
        if abs(time - datetime.now(tzlocal())).total_seconds() > 60:
            raise ValueError('time', 'Time is too far in the future or past. Use NTP!')
        if data['state'] not in DoorState.__members__:
            raise ValueError(
                'state',
                'State has to be one of {}.'.format(
                    ', '.join(DoorState.__members__.keys())
                )
            )
        state = DoorState[data['state']]
        latest_door_state = OpeningPeriod.get_latest_state()
        if latest_door_state:
            if latest_door_state.state == state:
                raise ValueError('state', 'Door is already {}'.format(state.name))
            elif latest_door_state.last_change_timestamp >= to_timestamp(time):
                raise ValueError('time', 'New entry must be newer than latest entry.')
        elif state == DoorState.closed:
            raise ValueError('state', 'Door is already closed')
    except ValueError as err:
        abort(400, {err.args[0]: err.args[1]})

    # update doorstate
    if latest_door_state and latest_door_state.is_open and state == DoorState.closed:
        latest_door_state.closed = time
        APP.logger.debug('Closing door. Resulting entry: open from %(opened)i till %(closed)i', latest_door_state.to_dict())
    elif (not latest_door_state or not latest_door_state.is_open) and state == DoorState.opened:
        latest_door_state = OpeningPeriod(opened=time)
        APP.logger.debug('Opening door. New entry: open from %(opened)i till t.b.a.', latest_door_state.to_dict())
        DB.session.add(latest_door_state)
    else:
        abort(500, 'This should not happen')
    DB.session.commit()
    return jsonify({
        'time': latest_door_state.last_change_timestamp,
        'state': latest_door_state.state.name,
    })


@APP.route('/door/all/', methods=('GET', ))
def get_all_doorstate():
    """Return the current door state. Filter by opened time using from and to."""
    try:
        time_from = datetime.fromtimestamp(int(
            request.args.get(
                'from',
                (datetime.now(tzlocal()) - timedelta(days=365)).timestamp(),
            )
        ), tzlocal())
        time_to = datetime.fromtimestamp(int(
            request.args.get(
                'to',
                datetime.now(tzlocal()).timestamp(),
            )
        ), tzlocal())
    except ValueError:
        abort(400, 'From and to have to be timestamps')

    all_entries = OpeningPeriod.query.order_by(
        DB.asc(OpeningPeriod.opened)
    ).filter(
        OpeningPeriod.opened >= time_from,
        OpeningPeriod.opened <= time_to,
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
