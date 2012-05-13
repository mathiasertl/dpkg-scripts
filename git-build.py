#!/usr/bin/env python

import os, re, sys, shutil, tempfile, shlex, atexit
from optparse import OptionParser
from subprocess import *
from dpkg import *

from git import *

try:
	import configparser
except ImportError:
	import ConfigParser as configparser

# basic sanity checks:
if not os.path.exists('debian'):
	print('Error: debian: Directory not found.')
	sys.exit(1)

# parse command-line:
parser = OptionParser()
parser.add_option('--keep-temp-dir', action='store_true', default=False,
	help="Do not delete temporary build directory after build.")
options, args = parser.parse_args()

# default values:
gbp_args = []

# basic environment:
arch = env.get_architecture()
dist = env.get_distribution()
build_dir = os.path.expanduser('~/build/')

# config
config = configparser.ConfigParser()
config.read([os.path.expanduser('~/debian/gbp.conf'), 'debian/gbp.conf', '.git/gbp.conf'])

# get path to dist-config
scriptpath = os.path.dirname(os.path.realpath(__file__ ))
config_path = os.path.join(scriptpath, 'dist-config')
dist_config_path = os.path.join(config_path, dist + '.cfg')

# initialize the git-repository
repo = Repo(".")
orig_branch = repo.head.reference
orig_dir = os.getcwd()

# check if we wuild build in this distro
if not env.would_build(config, dist):
	print("Not building on %s." % dist)
	sys.exit()

# exit handler
def exit(orig_dir, temp_directory, keep):
	os.chdir(orig_dir)
	if keep:
		print('Temporary directory is %s' % temp_directory)
	elif os.path.exists(temp_directory):
		print('Removing %s...' % temp_directory)
		shutil.rmtree(temp_directory)

# create export_dir
export_dir = os.path.join(build_dir, '%s/all/all/' % dist)
if not os.path.exists(export_dir):
	os.makedirs(export_dir)

# create temporary directory:
temp_directory = tempfile.mkdtemp()
atexit.register(exit, orig_dir, temp_directory, options.keep_temp_dir)

# move to demporary directory:
temp_dest = os.path.join(temp_directory, os.path.basename(os.getcwd()))
shutil.copytree( '.', temp_dest )
os.chdir(temp_dest)

# checkout any dist-specific banch:
branch = process.get_branch(repo, config, dist)
if branch:
	print('Using branch %s...' % branch.name)
	gbp_args += ['--git-debian-branch=%s' % branch.name]

	if repo.head.reference != branch:
		branch.checkout()

# see if we have only arch-independent packages, if yes, only build on amd64:
details = env.get_package_details()
archs = set( [ v['Architecture'] for v in details.values() if 'Source' not in v ] )
if set( ['all'] ) == archs and arch != 'amd64':
	print( 'Only arch-independent packages found and not on amd64!' )
	sys.exit()

# prepare package
process.prepare(dist, dist_config_path, config)

# get package details:
version = env.get_version()
source_pkg, binary_pkgs = env.get_packages()

# commit any changes:
commited_changes = False
git_commit = ['git', 'commit', '-a', '-m', 'prepare package for %s' % dist ]
p = Popen(git_commit, stderr=PIPE)
print(' '.join(git_commit))
p.communicate()

# build package
git_buildpackage = ['git-buildpackage', '--git-export-dir=%s' % export_dir ] + gbp_args
p = Popen(git_buildpackage, stderr=PIPE)
print(' '.join(git_buildpackage))
stderr = p.communicate()[1].strip()
if p.returncode:
	print(stderr.decode('utf_8'))
	sys.exit(1)

# create directory stubs:
source_dir = os.path.join(build_dir, '%s/all/source/' % dist)
if not os.path.exists(source_dir):
	os.makedirs(source_dir)
binary_dir = os.path.join(build_dir, '%s/all/binary-%s/' % (dist, arch))
if not os.path.exists(binary_dir):
	os.makedirs(binary_dir)

# link components:
if config.has_option('DEFAULT', 'components'):
	files = env.get_package_files(export_dir, source_pkg, version, arch)
	components = config.get('DEFAULT', 'components').split()

	for component in components:
		# precreate directories
		component_dir = os.path.join(build_dir, '%s/%s/all' % (dist, component))
		if not os.path.exists(component_dir):
			os.makedirs(component_dir)
		source_dir = os.path.join(build_dir, '%s/%s/source' % (dist, component))
		if not os.path.exists(source_dir):
			os.makedirs(source_dir)
		binary_dir = os.path.join(build_dir, '%s/%s/binary-%s' % (dist, component, arch))
		if not os.path.exists(binary_dir):
			os.makedirs(binary_dir)

		for f in files:
			source = os.path.join('../../all/all/', f)
			dest = os.path.join(component_dir, f)
			if not os.path.exists(dest):
				print('ln -s %s %s' % (source, dest))
				os.symlink(source, dest)
