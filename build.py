#!/usr/bin/env python

import os, re, sys, glob, shutil
from optparse import OptionParser
from subprocess import *
from dpkg import *

# import git externals:
scriptpath = os.path.dirname( os.path.realpath( __file__ ) )
sys.path.append( os.path.join( scriptpath, 'python-git' ) )
sys.path.append( os.path.join( scriptpath, 'python-git/git/ext/gitdb/gitdb' ) )
import git

def exit(status=0):
	os.chdir( '../' )
	if repo.head.reference.name != "master":
		repo.heads.master.checkout()
	sys.exit( status )

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
parser.add_option( '--dist-id', help="Either 'ubuntu' or 'debian', "
	"this is just passed to the build process." )
parser.add_option( '--no-source', action='store_false', dest='src', default=True,
	help="Do not build source package" )
parser.add_option( '--no-binary', action='store_false', dest='bin', default=True,
	help="Do not build binary packages" )
options, args = parser.parse_args()

if len( args ) != 1:
	print( "Please supply exactly one directory to build." )
	sys.exit(1)
else:
	if not os.path.exists( args[0] ):
		print( "%s does not exist."%args[0] )
		sys.exit(1)

# get distribution and architecture first:
if not options.dist:
	options.dist = env.get_distribution()
if not options.arch:
	options.arch = env.get_architecture()
if not options.dist_id:
	options.dist_id = env.get_dist_id()
os.environ['ARCH'] = options.arch
os.environ['DIST'] = options.dist
os.environ['DIST_ID'] = options.dist_id

# initialize git-repo wrapper:
repo = git.Repo.init( os.getcwd() )

# switch to distro-specific branch, if it exists
for branch in repo.heads:
	if branch.name == options.dist:
		branch.checkout()

if os.path.exists( 'skip' ):
	print( "Not building for %s"%options.dist )
	exit()

# load package config
package_config_file = os.path.basename( os.getcwd() ) + '.cfg'
package_config = configparser.ConfigParser()
package_config.read( package_config_file )

os.chdir( args[0] )

# get some runtime data that we will fail without
source, binary_pkgs = env.get_packages()
version = env.get_version()
upstream_version, debian_version = version.rsplit( '-', 1 )

# target of the apt-repository directory:
base_target = os.path.expanduser( options.dest + '/' + options.dist )
generic_target = base_target + '/all/all'

control_file = 'debian/control'
if os.path.exists( 'debian/control.' + options.dist ):
	control_file = 'debian/control.' + options.dist

check = [ 'dpkg-checkbuilddeps', control_file ]
p = Popen( check, stderr=PIPE )
stderr = p.communicate()[1].strip()
if p.returncode:
	print( stderr.decode( 'utf_8' ) )
	exit(1)

# we wouldn't build anything!
if not options.src and not options.bin:
	exit()

# prepare package
dist_config_path = os.path.join( scriptpath, 'dist-config', options.dist + '.cfg' )
process.prepare( options.dist, dist_config_path )

deb_path = generic_target + '/' + binary_pkgs[0] + '_' + version + '_' + options.arch + '.deb'
if os.path.exists( deb_path ):
	print( "Not building binary package, it seems to already exist..." )
	options.bin = False

if not options.bin and not options.src:
	exit()

print( "\n\nBuilding target..." )
debuild_params = [ '--set-envvar', 'DIST=' + options.dist, 
	'--set-envvar', 'ARCH=' + options.arch,
	'--set-envvar', 'DIST_ID=' + options.dist_id, '-d' ]

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

# we get the new version *again* because prepare might have changed the version
# and the files created in the build-process use that version.
version = env.get_version()
upstream_version, debian_version = version.rsplit( '-', 1 )
# get location of changes file:
source_format = env.get_source_format( options.dist )
if source_format == '3.0 (quilt)' and options.dist != "hardy":
	debian_changes = '%s_%s.debian.tar.gz'%(source,version)
else:
	debian_changes = '%s_%s.diff.gz'%(source,version)

# if we have a "final" target, we execute it
# TODO: move this to process.finish()
for line in open( 'debian/rules' ).readlines():
	if line.startswith( 'final:' ):
		print( 'debian/rules final' )
		final_make = Popen( [ 'debian/rules', 'final' ] )
		final_make.communicate()

# clean up the package:
process.finish()

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
if options.src:
	move_files( "../%s_%s.orig.tar.gz" %(source, upstream_version), 'copy', 'source' )
	move_files( '../' + debian_changes, 'move', 'source' )
	move_files( "../%s_%s.dsc" %(source, version), 'move', 'source' )
	move_files( "../%s_%s_source.changes" %(source, version), 'move', 'source' )
	move_files( "../%s_%s_source.build" %(source, version), 'move', 'source' )

if options.bin:
	for package in binary_pkgs:
		# move .debs
		package_version = env.get_version( package )
		pattern = '../%s_%s_*.deb' %(package, package_version)
		files = glob.glob( pattern )
		for match in files:
			move_files( match, 'move', package )

	# move but not link the arch.changes file (it may contain signatures
	# for packages we do not link for every component)
	move_files( '../%s_%s_%s.changes' %(source, version, options.arch), 'move', source, False )
	move_files( '../%s_%s_%s.build' %(source, version, options.arch), 'move', source )

# switch back to master branch
exit()
