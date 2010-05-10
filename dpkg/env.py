import os
from subprocess import Popen, PIPE

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
