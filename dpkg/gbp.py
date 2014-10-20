# helper functions for git-buildpackage related tasks

import configparser
import os

CONFIG_FILES = [
    '/etc/git-buildpackage/gbp.conf',
    os.path.expanduser('~/.gbp.conf'),
    '.gbp.conf',
    'debian/gbp.conf',
    '.git/gbp.conf',
]
config = None

def get_config_value(value, default=None):
    global config
    if config is None:
        config = configparser.RawConfigParser()
        config.read(CONFIG_FILES)
    return config['DEFAULT'].get(value, default)

def upstream_branch():
    return get_config_value('upstream-branch', 'upstream')

def master_branch():
    return get_config_value('debian-branch', 'master')

def upstream_tag():
    return get_config_value('upstream-tag', 'upstream/%(version)s')

def debian_tag():
    return get_config_value('debian-tag', 'debian/%(version)s')
