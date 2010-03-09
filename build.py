#!/usr/bin/env python

import os, re, sys, glob, shutil
from optparse import OptionParser
from subprocess import *
try:
	import configparser
except ImportError:
	import ConfigParser as configparser

parser = OptionParser()
parser.add_option( '--dest', default=os.path.expanduser( '~/build/'),
	help="Move the packages to this directory (Default: ~/build/)" )
parser.add_option( '--dist-name', metavar='NAME',
	help="Override distribution codename detection. By default, this is the"
	"value of DISTRIB_CODENAME in /etc/lsb-release, e.g. 'lenny' or "
	"'karmic'." )
options, args = parser.parse_args()

if args == []:
	action='build'
elif len(args) == 1:
	action=args[0] #TODO: valid actions?
else:
	print( "Please supply at maximum one action." )
	sys.exit(1)

# check if we are in the right directory
dh_testdir = [ 'dh_testdir' ]
p = Popen( dh_testdir, stderr=PIPE )
stderr = p.communicate()[1].strip()
if p.returncode:
	print( stderr.decode( 'utf_8' ) )
	sys.exit(1)

# see where we run
if not options.dist_name:
	f = open( '/etc/lsb-release' )
	lines = f.readlines()
	for line in lines:
		line = line.strip()
		var, delim, val = line.partition( '=' )
		if var == 'DISTRIB_CODENAME' and not options.dist_name:
			options.dist_name=val
			break

if not options.dist_name:
	print( "Error: Could not get distribution codename" )
	sys.exit(1)

# load distribution config
distrib_config_file = '../../.' + options.dist_name + '.cfg'
if not os.path.exists( distrib_config_file ):
	print( "Error: " + distrib_config_file + ": Does not exist" )
	sys.exit(1)
distrib_config = configparser.ConfigParser()
distrib_config.read( distrib_config_file )

# switch to distro-specific dir, if it exists
basename = os.path.basename( os.getcwd() )
distro_build_dir = '../../' + options.dist_name + '/' + basename
if os.path.exists( distro_build_dir ):
	os.chdir( distro_build_dir )

# action 'where':
if action == 'where':
	dist = os.path.basename( os.path.dirname( os.getcwd() ) )
	print( "Building in " + dist + '/' + basename )
	sys.exit(0)

# load package config
package_config_file = '../' + basename + '.cfg'
package_config = configparser.ConfigParser()
package_config.read( package_config_file )

# see if we build for this distro
if package_config.has_section( 'distros' ):
	if package_config.has_option( 'distros', 'exclude' ):
		excludes = package_config.get( 'distros', 'exclude' ).split()
		if distrib_codename in excludes:
			print( "Not building for " + distrib_codename )
			sys.exit()

if action == 'check':
	check = [ 'dpkg-checkbuilddeps' ]
	p = Popen( check, stderr=PIPE )
	stderr = p.communicate()[1].strip()
	if p.returncode:
		print( stderr.decode( 'utf_8' ) )
	else:
		print( "Passed dependency check." )
	sys.exit()

# set compat level to distro-specific value
compat = distrib_config.get( 'defaults', 'compat' )
print( "Set debian/compat to " + compat + "..." )
f = open( 'debian/compat', 'w' )
f.write( compat + '\n' )
f.close()

# set Standards-Version in debian/control:
standards = distrib_config.get( 'defaults', 'standards' )
print( "Set Standards-Version to " + standards + '...' )
p = Popen( [ 'sed', '-i', 's/^Standards-Version:.*/Standards-Version: ' + standards + '/', 'debian/control' ] )
p.communicate()

# get source package and binary packages:
binary_pkgs = []
source_pkg = ''
f = open( 'debian/control', 'r' )
control = f.readlines()
for line in control:
	if line.startswith( 'Source: ' ):
		source_pkg = line.partition( ': ' )[2].strip()

	if line.startswith( 'Package: ' ):
		package = line.partition( ': ' )[2].strip()
		binary_pkgs.append( package )

# prepare
print( "\n\nPreparing target..." )
prepare_p = Popen( [ 'fakeroot', 'debian/rules', 'prepare' ] )
prepare_p.communicate()

# replace __DATE__
pdate = Popen( [ 'date', '-R' ], stdout=PIPE )
timestamp = pdate.communicate()[0].decode( 'utf_8' ).strip()
p1 = Popen( [ 'find', 'debian/', '-maxdepth', '1', '-type', 'f' ], stdout=PIPE )
p2 = Popen( [ 'xargs', 'sed', '-i', 's/__DATE__/' + timestamp + '/' ], stdin = p1.stdout )
p2.communicate()

print( "\n\nBuilding target..." )
debuild = Popen( ['debuild' ] )
debuild.communicate()

# delete useless files:
#changes = glob.glob( '../' + source_pkg + '*.changes' )
#for change in changes:
#	os.remove( change )
builds = glob.glob( '../' + source_pkg + '*.build' )
for build in builds:
	os.remove( build )

# prepare repo directory:
base_target = os.path.expanduser( options.dest + '/' + options.dist_name )
generic_target = base_target + '/all/all'

def get_arch( package, file ):
	return ''
	if package == 'source':
		return 'source'
	else:
		# parse binary package arch:
		arch = re.split( '_([^_]*).deb', file )[1]
		arch = 'binary-' + arch
		return arch

# link a "file" belonging to package "what" to the components configured
# in package specific config file
def link( what, file ):
	components = []
	if not package_config.has_section( 'components' ):
		return
	
	if package_config.has_option( 'components', '*' ):
		components += package_config.get( 'components', '*' ).split()
	if package_config.has_option( 'components', what ):
		components += package_config.get( 'components', what ).split()

	if components == []:
		return

	basename = os.path.basename( file )
	arch = get_arch( what, file )
	source = os.path.normpath( '../../all/all/' + arch + '/' + basename )
	
	for component in components:
		target_dir = os.path.expanduser( base_target + '/' + component + '/all/' + arch )
		target = target_dir + '/' + basename
		if os.path.exists( target ):
			return

		if not os.path.exists( target_dir ):
			os.makedirs( target_dir )
		if os.path.exists( target ):
			os.remove( target )
		os.symlink( source, target )
	
# move/copy files from buld-directory to repository tree
def move_files( base, suffix, action, package=None ):
	if package == None:
		package = base

	files = glob.glob( '../' + base + '_*.' + suffix )
	for file in files:
		arch = get_arch( package, file )

		basename = os.path.basename( file )
		target = generic_target + '/' + arch + '/' + basename
		if not os.path.exists( os.path.dirname( target ) ):
			os.makedirs( os.path.dirname( target ) )
		if os.path.exists( target ):
			os.remove( target )

		f = getattr( shutil, action )
		f( file, target )
		link( package, file )

# copy move everything to generic components and symlink in specific components
print( "Building repository tree..." )
move_files( source_pkg, 'diff.gz', 'move', 'source' )
move_files( source_pkg, 'dsc', 'move', 'source' )
move_files( source_pkg, 'orig.tar.gz', 'copy', 'source' )
for package in binary_pkgs:
	move_files( package, 'deb', 'move' )

# reset package to a nice default state
f = open( 'debian/compat', 'w' )
f.write( '7\n' )
f.close()

# standards version to most recent
p = Popen( [ 'sed', '-i', 's/^Standards-Version:.*/Standards-Version: 3.8.3/', 'debian/control' ] )
p.communicate()
