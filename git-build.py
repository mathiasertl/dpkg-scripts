#!/usr/bin/env python

import os
import sys

from argparse import ArgumentParser
from git import Repo
from subprocess import Popen

from dpkg import argparse_helpers
from dpkg import dist_config
from dpkg import env
from dpkg import process

# parse command-line:
parser = ArgumentParser(parents=[argparse_helpers.build_parser])
parser.add_argument('-d', '--dist', help="Distribution we build for.")
parser.add_argument('-a', '--arch', help="Architecture we build for.")
args = parser.parse_args()

# basic sanity checks:
if not os.path.exists('debian'):
    print('Error: debian: Directory not found.')
    sys.exit(1)
if args.dist is None:
    parser.error('Distribution must be given via --dist')
if args.arch is None:
    parser.error('Architecture must be given via --arch')

# default values:
gbp_args = [
    # -nc is passed to dpkg-buildpackage and equals "--no-pre-clean"
    '--git-pbuilder', '--git-dist=%s' % args.dist, '--git-arch=%s' % args.arch, '-nc',
]

# basic environment:
build_dir = os.path.expanduser('~/build/')
# pbuilder environment variables:
os.environ['DIST'] = args.dist
os.environ['ARCH'] = args.arch

# add a keyid to sign packages with, if in config
key_id = dist_config.get(args.dist, 'DEBSIGN_KEYID', '')
if key_id:
    os.environ['DEBSIGN_KEYID'] = key_id

cow_path = '/var/cache/pbuilder/base-%s-%s.cow' % (args.dist, args.arch)
if not os.path.exists(cow_path):
    print('Error: %s: Directory not found.')
    sys.exit(1)

# check if we would build in this distro
if not env.would_build(args.dist):
    print("Not building on %s." % args.dist)
    sys.exit()

# initialize the git-repository
repo = Repo(".")
orig_branch = repo.head.reference

# checkout any dist-specific banch:
branch = process.get_branch(repo, args.dist)
if branch:
    print('Using branch %s...' % branch.name)
    gbp_args += ['--git-debian-branch=%s' % branch.name]

    if repo.head.reference != branch:
        branch.checkout()

postexport = '--git-postexport=%s' % '; '.join(process.postexport_cmds(args.dist))

if args.upload:
    # NOTE: We do not use $GBP_CHANGES_FILE for the changes file, because the version is updated in
    # the postexport script and $GBP_CHANGES_FILE seems to be computed before that, so the location
    # of the changes-file does not add up.
    changes_file = process.get_changes_file(args.dist, args.arch)
    postbuild = '--git-postbuild=dput -f %s-%s %s' % (args.dist, args.arch, changes_file)
    gbp_args.append(postbuild)

if args.pristine:
    gbp_args.append('--git-pristine-tar')
elif args.upstream_tree:
    gbp_args.append('--git-upstream-tree=%s' % args.upstream_tree)
    if args.upstream_branch:
        gbp_args.append('--git-upstream-branch=%s' % args.upstream_branch)
if args.sa:
    gbp_args.append('-sa')

# see if we have only arch-independent packages, if yes, only build on amd64:
details = env.get_package_details()
archs = set([v['Architecture'] for v in details.values() if 'Source' not in v])
if set(['all']) == archs and args.arch != 'amd64':
    print('Only arch-independent packages found and not on amd64!')
    sys.exit()

# get package details:
source_pkg, binary_pkgs = env.get_packages()

# create export_dir
export_dir = os.path.join(build_dir, '%s-%s' % (args.dist, args.arch))
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

# build package
git_buildpackage = [
    'git-buildpackage',
    '--git-cleaner=',
    '--git-export-dir=%s' % export_dir,
    postexport,
] + gbp_args
print(' '.join(git_buildpackage))
try:
    p = Popen(git_buildpackage)
    p.communicate()
finally:
    orig_branch.checkout()
sys.exit(p.returncode)
