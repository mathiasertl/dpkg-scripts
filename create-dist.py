#!/usr/bin/python3

import argparse
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--vendor', choices=['debian', 'ubuntu'],
                    help='Distribution vendor.')
parser.add_argument('dist', help='Name of the distribution.')
args = parser.parse_args()

vendor = args.vendor
if not vendor:
    vendor = input('Distribution vendor [DEBIAN|ubuntu]: ').lower().strip()
    if not vendor:
        vendor = 'debian'

# create debootstrap script if necessary
debootstrap_script = '/usr/share/debootstrap/scripts/%s' % args.dist
if not os.path.exists(debootstrap_script):
    if vendor == 'debian':
        debootstrap_dest = '/usr/share/debootstrap/scripts/sid'
    else:
        debootstrap_dest = '/usr/share/debootstrap/scripts/gutsy'

    subprocess.run(['sudo', 'ln', '-s', debootstrap_dest, debootstrap_script], check=True)


for arch in ['amd64', 'i386']:
    pbuilder_create = [
        'git-pbuilder', 'create', '--distribution', args.dist, '--architecture', arch,
        '--othermirror', 'deb http://apt.local %s all' % args.dist,
        '--keyring', '/usr/share/keyrings/fsinf-keyring.gpg',
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

    if not os.path.exists('/var/cache/pbuilder/base-%s-%s.cow' % (args.dist, arch)):
        print('+ ', ' '.join(pbuilder_create))
        subprocess.run(pbuilder_create, check=True, env={'DIST': args.dist, 'ARCH': arch})
