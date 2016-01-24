# helper functions for git-buildpackage related tasks

import os
import sys

import six

from six.moves import configparser

config = {}

def get_config(dist):
    global config

    if dist not in config:
        scriptpath = os.path.dirname(os.path.dirname(__file__))
        files = [
            os.path.join(scriptpath, 'dist-config', '%s.cfg' % dist),
            os.path.join(os.path.expanduser('~/.dist-config'), '%s.cfg' % dist),
            os.path.join('/etc/dist-config', '%s.cfg' % dist),
        ]

        cfg = configparser.RawConfigParser()
        cfg.read(files)
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
            six.reraise(*sys.exc_info())


def has_option(dist, value):
    return get_config(dist).has_option('DEFAULT', value)
