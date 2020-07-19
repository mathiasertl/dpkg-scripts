#!/usr/bin/python3

import argparse
import configparser
import datetime
import os
import subprocess
import sys

from dpkg import dist_config


def _parse_date(date):
    """Function to parse a date string into a date object."""
    return datetime.datetime.strptime(date, '%Y-%m-%d').date()


def _get_date(prompt, default=None):
    """Function to get a date via prompt."""
    fmt = '%Y-%m-%d'
    if default:
        act_prompt = '%s [%s]: ' % (prompt, default.strftime(fmt))
    else:
        act_prompt = '%s: ' % prompt

    d = input(act_prompt)
    if default and not d:
        return default
    elif not d:
        d = _get_date(prompt, default)

    try:
        return datetime.datetime.strptime(d, '%Y-%m-%d').date()
    except ValueError as e:
        print(e)
        return _get_date(prompt, default)


parser = argparse.ArgumentParser()
parser.add_argument('-v', '--vendor', choices=['debian', 'ubuntu'],
                    help='Distribution vendor.')
parser.add_argument('--release-date', metavar='YYYY-MM-DD', type=_parse_date,
                    help='Date when this distribution was released.')
parser.add_argument('--supported-until', metavar='YYYY-MM-DD', type=_parse_date,
                    help='Date until which this distribution is supported.')
parser.add_argument(
    '--release',
    help='Release tag used in versioning of packages (e.g. "10" for Debian or "20.04" for Ubuntu).')
parser.add_argument('--fsinf-keyring', default='/usr/share/keyrings/fsinf-keyring.gpg', metavar='PATH',
                    help='Location of the FSINF keyring (default: %(default)s).')
parser.add_argument('dist', help='Name of the distribution.')
args = parser.parse_args()


if not os.path.exists(args.fsinf_keyring):
    print('Error: %s: File not found (give path with --fsinf-keyring).' % args.fsinf_keyring)
    sys.exit(1)

vendor = args.vendor
if not vendor:
    vendor = input('Distribution vendor [DEBIAN|ubuntu]: ').lower().strip()
    if not vendor:
        vendor = 'debian'

release_date = args.release_date
if not release_date:
    release_date = _get_date('Release date', default=datetime.date.today())

supported_until = args.supported_until
if not supported_until:
    supported_until = _get_date('Supported until')

release = args.release
if not args.release:
    if vendor == 'debian':
        example = '10'
    else:
        example = '20.04'
    release = input('Release number (ex: %s): ' % example)
if vendor == 'debian':
    release = 'afa%s' % release
else:
    release = 'ubuntu%s' % release

# create debootstrap script if necessary
debootstrap_script = '/usr/share/debootstrap/scripts/%s' % args.dist
if not os.path.exists(debootstrap_script):
    if vendor == 'debian':
        debootstrap_dest = '/usr/share/debootstrap/scripts/sid'
    else:
        debootstrap_dest = '/usr/share/debootstrap/scripts/gutsy'

    subprocess.run(['sudo', 'ln', '-s', debootstrap_dest, debootstrap_script], check=True)

# location of this script
scriptpath = os.path.dirname(os.path.realpath(__file__))
dc_path = os.path.join(dist_config.__path__, '%s.cfg' % args.dist)
dc_config = configparser.ConfigParser()
dc_config['DEFAULT']['vendor'] = vendor
dc_config['DEFAULT']['release'] = release
dc_config['DEFAULT']['release-date'] = release_date.strftime('%Y-%m-%d')
dc_config['DEFAULT']['supported-until'] = supported_until.strftime('%Y-%m-%d')

with open(dc_path, 'w') as stream:
    dc_config.write(stream, True)

for arch in ['amd64', 'i386']:
    pbuilder_create = [
        'git-pbuilder', 'create', '--distribution', args.dist, '--architecture', arch,
        '--othermirror', 'deb http://apt.local %s all' % args.dist,
        '--keyring', args.fsinf_keyring,
        '--extrapackages', 'eatmydata gnupg2 lintian fakeroot fsinf-keyring',
    ]

    if vendor == 'debian':
        pbuilder_create += [
            '--mirror', 'http://ftp.at.debian.org/debian/',
            '--debootstrapopts', '--keyring=/usr/share/keyrings/debian-archive-keyring.gpg',
        ]
    else:
        pbuilder_create += [
            '--mirror=http://at.archive.ubuntu.com/ubuntu/', '--components=main universe',
            '--debootstrapopts' '--keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg',
        ]
    pbuilder_create += [
    ]

    # create pbuilder chroot
    if not os.path.exists('/var/cache/pbuilder/base-%s-%s.cow' % (args.dist, arch)):
        print('+ ', ' '.join(pbuilder_create))
        subprocess.run(pbuilder_create, check=True, env={'DIST': args.dist, 'ARCH': arch})

    # update dput config
    dput_path = os.path.expanduser('~/.dput.cf')
    dput_config = configparser.ConfigParser()
    dput_config.read([dput_path])
    dput_section = '%s-%s' % (args.dist, arch)
    if dput_section not in dput_config:
        dput_config.add_section(dput_section)
    dput_config[dput_section]['dist'] = args.dist
    dput_config[dput_section]['arch'] = arch

    dput_stage_section = '%s-%s-stage' % (args.dist, arch)
    if dput_stage_section not in dput_config:
        dput_config.add_section(dput_stage_section)
    dput_config[dput_stage_section]['method'] = 'local'
    dput_config[dput_stage_section]['incoming'] = '/var/cache/pbuilder/repo/%s-%s' % (args.dist, arch)

    with open(dput_path, 'w') as stream:
        dput_config.write(stream, space_around_delimiters=True)
