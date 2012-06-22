from subprocess import Popen, PIPE
import env, os, sys, re

try:   
	import configparser
except ImportError:
	import ConfigParser as configparser

def find_source( src_package_name, version ):
	name_template = '%s_%s.orig'%(src_package_name, version)
	files = [ f for f in os.listdir('.') if f.startswith( name_template ) ]
	if not files:
		return None
	else:
		return files[0]

def get_source( pkg_dir, src_package_name, version ):
	source = find_source( src_package_name, version )
	if not source:
		# get-orig-source
		print( "%s/debian/rules get-orig-source"%pkg_dir )
		get_orig_source = Popen( [ '%s/debian/rules'%pkg_dir, 'get-orig-source' ] )
		get_orig_source.communicate()
		if get_orig_source.returncode != 0:
			raise RuntimeError( "Error: %s/debian/rules get-orig-source exited with non-zero exit-status"%pkg_dir )
		source = find_source( src_package_name, version )
	return source

def extract_source( source, config ):
	if source.endswith( 'tar.gz' ):
		cmd = ['tar', 'xzf' ]
	elif source.endswith( 'tar.bz2' ):
		cmd = [ 'tar', 'xjf' ]
	elif source.endswith( 'tar.xz' ):
		cmd = [ 'tar', 'xJf' ]
	else:
		raise RuntimeError( "Unrecognized file format: %s"%source )
	cmd += [ source ]
	if config.has_section( 'source' ):
		cmd += config.get( 'source', 'tar-args' ).split(' ')
	else:
		cmd += config.get( 'DEFAULT', 'tar-args' ).split(' ')
	
	print( ' '.join( cmd ) )
	p = Popen( cmd )
	p.communicate()
	if p.returncode != 0:
		raise RuntimeError( "Error: Exit status was %s"%p.returncode )

def get_branch(repo, config, dist, dist_id=None):
	# see if config-file gives a branch:
	option = '%s-branch' % dist
	if config.has_option('DEFAULT', option):
		branch_name = config.get('DEFAULT', option)
		if hasattr(repo.heads, branch_name):
			return getattr(repo.heads, branch_name)
		else:
			raise RuntimeError('%s: Branch does not exist.' % branch_name)

	# see if dist-name branch exists:
	if hasattr(repo.heads, dist):
		print("WARNING: <dist> branches are deprecated. Use <debian|ubuntu>/<dist> instead")
		return getattr(repo.heads, dist)
	if dist_id:
		branchname = '%s/%' % (dist_id.lower(), dist)
		if hasattr(repo.heads, branchname):
			return getattr(repo.heads, branchname)
	return None

def prepare(dist, dist_config_path, config=None):
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

	if config:
		if config.has_option('DEFAULT', 'prepare'):
		        cmd = config.get('DEFAULT', 'prepare')
		        print(cmd)
	        	p = Popen(shlex.split(cmd))
		        p.communicate()
		
		if config.has_option('DEFAULT', 'append-dist'):
		        if config.getboolean('DEFAULT', 'append-dist'):
				index = env.DISTROS.index(dist) + 1
		        	cmd = ['sed', '-i', '1s/(\(.*\)-\([^-]*\))/(\\1-\\2+%s~%s)/' % (index, dist), 'debian/changelog']
			        print(' '.join(cmd))
			        p = Popen(cmd)
			        p.communicate()

def finish( config_path ):
	env.test_dir()

	# reset package to a nice default state
	f = open( 'debian/compat', 'w' )
	f.write( '8\n' )
	f.close()

	# set distribution in topmost entry in changes-file:
	p = Popen( [ 'sed', '-i', '1s/) [^;]*;/) unstable;/', 'debian/changelog' ] )

	# standards version to most recent
	p = Popen( [ 'sed', '-i', 's/^Standards-Version:.*/Standards-Version: 3.9.2/', 'debian/control' ] )
	p.communicate()
