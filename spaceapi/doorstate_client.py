#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client script to update the doorstate on our website or to make plots."""

import argparse
from collections import defaultdict
from datetime import datetime, time, timedelta

import requests
from dateutil.tz import tzlocal
from matplotlib import dates as mdates
from matplotlib import pyplot

from lib_doorstate import (add_debug_arg, add_key_arg, add_outfile_arg,
                           add_plot_type_arg, add_state_arg, add_time_arg,
                           add_url_arg, calculate_hmac,
                           parse_args_and_read_key, to_timestamp)

ARGS = None  # command line args


def _json_response_error_handling(response):
    """Return the response json of a request after error handling."""
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        print('Error', err.response.status_code)
        try:
            response_json = response.json()
            print(response_json)
        except Exception:
            print(err)

        exit(1)

    return response.json()


def update_doorstate(args):
    """Update doorstate (opened, closed, ...)."""
    resp = requests.post(
        args.url,
        data={
            'time': int(args.time),
            'state': args.state,
            'hmac': calculate_hmac(args.time, args.state, args.key)
        }
    )
    resp_json = _json_response_error_handling(resp)
    if any((key not in resp_json for key in {'time', 'state', '_text'})):
        print("Invalid response from API:", resp_json)
    elif resp_json['time'] <= args.time and resp_json['state'] == args.state:
        print('OK', resp_json['_text'])
    else:
        print(
            'The API missunderstood our request. Sent:',
            args.time, args.state,
            'API response: ', resp_json['time'], resp_json['state']
        )


def plot_by_hour(data, outfile):
    """Plot graph by hour."""
    fig = pyplot.figure()
    plot = fig.add_subplot(1, 1, 1)

    for entry in data:
        opened = datetime.fromtimestamp(entry['opened'], tzlocal())
        openedhour = opened.time().hour + opened.time().minute / 60
        closed = (
            datetime.fromtimestamp(entry['closed'], tzlocal())
            if entry['closed'] else datetime.now(tzlocal())
        )
        closedhour = closed.time().hour + closed.time().minute / 60
        # split entry if it spans to next day
        if opened.date() != closed.date():
            plot.vlines(opened.date(), openedhour, 24, color='g', lw=2)
            plot.vlines(closed.date(), 0, closedhour, color='g', lw=2)
        else:
            plot.vlines(opened.date(), openedhour, closedhour, color='g', lw=2)

    plot.set_ylim(0, 24)

    plot.set_ylabel("Uhrzeit (Stunde)")
    plot.set_title("Das FAU FabLab war offen")

    plot.xaxis.set_major_locator(mdates.MonthLocator())
    plot.xaxis.set_major_formatter(mdates.DateFormatter('%B'))
    plot.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=7))

    plot.grid(True)

    fig.autofmt_xdate()
    pyplot.savefig(outfile)


def plot_by_week(data, outfile):
    """Plot graph by week."""
    data_by_week = defaultdict(timedelta)  # Save open duration per week
    for entry in data:
        opened = datetime.fromtimestamp(entry['opened'], tzlocal())
        closed = (
            datetime.fromtimestamp(entry['closed'], tzlocal())
            if entry['closed'] else datetime.now(tzlocal())
        )
        # get the previous monday of opened date
        last_monday = (opened - timedelta(days=opened.weekday())).date()
        last_monday = datetime.combine(last_monday, time(0), tzlocal())  # ... at 0:00
        while True:
            # for each week between opened and closed add the open time duration
            next_monday = last_monday + timedelta(days=7)
            data_by_week[last_monday.date()] += min(closed, next_monday) - opened
            opened = min(closed, next_monday)
            last_monday = next_monday
            if closed == opened:
                break

    fig = pyplot.figure()
    plot = fig.add_subplot(1, 1, 1)
    plot.bar(
        [x for x in data_by_week.keys()],
        [y.total_seconds() / (60 * 60) for y in data_by_week.values()],
        align='center',
        width=6,
    )
    plot.xaxis_date()

    plot.set_ylabel("Geöffnete Stunden pro Woche")
    plot.set_title("Öffnungszeiten")

    plot.xaxis.set_major_locator(mdates.MonthLocator())
    plot.xaxis.set_major_formatter(mdates.DateFormatter('%B'))
    plot.xaxis.set_minor_locator(mdates.WeekdayLocator(interval=7))

    plot.grid(True)

    fig.autofmt_xdate()
    pyplot.savefig(outfile)


def plot_doorstate(args):
    """Generate plots."""
    resp = requests.get(
        args.url,
        params={'from': to_timestamp(datetime.now(tzlocal()) - timedelta(days=365))},
    )
    resp_json = _json_response_error_handling(resp)

    if not isinstance(resp_json, list):
        print('Invalid reponse from API:', resp_json)

    if args.plot_type == 'by-week':
        plot_by_week(resp_json, args.out)
    elif args.plot_type == 'by-hour':
        plot_by_hour(resp_json, args.out)


def parse_args():
    """Return parsed command line arguments."""
    parser = argparse.ArgumentParser(__doc__)
    subparsers = parser.add_subparsers(title='actions', dest='action')

    update_parser = subparsers.add_parser('update', help='update door state')
    add_debug_arg(update_parser)
    add_url_arg(update_parser, default='https://fablab.fau.de/spaceapi/door/')
    add_key_arg(update_parser)
    add_time_arg(update_parser)
    add_state_arg(update_parser)

    plot_parser = subparsers.add_parser('plot', help='Plot history')
    add_url_arg(plot_parser, default='https://fablab.fau.de/spaceapi/door/all/')
    add_debug_arg(plot_parser)
    add_plot_type_arg(plot_parser)
    add_outfile_arg(plot_parser)

    return parse_args_and_read_key(parser)


def main():
    """Parse args and run action."""
    args = parse_args()
    if args.action == 'update':
        update_doorstate(args)
    elif args.action == 'plot':
        plot_doorstate(args)


if __name__ == '__main__':
    main()
