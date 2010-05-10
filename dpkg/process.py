from subprocess import Popen, PIPE
import env, os

try:   
        import configparser
except ImportError:
        import ConfigParser as configparser

def prepare( dist ):
	env.test_dir()

	# load distribution config
	distrib_config_file = '../../.' + dist + '.cfg'
	if not os.path.exists( distrib_config_file ):
        	print( "Error: " + distrib_config_file + ": Does not exist" )
	        sys.exit(1)
	distrib_config = configparser.ConfigParser()
	distrib_config.read( distrib_config_file )

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
	

def finish():
	env.test_dir()

	# reset package to a nice default state
	f = open( 'debian/compat', 'w' )
	f.write( '7\n' )
	f.close()

	# set distribution in topmost entry in changes-file:
	p = Popen( [ 'sed', '-i', '1s/) [^;]*;/) lucid;/', 'debian/changelog' ] )

	# standards version to most recent
	p = Popen( [ 'sed', '-i', 's/^Standards-Version:.*/Standards-Version: 3.8.4/', 'debian/control' ] )
	p.communicate()
