# helper functions for git-buildpackage related tasks

import os
import sys

import six

from six.moves import configparser

CONFIG_FILES = [
    '/etc/git-buildpackage/gbp.conf',
    os.path.expanduser('~/.gbp.conf'),
    '.gbp.conf',
    'debian/gbp.conf',
    '.git/gbp.conf',
]
config = None

def get_config():
    global config
    if config is None:
        config = configparser.RawConfigParser()
        config.read(CONFIG_FILES)
    return config

def get(value, default=None):
    config = get_config()
    try:
        return config.get('DEFAULT', value)
    except configparser.NoOptionError:
        if default is not None:
            return default
        else:
            six.reraise(*sys.exc_info())

def getboolean(value, default=None):
    config = get_config()
    try:
        return config.getboolean('DEFAULT', value)
    except configparser.NoOptionError:
        if default is not None:
            return default
        else:
            six.reraise(*sys.exc_info())


def has_option(value):
    config = get_config()
    return config.has_option('DEFAULT', value)


def upstream_branch():
    return get('upstream-branch', 'upstream')


def master_branch():
    return get('debian-branch', 'master')


def upstream_tag():
    return get('upstream-tag', 'upstream/%(version)s')


def debian_tag():
    return get('debian-tag', 'debian/%(version)s')


def compression():
    return get('compression', 'gzip')
