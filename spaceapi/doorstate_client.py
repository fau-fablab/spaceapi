#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client script to update the doorstate on our website or to make plots."""

import argparse
from collections import defaultdict
from datetime import datetime, time, timedelta

import requests
from matplotlib import dates as mdates
from matplotlib import pyplot

from lib_doorstate import (add_debug_arg, add_key_arg, add_outfile_arg,
                           add_plot_type_arg, add_state_arg, add_time_arg,
                           add_url_arg, calculate_hmac,
                           json_response_error_handling,
                           parse_args_and_read_key)

ARGS = None  # command line args


def update_doorstate(args):
    """Update doorstate (open, close, ...)."""
    resp = requests.post(
        args.url,
        data={
            'time': int(args.time),
            'state': args.state,
            'hmac': calculate_hmac(args.time, args.state, args.key)
        }
    )
    resp_json = json_response_error_handling(resp)
    if 'time' not in resp_json or 'state' not in resp_json:
        print("Invalid response from API:", resp_json)
    elif resp_json['time'] == args.time and resp_json['state'] == args.state:
        print('OK', args.time, args.state)
    else:
        print(
            'The API missunderstood our request. Sent:',
            args.time, args.state,
            'API response: ', resp_json['time'], resp_json['state']
        )


def _open_ranges_with_end(list_of_entries):
    """
    Generator to filter open ranges out of entries and add their end time.

    >>> list(_with_end([
            {'time': 0, 'state': 'open'},
            {'time': 10, 'state': 'close'},
            {'time': 20, 'state': 'open'},
        ]))
    [
        {
            'start': datetime.utcfromtimestamp(0),
            'end': datetime.utcfromtimestamp(10),
            'state': 'end',
        },
    ]
    """
    list_iterator = iter(list_of_entries)
    last = next(list_iterator)
    for entry in list_iterator:
        start = datetime.utcfromtimestamp(last['time'])
        end = datetime.utcfromtimestamp(entry['time'])
        if last['state'] == 'open':
            yield {
                'start': start,
                'end': end,
                'state': last['state'],
            }
        last = entry


def plot_by_hour(data, outfile):
    """Plot graph by hour."""
    fig = pyplot.figure()
    plot = fig.add_subplot(1, 1, 1)

    for entry in _open_ranges_with_end(data):
        start = entry['start']
        starthour = start.time().hour + start.time().minute / 60
        end = entry['end']
        endhour = end.time().hour + end.time().minute / 60
        # split entry if it spans to next day
        if start.date() != end.date():
            plot.vlines(start.date(), starthour, 24, color='g', lw=2)
            plot.vlines(end.date(), 0, endhour, color='g', lw=2)
        else:
            plot.vlines(start.date(), starthour, endhour, color='g', lw=2)

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
    for entry in _open_ranges_with_end(data):
        start = entry['start']
        end = entry['end']
        # get the previous monday of start date
        last_monday = (start - timedelta(days=start.weekday())).date()
        last_monday = datetime.combine(last_monday, time(0))  # ... at 0:00
        while True:
            # for each week between start and end add the open time duration
            next_monday = last_monday + timedelta(days=7)
            data_by_week[last_monday.date()] += min(end, next_monday) - start
            start = min(end, next_monday)
            last_monday = next_monday
            if end == start:
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
        params={'from': int((datetime.utcnow() - timedelta(days=365)).timestamp())},
    )
    resp_json = json_response_error_handling(resp)

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
