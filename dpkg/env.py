import os, sys
from subprocess import Popen, PIPE

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

def test_dir():
	p = Popen( ['dh_testdir'], stderr=PIPE )
	stderr = p.communicate()[1].strip()
	if p.returncode:
		print( stderr.decode( 'utf_8' ) )
		sys.exit(1)

def get_architecture():
	p = Popen( [ 'dpkg-architecture', '-qDEB_BUILD_ARCH' ], stdout=PIPE )
	stdout = p.communicate()[0].strip()
	return stdout

def get_lsb_value( var ):
	f = open( '/etc/lsb-release' )
	line = [ l for l in f.readlines() if l.startswith( var ) ]
	if len( line ) != 1:
		raise RuntimeError( "Variable could not be read from '/etc/lsb-release'" )

	return line[0].strip().split( '=', 1 )[1]
	
def get_distribution():
	return get_lsb_value( 'DISTRIB_CODENAME' )

def get_dist_id():
	return get_lsb_value( 'DISTRIB_ID' )

def get_source_package():
	test_dir()
	f = open( 'debian/control', 'r' )
	line = [ l for l in f.readlines() if l.startswith( 'Source: ' ) ][0]
	source = line.split( ': ', 1 )[1].strip()
	return source

def get_binary_packages():
	test_dir()
	f = open( 'debian/control', 'r' )
	lines = [ l for l in f.readlines() if l.startswith( 'Package: ' ) ]
	return [ l.split( ': ', 1 )[1].strip() for l in lines ]

def get_packages():
	return get_source_package(), get_binary_packages()

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
