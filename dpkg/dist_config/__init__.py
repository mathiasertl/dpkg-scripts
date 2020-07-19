# helper functions for git-buildpackage related tasks

import configparser
import os
from datetime import date
from importlib import resources

from ..utils import parse_date

config = {}


def load_distributions():
    today = date.today()

    dists = [os.path.splitext(f)[0] for f in resources.contents('dpkg.dist_config') if f.endswith('.cfg')]
    for dist in list(sorted(dists)):
        config = get_config(dist)

        supported_until = config['DEFAULT']['supported-until']
        if supported_until == '':
            continue  # EOL for this dist has not been defined yet

        if today > parse_date(supported_until):
            dists.remove(dist)
            continue

        if config['DEFAULT'].getboolean('skip'):
            dists.remove(dist)

    print(sorted(dists))


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
