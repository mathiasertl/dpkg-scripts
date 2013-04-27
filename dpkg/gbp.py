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

def get_config_value(value, default=None):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILES)
    return config['DEFAULT'].get(value, default)

def upstream_branch():
    return get_config_value('upstream-branch', 'upstream')

def master_branch():
    return get_config_value('master-branch', 'master')
