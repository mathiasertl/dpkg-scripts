import env
import gbp

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


def get_version(dist, dist_config):
    """Get the version to build for the given distribution."""

    changelog_fields = env.get_changelog_fields()
    version = changelog_fields['version']

    distrib_config = configparser.ConfigParser()
    distrib_config.read(dist_config)

    if gbp.getboolean('append-dist'):
        release = env.get_release(dist, distrib_config)

        if release:
            return '%s~%s' % (version, release)

    return version


def postexport_cmds(dist, dist_config_path, config):
    cmds = []
    env.test_dir()

    distrib_config = configparser.ConfigParser()
    distrib_config.read(dist_config_path)

    # update debian/compat
    compat = distrib_config.get('DEFAULT', 'compat')
    cmds.append('echo %s > debian/compat' % compat)

    # set Standards-Version field
    standards = distrib_config.get('DEFAULT', 'standards')
    sed_ex = 's/^Standards-Version:.*/Standards-Version: %s/' % standards
    cmds.append('sed -i "%s" debian/control' % sed_ex)

    # set distribution in topmost entry in changes-file:
    if distrib_config.has_option('DEFAULT', 'name'):
        dist = distrib_config.get('DEFAULT', 'name')
    sed_ex = '1s/) [^;]*;/) %s;/' % dist
    cmds.append('sed -i "%s" debian/changelog' % sed_ex)

    # append version if requested
    if gbp.getboolean('append-dist'):
        release = env.get_release(dist, distrib_config)

        if release:
            regex = '1s/(\(.*\)\(-[^-]*\)\\?)/(\\1\\2~%s)/' % release
            cmds.append('sed -i "%s" debian/*changelog' % regex)

    return cmds
