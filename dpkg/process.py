import env
import glob
import shlex

from subprocess import PIPE
from subprocess import Popen

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


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
        print("WARNING: <dist> branches are deprecated. "
              "Use <debian|ubuntu>/<dist> instead")
        return getattr(repo.heads, dist)
    if dist_id:
        branchname = '%s/%s' % (dist_id, dist)
        if hasattr(repo.heads, branchname):
            return getattr(repo.heads, branchname)
    if hasattr(repo.heads, 'debian/%s' % dist):
        return getattr(repo.heads, 'debian/%s' % dist)
    if hasattr(repo.heads, 'ubuntu/%s' % dist):
        return getattr(repo.heads, 'ubuntu/%s' % dist)

    return None


def prepare(dist, dist_config_path, config):
    env.test_dir()

    distrib_config = configparser.ConfigParser()
    distrib_config.read(dist_config_path)

    # error on old sections
    if distrib_config.has_section('defaults'):
        raise Exception("dist-config: Found old 'defaults' section, use 'DEFAULT' instead.")

    # set compat level to distro-specific value
    compat = distrib_config.get('DEFAULT', 'compat')
    print("Set debian/compat to " + compat + "...")
    f = open('debian/compat', 'w')
    f.write(compat + '\n')
    f.close()

    # set Standards-Version in debian/control:
    standards = distrib_config.get('DEFAULT', 'standards')
    print("Set Standards-Version to " + standards + '...')
    sed_ex = 's/^Standards-Version:.*/Standards-Version: %s/' % standards
    p = Popen(['sed', '-i', sed_ex, 'debian/control'])
    p.communicate()

    # set distribution in topmost entry in changes-file:
    if distrib_config.has_option('DEFAULT', 'name'):
        dist = distrib_config.get('DEFAULT', 'name')
    sed_ex = '1s/) [^;]*;/) %s;/' % dist
    p = Popen(['sed', '-i', sed_ex, 'debian/changelog'])
    p.communicate()

    # replace __DATE__
    pdate = Popen(['date', '-R'], stdout=PIPE)
    timestamp = pdate.communicate()[0].decode('utf_8').strip()
    p1 = Popen(['find', 'debian/', '-maxdepth', '1', '-type', 'f'],
               stdout=PIPE)
    p2 = Popen(['xargs', 'sed', '-i', 's/__DATE__/' + timestamp + '/'],
               stdin=p1.stdout)
    p2.communicate()

    if config.has_option('DEFAULT', 'prepare'):
        cmd = config.get('DEFAULT', 'prepare')
        print(cmd)
        p = Popen(shlex.split(cmd))
        p.communicate()

    if config.getboolean('DEFAULT', 'append-dist'):
        release = env.get_release(dist, distrib_config)

        if release:
            regex = '1s/(\(.*\)-\([^-]*\))/(\\1-\\2~%s)/' % release

            for path in glob.glob('debian/*changelog'):
                cmd = ['sed', '-i', regex, path]
                print(' '.join(cmd))
                p = Popen(cmd)
                p.communicate()
