from subprocess import Popen, PIPE
import env, os, sys

try:   
        import configparser
except ImportError:
        import ConfigParser as configparser

def prepare( dist, dist_config_path ):
	env.test_dir()

	# load distribution config
	if not os.path.exists( dist_config_path ):
        	print( "Error: " + dist_config_path + ": Does not exist" )
	        sys.exit(1)

	distrib_config = configparser.ConfigParser()
	distrib_config.read( dist_config_path )

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

	# set distribution in topmost entry in changes-file:
	p = Popen( [ 'sed', '-i', '1s/) [^;]*;/) ' + dist + ';/', 'debian/changelog' ] )
	p.communicate()

	# replace __DATE__
	pdate = Popen( [ 'date', '-R' ], stdout=PIPE )
	timestamp = pdate.communicate()[0].decode( 'utf_8' ).strip()
	p1 = Popen( [ 'find', 'debian/', '-maxdepth', '1', '-type', 'f' ], stdout=PIPE )
	p2 = Popen( [ 'xargs', 'sed', '-i', 's/__DATE__/' + timestamp + '/' ], stdin = p1.stdout )
	p2.communicate()

	# debian/rules prepare
	print( "fakeroot debian/rules prepare" )
	prepare_p = Popen( [ 'fakeroot', 'debian/rules', 'prepare' ] )
	prepare_p.communicate()
	if prepare_p.returncode != 0:
		print( "Error: fakeroot debian/rules/prepare exited with non-zero exit-status")
		sys.exit( prepare_p.returncode )

def finish( config_path ):
	env.test_dir()

	# reset package to a nice default state
	f = open( 'debian/compat', 'w' )
	f.write( '7\n' )
	f.close()

	last_distro = env.DISTROS[-1]
	config_path = os.path.join( config_path, last_distro + '.cfg' )
	distrib_config = configparser.ConfigParser()
	distrib_config.read( config_path )
	standards = distrib_config.get( 'defaults', 'standards' )

	# set distribution in topmost entry in changes-file:
	p = Popen( [ 'sed', '-i', '1s/) [^;]*;/) %s;/'%last_distro, 'debian/changelog' ] )

	# standards version to most recent
	p = Popen( [ 'sed', '-i', 's/^Standards-Version:.*/Standards-Version: %s/'%(standards), 'debian/control' ] )
	p.communicate()
