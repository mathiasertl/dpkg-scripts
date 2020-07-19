# helper functions for git-buildpackage related tasks

import configparser
import os
from datetime import date
from importlib import resources

from ..utils import parse_date

config = {}


def load_distributions(skip=None, start=None, until=None):
    if skip is None:
        skip = []

    def _sort_dist_key(t):
        val = t[1]['DEFAULT']['release-date']
        if val == '':
            return ('2099-12-31', t[0])
        return (val, t[0])

    today = date.today()

    # get config files in dpkg.dist_config module
    dists = [os.path.splitext(f)[0] for f in resources.contents('dpkg.dist_config') if f.endswith('.cfg')]

    # load config files
    dists = {d: get_config(d) for d in dists if d not in skip}

    # filter config files with skip=True
    dists = {d: c for d, c in dists.items() if not c['DEFAULT'].getboolean('skip', fallback=False)}

    for dist, config in sorted(dists.items(), key=_sort_dist_key):
        supported_until = config['DEFAULT']['supported-until']
        if supported_until == '':
            continue  # EOL for this dist has not been defined yet
        elif today > parse_date(supported_until):
            del dists[dist]

    dists = [d for d, c in sorted(dists.items(), key=_sort_dist_key)]
    if start:
        dists = dists[dists.index(start):]
    if until:
        dists = dists[:dists.index(until) + 1]

    return dists


def get_config(dist):
    global config

    if dist not in config:
        cfg = configparser.ConfigParser({
            'vendor': 'debian',
        })
        cfg.read_file(resources.open_text('dpkg.dist_config', '%s.cfg' % dist))
        config[dist] = cfg
    return config[dist]


def get(dist, value, default=None):
    config = get_config(dist)
    try:
        return config.get('DEFAULT', value)
    except configparser.NoOptionError:
        if default is not None:
            return default
        else:
            raise


def has_option(dist, value):
    return get_config(dist).has_option('DEFAULT', value)
