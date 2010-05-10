#!/usr/bin/env python

import os, re, sys, glob, shutil
from optparse import OptionParser
from subprocess import *
from dpkg import *

try:
	import configparser
except ImportError:
	import ConfigParser as configparser

parser = OptionParser()
parser.add_option( '--dest', default=os.path.expanduser( '~/build/'),
	help="Move the packages to this directory (Default: ~/build/)" )
parser.add_option( '--dist',
	help="Override distribution codename detection. By default, this is the"
	"value of DISTRIB_CODENAME in /etc/lsb-release, e.g. 'lenny' or "
	"'karmic'." )
parser.add_option( '--arch', 
	help="Override the architecture that we build for. The script should "
	"automatically detect the architecture with the help of "
	"dpkg-architecture." )
parser.add_option( '--no-source', action='store_false', dest='src', default=True,
	help="Do not build source package" )
parser.add_option( '--no-binary', action='store_false', dest='bin', default=True,
	help="Do not build binary packages" )
options, args = parser.parse_args()

if args == []:
	action='build'
elif len(args) == 1:
	action=args[0] #TODO: valid actions?
else:
	print( "Please supply at most one action." )
	sys.exit(1)

# get distribution and architecture first:
if not options.dist:
	options.dist = env.get_distribution()
if not options.arch:
	options.arch = env.get_architecture()

# switch to distro-specific dir, if it exists
basename = os.path.basename( os.getcwd() )
distro_build_dir = '../../' + options.dist + '/' + basename
if os.path.exists( distro_build_dir ):
	os.chdir( distro_build_dir )

# action 'where':
if action == 'where':
	dist = os.path.basename( os.path.dirname( os.getcwd() ) )
	print( "Building in " + dist + '/' + basename )
	sys.exit(0)

# get some runtime data that we will fail without
source, binary_pkgs = env.get_packages()
version = env.get_version()
upstream_version = version.rsplit( '-', 1 )[0]

# load package config
package_config_file = '../' + basename + '.cfg'
package_config = configparser.ConfigParser()
package_config.read( package_config_file )

# see if we build for this distro
if package_config.has_section( 'distros' ):
	if package_config.has_option( 'distros', 'exclude' ):
		excludes = package_config.get( 'distros', 'exclude' ).split()
		if options.dist in excludes:
			print( "Not building for " + options.dist )
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

# prepare package
process.prepare( options.dist )

print( "\n\nBuilding target..." )
debuild_params = [ '--set-envvar', 'DIST=' + options.dist, 
	'--set-envvar', 'ARCH=' + options.arch ]

if options.src:
	cmd = [ 'debuild' ] + debuild_params + [ '-S', '-sa']
	print( " ".join( cmd ) )
	debuild = Popen( cmd )
	debuild.communicate()
	if debuild.returncode != 0:
		options.src = False
		options.bin = False
		print( "Error building source package!" )

if options.bin:
	cmd = [ 'debuild'] + debuild_params + [ '-b' ]
	print( " ".join( cmd ) )
	debuild = Popen( cmd )
	debuild.communicate()
	if debuild.returncode != 0:
		options.bin = False
		print( "Error building binary package!" )

# if we have a "final" target, we execute it
# TODO: move this to process.finish()
for line in open( 'debian/rules' ).readlines():
	if line.startswith( 'final:' ):
		print( 'debian/rules final' )
		final_make = Popen( [ 'debian/rules', 'final' ] )
		final_make.communicate()

# clean up the package:
process.finish()

# prepare repo directory:
base_target = os.path.expanduser( options.dest + '/' + options.dist )
generic_target = base_target + '/all/all'

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
	source = os.path.normpath( '../../all/all/' + basename )
	
	for component in components:
		target_dir = os.path.expanduser( base_target + '/' + component + '/all/' )
		target = target_dir + '/' + basename
		if os.path.exists( target ):
			return

		if not os.path.exists( target_dir ):
			os.makedirs( target_dir )
		if os.path.exists( target ):
			os.remove( target )
		print( "link: %s to %s" %(target, source) )
		os.symlink( source, target )

# move/copy files from buld-directory to repository tree
def move_files( path, action, package, do_link=True ):
	basename = os.path.basename( path )
	target = generic_target + '/' + basename
	if not os.path.exists( os.path.dirname( target ) ):
		os.makedirs( os.path.dirname( target ) )
	if os.path.exists( target ):
		os.remove( target )

	f = getattr( shutil, action )
	print( "%s: %s to %s" %(action, path, target) )
	f( path, target )
	if do_link:
		link( package, target )

# copy/move everything to generic components and symlink in specific components
print( "Building repository tree..." )
if options.src:
	move_files( "../%s_%s.orig.tar.gz" %(source, upstream_version), 'copy', 'source' )
	move_files( "../%s_%s.diff.gz" %(source, version), 'move', 'source' )
	move_files( "../%s_%s.dsc" %(source, version), 'move', 'source' )
	move_files( "../%s_%s_source.changes" %(source, version), 'move', 'source' )
	move_files( "../%s_%s_source.build" %(source, version), 'move', 'source' )

if options.bin:
	for package in binary_pkgs:
		# move .debs
		pattern = '../%s_%s_*.deb' %(package, env.get_version( package ) )
		files = glob.glob( pattern )
		for match in files:
			move_files( match, 'move', package )

	# move but not link the arch.changes file (it may contain signatures
	# for packages we do not link for every component)
	move_files( '../%s_%s_%s.changes' %(source, version, options.arch), 'move', source, False )
	move_files( '../%s_%s_%s.build' %(source, version, options.arch), 'move', source )
