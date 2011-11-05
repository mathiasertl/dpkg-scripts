#!/usr/bin/env python

import os, re, sys, glob, shutil, tempfile
from optparse import OptionParser
from subprocess import *
from dpkg import *

orig_directory = os.getcwd()
scriptpath = os.path.dirname( os.path.realpath( __file__ ) )
temp_directory = None

def exit(status=0):
	os.chdir( orig_directory )
	if temp_directory:
		print( 'rm -r %s'%temp_directory )
		shutil.rmtree( temp_directory )
	sys.exit( status )

def excepthook(exctype, value, traceback):
	exit(1)

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

# decide on directory to build:
package_directory = env.get_package_directory( args )
os.chdir( package_directory )

# see if we have only arch-independent packages, if yes, only build on amd64:
details = env.get_package_details()
archs = set( [ v['Architecture'] for v in details.values() if 'Source' not in v ] )
if set( ['all'] ) == archs and options.arch != 'amd64':
	print( 'Only arch-independent packages found and not on amd64!' )
	exit()

# if we have a "prepare" target, we execute it
for line in open( 'debian/rules' ).readlines():
	if line.startswith( 'prepare:' ):
		print( 'debian/rules prepare' )
		p = Popen( [ 'debian/rules', 'prepare' ] )
		p.communicate()
		break

# get some runtime data that we will fail without
source, binary_pkgs = env.get_packages()
version = env.get_version()
upstream_version, debian_version = version.rsplit( '-', 1 )

os.chdir( orig_directory )

# load various config-files
config_file_paths = [ 'config.cfg', source + '.cfg', package_directory + '.cfg' ]
package_config = configparser.ConfigParser( {'tar-args': '--strip=1'} )
package_config.read( config_file_paths )

# check if we wuild build in this distro
if not env.would_build( package_config, options.dist ):
	print( "Not building on %s."%options.dist )
	exit()

p = Popen( ['dpkg-checkbuilddeps', package_directory + '/debian/control'], stderr=PIPE )
stderr = p.communicate()[1].strip()
if p.returncode:
	print( stderr.decode( 'utf_8' ) )
	exit(1)

# get original source
orig_source = process.get_source( package_directory, source, upstream_version )

# create temporary directory
temp_directory = tempfile.mkdtemp()
sys.excepthook = excepthook # register exception handler to remove temporary directory
target = os.path.join( temp_directory, '%s-%s'%(source, upstream_version) )
print( 'cp -a %s %s'%(package_directory, target) )
shutil.copytree( package_directory, target )
print( 'cp -a %s %s'%(orig_source, temp_directory) )
shutil.copy2( orig_source, temp_directory )
orig_source = os.path.join( temp_directory, orig_source )
os.chdir( temp_directory )

# target of the apt-repository directory:
base_target = os.path.expanduser( options.dest + '/' + options.dist )
generic_target = base_target + '/all/all'

# we wouldn't build anything!
if not options.src and not options.bin:
	exit()

os.chdir( target ) # go to package directory
process.extract_source( orig_source, package_config ) # extract source

# prepare package
config_path = os.path.join( scriptpath, 'dist-config' )
dist_config_path = os.path.join( config_path, options.dist + '.cfg' )
process.prepare( options.dist, dist_config_path )

deb_path = generic_target + '/' + binary_pkgs[0] + '_' + version + '_' + options.arch + '.deb'
if os.path.exists( deb_path ):
	print( "Not building binary package, it seems to already exist..." )
	options.bin = False

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

# get location of changes file:
source_format = env.get_source_format( options.dist )
if source_format == '3.0 (quilt)' and options.dist != "hardy":
	debian_changes = '%s_%s.debian.tar.gz'%(source,version)
else:
	debian_changes = '%s_%s.diff.gz'%(source,version)

# clean up the package:
process.finish( config_path )

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
def move_files( path, package, do_link=True ):
	basename = os.path.basename( path )
	target = generic_target + '/' + basename
	if not os.path.exists( os.path.dirname( target ) ):
		os.makedirs( os.path.dirname( target ) )
	if os.path.exists( target ):
		os.remove( target )

	print( "mv %s %s" %(path, target) )
	shutil.move( path, target )
	if do_link:
		link( package, target )

# move everything to generic components and symlink in specific components
if options.src:
	move_files( orig_source, 'source' )
	move_files( '../' + debian_changes, 'source' )
	move_files( "../%s_%s.dsc" %(source, version), 'source' )
	move_files( "../%s_%s_source.changes" %(source, version), 'source' )
	move_files( "../%s_%s_source.build" %(source, version), 'source' )

if options.bin:
	for package in binary_pkgs:
		# move .debs
		package_version = env.get_version( package )
		pattern = '../%s_%s_*.deb' %(package, package_version)
		files = glob.glob( pattern )
		for match in files:
			move_files( match, package )

	# move but not link the arch.changes file (it may contain signatures
	# for packages we do not link for every component)
	move_files( '../%s_%s_%s.changes' %(source, version, options.arch), source, False )
	move_files( '../%s_%s_%s.build' %(source, version, options.arch), source )

# if we have a "final" target, we execute it
for line in open( 'debian/rules' ).readlines():
	if line.startswith( 'final:' ):
		print( 'debian/rules final' )
		final_make = Popen( [ 'debian/rules', 'final' ] )
		final_make.communicate()


# switch back to master branch
exit()
