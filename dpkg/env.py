import os, sys, re
from subprocess import Popen, PIPE

# available distros, in order of release
# NOTE: do not remove old distros, as this list is used
#	to determine increasing debian revision numbers.
DISTROS = [
    'hardy', 'lenny', 'jaunty',
	'karmic', 'lucid', 'maverick',
	'natty', 'squeeze', 'oneiric',
	'precise', 'quantal', 'raring',
    'wheezy', 'jessie', 'unstable'
]

def would_build( config, dist ):
	build_distros = DISTROS

	if config.has_section( 'distros' ):
		if config.has_option( 'distros', 'until' ):
			until = config.get( 'distros', 'until' )
			build_distros = build_distros[:build_distros.index( until )+1 ]
		if config.has_option( 'distros', 'from' ):
			until = config.get( 'distros', 'from' )
			build_distros = build_distros[build_distros.index( until ): ]
		if config.has_option( 'distros', 'exclude' ):
			exclude = config.get( 'distros', 'exclude' ).split()
			build_distros = [ d for d in build_distros if d not in exclude ]

	if config.has_option( 'DEFAULT', 'until' ):
		until = config.get( 'DEFAULT', 'until' )
		build_distros = build_distros[:build_distros.index( until )+1 ]
	if config.has_option( 'DEFAULT', 'from' ):
		until = config.get( 'DEFAULT', 'from' )
		build_distros = build_distros[build_distros.index( until ): ]
	if config.has_option( 'DEFAULT', 'exclude' ):
		exclude = config.get( 'DEFAULT', 'exclude' ).split()
		build_distros = [ d for d in build_distros if d not in exclude ]

	if dist in build_distros:
		return True
	else:
		return False

def get_package_directory( args ):
	"""
	Get the directory containing the source package
	"""
	def get_directory( arg ):
		if os.path.exists( arg ):
			return arg

		dirs = [n for n in os.listdir('.') if os.path.isdir(n)]
		candidates = [d for d in dirs if re.match('%s-[0-9]+'%arg, d)]
		return sorted( candidates )[-1]

	if len( args ) == 0:
		if os.path.exists('debian'):
			return '.' # we already are in the package directory

		dirs = [ node for node in os.listdir( '.' ) if os.path.isdir( node ) ]
		if len( dirs ) == 1:
			directory = dirs[0]
		else:
			directory = get_directory( os.path.basename( os.getcwd() ) )
	elif len( args ) == 1:
		directory = get_directory( args[0] )
	else:
		print( "Please name at most one directory to build." )
		sys.exit(1)

	return directory

def get_source_format( dist ):
	old_dists = [ 'hardy', 'intrepid', 'jaunty', 'karmic', 'lenny' ]
	if dist in old_dists:
		if os.path.exists( 'debian/source/format' ):
			return open( 'debian/source/format' ).readline().strip()
		else:
			return '1.0'
	else:
		# determine source package format:
		workdir = os.getcwd()
		dirname = os.path.dirname( workdir )
		basename = os.path.basename( workdir )
		os.chdir( dirname )
		# note that lenny, intrepid, jaunty and karmic don't support --print-format
		p = Popen( [ 'dpkg-source', '--print-format', basename ], stdout=PIPE )
		source_format = p.communicate()[0].strip()
		os.chdir( workdir )
		return source_format

def get_command_output( cmd ):
	p = Popen( cmd, stdout=PIPE )
	stdout = p.communicate()[0].strip()
	return stdout

def test_dir():
	p = Popen( ['dh_testdir'], stderr=PIPE )
	stderr = p.communicate()[1].strip()
	if p.returncode:
		print( stderr.decode( 'utf_8' ) )
		sys.exit(1)

def get_architecture():
	return get_command_output( [ 'dpkg-architecture', '-qDEB_BUILD_ARCH' ] )

def get_lsb_value( var ):
	f = open( '/etc/lsb-release' )
	line = [ l for l in f.readlines() if l.startswith( var ) ]
	if len( line ) != 1:
		raise RuntimeError( "Variable could not be read from '/etc/lsb-release'" )

	return line[0].strip().split( '=', 1 )[1]

def get_distribution():
	return get_command_output( [ 'lsb_release', '-sc' ] ).lower()

def get_dist_id():
	return get_command_output( [ 'lsb_release', '-si' ] ).lower()

def get_dist_release():
	return get_command_output( [ 'lsb_release', '-sr' ] ).lower()

def get_binary_packages():
	test_dir()
	f = open( 'debian/control', 'r' )
	lines = [ l for l in f.readlines() if l.startswith( 'Package: ' ) ]
	return [ l.split( ': ', 1 )[1].strip() for l in lines ]

def get_packages():
	return get_source_package(), get_binary_packages()

def get_package_details():
	test_dir()
	f = open( 'debian/control', 'r' )
	lines = [ l for l in f.readlines() ]
	packages = {}
	field, value, pkg, pkg_name = None, None, None, None
	for line in lines:
		if not line.strip():
			continue

		if line.startswith("Source: " ):
			pkg_name = 'source'
			pkg = {'Source': line.split( ": ", 1 )[1].strip() }
			continue

		if line.startswith( "Package: " ):
			packages[pkg_name] = pkg

			pkg_name = line.split( ": ", 1 )[1].strip()
			pkg = {'Package': line.split( ": ", 1 )[1].strip() }
			continue

		if ':' in line and not line.startswith( ' ' ):
			field, value = line.split( ": ", 1 )
			field.strip()
			value.strip()

			pkg[field] = value.strip()
		else:
			pkg[field] += " %s"%line.strip()

	packages[pkg_name] = pkg

	return packages


def get_version( package=None ):
	test_dir()
	changelog = 'debian/changelog'
	if package and os.path.exists( 'debian/%s.changelog' %(package) ):
		changelog = 'debian/%s.changelog' %(package)

	p1 = Popen( [ "dpkg-parsechangelog", '-l' + changelog ], stdout=PIPE )
	p2 = Popen( [ 'grep', '^Version:' ], stdin=p1.stdout, stdout=PIPE )
	p3 = Popen( [ 'sed', 's/Version: //' ], stdin=p2.stdout, stdout=PIPE )
	p4 = Popen( [ 'sed', 's/.*://' ], stdin=p3.stdout, stdout=PIPE )
	version = p4.communicate()[0].strip()
	return version


def get_changelog_fields(changelog='debian/changelog'):
    # cgabackup (1:2.2-1) quantal; urgency=low
    line = open(changelog).readline().strip()
    match = re.match(r'^(?P<package>[^ ]*)\s+\((?P<version>[^\)]*)\)\s+'
                     '(?P<dist>[^;]*);\s+(?P<urgency>.*)', line)
    return match.groupdict()

def get_source_package(changelog='debian/changelog'):
    return get_changelog_fields(changelog)['package']

def get_version(changelog='debian/changelog'):
    version = get_changelog_fields(changelog)['version']
    epoch = None
    deb_rev = None

    if ':' in version:
        epoch, version = version.split(':', 1)
    if '-' in version:
        version, deb_rev = version.rsplit('-', 1)
    return {'epoch': epoch, 'version': version, 'debian_revision': deb_rev}

def get_package_files(path, source_pkg, version, arch):
	changes_file = '%s/%s_%s_%s.changes' % (path, source_pkg, version, arch)
	files = [os.path.basename(changes_file)]
	section = False
	for line in open(changes_file).readlines():
		if line.strip() == "Files:":
			section = True
			continue
		if not section:
			continue
		if section and not line.startswith(' '):
			break

		files.append(line.strip().split()[4])

	build_file = '%s/%s_%s_%s.build' % (path, source_pkg, version, arch)
	if os.path.exists(build_file):
		files.append(os.path.basename(build_file))

	return files
