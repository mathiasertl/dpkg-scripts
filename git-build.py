#!/usr/bin/env python

import ConfigParser
import atexit
import os
import shutil
import tempfile
import sys

from argparse import ArgumentParser
from subprocess import Popen, PIPE
from dpkg import env, process
from git import Repo

# parse command-line:
parser = ArgumentParser()
parser.add_argument('--keep-temp-dir', action='store_true', default=False,
    help="Do not delete temporary build directory after build.")
parser.add_argument('--upload', action='store_true', default=False,
    help="Upload files to enceladus.htu.")
parser.add_argument('--sa', action='store_true', default=False,
    help="Force inclusion of original source (Default: True unless --no-pristine is given).")
parser.add_argument('--no-pristine', action='store_false', dest='pristine',
    default=True, help="Do not use pristine tars")
parser.add_argument('--dist', help="Distribution we build for.")
parser.add_argument('--arch', help="Architecture we build for.")
args = parser.parse_args()

# basic sanity checks:
if not os.path.exists('debian'):
    print('Error: debian: Directory not found.')
    sys.exit(1)

if args.pristine:
    args.sa = True

# default values:
gbp_args = []

# basic environment:
if args.arch is None:
    args.arch = env.get_architecture()
if args.dist is None:
    args.dist = env.get_distribution()
build_dir = os.path.expanduser('~/build/')

# config
config = ConfigParser.ConfigParser({'append-dist': 'true'})
config.read([
    'debian/gbp.conf',
    '.git/gbp.conf',
])

# get path to dist-config
scriptpath = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(scriptpath, 'dist-config')
dist_config_path = os.path.join(config_path, args.dist + '.cfg')

# check if we wuild build in this distro
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

if os.path.exists('/var/cache/pbuilder/base-%s-%s.cow' % (args.dist, args.arch)):
    # use git-pbuilder if available
    gbp_args += ['--git-pbuilder', '--git-dist=%s' % args.dist, '--git-arch=%s' % args.arch]
    os.environ['DIST'] = args.dist
    os.environ['ARCH'] = args.arch
elif args.sa:
    gbp_args.append('--git-builder=debuild -i\.git -I.git -sa')

if args.pristine:
    gbp_args.append('--git-pristine-tar')

# see if we have only arch-independent packages, if yes, only build on amd64:
details = env.get_package_details()
archs = set([v['Architecture'] for v in details.values() if 'Source' not in v])
if set(['all']) == archs and args.arch != 'amd64':
    print('Only arch-independent packages found and not on amd64!')
    sys.exit()

# prepare package
print('prepare(%s, %s, %s)' % (args.dist, dist_config_path, config))
process.prepare(args.dist, dist_config_path, config)

# get package details:
version = env.get_version()
source_pkg, binary_pkgs = env.get_packages()

# commit any changes:
commited_changes = False
git_commit = ['git', 'commit', '-a', '-m', 'prepare package for %s' % args.dist]
p = Popen(git_commit, stderr=PIPE)
print(' '.join(git_commit))
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
p = Popen(git_buildpackage, stderr=PIPE)
print(' '.join(git_buildpackage))
stderr = p.communicate()[1].strip()
if p.returncode:
    print(stderr.decode('utf_8'))
    sys.exit(1)
