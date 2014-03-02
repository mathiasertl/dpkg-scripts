#!/usr/bin/env python

import ConfigParser
import atexit
import os
import shutil
import tempfile
import sys

from argparse import ArgumentParser
from subprocess import Popen, PIPE
from dpkg import env, process, argparse_helpers
from git import Repo

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
    '--git-pbuilder', '--git-dist=%s' % args.dist, '--git-arch=%s' % args.arch,
]

# basic environment:
build_dir = os.path.expanduser('~/build/')
# pbuilder environment variables:
os.environ['DIST'] = args.dist
os.environ['ARCH'] = args.arch

cow_path = '/var/cache/pbuilder/base-%s-%s.cow' % (args.dist, args.arch)
if not os.path.exists(cow_path):
    print('Error: %s: Directory not found.')
    sys.exit(1)

# config
config = ConfigParser.ConfigParser({'append-dist': 'true'})
config.read([
    'debian/gbp.conf',
    '.git/gbp.conf',
])

# get path to dist-config
scriptpath = os.path.dirname(os.path.realpath(__file__))
dist_config_path = [
    os.path.join(os.path.expanduser('~/.dist-config'), '%s.cfg' % args.dist),
    os.path.join('/etc/dist-config', '%s.cfg' % args.dist),
]

# check if we would build in this distro
if not env.would_build(config, args.dist):
    print("Not building on %s." % args.dist)
    sys.exit()

# exit handler
orig_dir = os.getcwd()

def exit(orig_dir, temp_directory, keep):
    os.chdir(orig_dir)
    if keep:
        print('Temporary directory is %s' % temp_directory)
    elif os.path.exists(temp_directory):
        print('Removing %s...' % temp_directory)
        shutil.rmtree(temp_directory)

# create temporary directory:
temp_directory = tempfile.mkdtemp()
atexit.register(exit, orig_dir, temp_directory, args.keep_temp_dir)

# move to temporary directory:
temp_dest = os.path.join(temp_directory, os.path.basename(os.getcwd()))
shutil.copytree('.', temp_dest)
os.chdir(temp_dest)

# initialize the git-repository
repo = Repo(".")
orig_branch = repo.head.reference

# checkout any dist-specific banch:
branch = process.get_branch(repo, config, args.dist)
if branch:
    print('Using branch %s...' % branch.name)
    gbp_args += ['--git-debian-branch=%s' % branch.name]

    if repo.head.reference != branch:
        branch.checkout()

if args.upload:
    postbuild = '--git-postbuild=dput %s-%s $GBP_CHANGES_FILE' % (args.dist, args.arch)
    gbp_args.append(postbuild)

if args.pristine:
    gbp_args.append('--git-pristine-tar')
elif args.upstream_tree:
    gbp_args.append('--git-upstream-tree=%s' % args.upstream_tree)
    if args.upstream_branch:
        gbp_args.append('--git-upstream-branch=%s' % args.upstream_branch)

# see if we have only arch-independent packages, if yes, only build on amd64:
details = env.get_package_details()
archs = set([v['Architecture'] for v in details.values() if 'Source' not in v])
if set(['all']) == archs and args.arch != 'amd64':
    print('Only arch-independent packages found and not on amd64!')
    sys.exit()

# prepare package
process.prepare(args.dist, dist_config_path, config)

# get package details:
source_pkg, binary_pkgs = env.get_packages()

# commit any changes:
git_commit = ['git', 'commit', 'debian/', '-m', 'prepare package for %s' % args.dist]
print(' '.join(git_commit))
p = Popen(git_commit, stderr=PIPE)
p.communicate()

# create export_dir
export_dir = os.path.join(build_dir, '%s-%s' % (args.dist, args.arch))
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

# build package
git_buildpackage = [
    'git-buildpackage',
    '--git-export-dir=%s' % export_dir,
] + gbp_args
print(' '.join(git_buildpackage))
p = Popen(git_buildpackage, stderr=PIPE)
stderr = p.communicate()[1].strip()
if p.returncode:
    print(stderr.decode('utf_8'))
    sys.exit(1)
