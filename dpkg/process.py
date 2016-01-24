from __future__ import absolute_import

import os

from . import env
from . import gbp
from . import dist_config


def get_branch(repo, dist, dist_id=None):
    # see if config-file gives a branch:
    option = '%s-branch' % dist
    if gbp.has_option(option):
        branch_name = gbp.get(option)
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


def get_version(dist):
    """Get the version to build for the given distribution."""

    changelog_fields = env.get_changelog_fields()
    version = changelog_fields['version']

    if gbp.getboolean('append-dist'):
        release = env.get_release(dist)

        if release:
            return True, '%s~%s' % (version, release)

    return False, version


def postexport_cmds(dist):
    cmds = []
    env.test_dir()

    # update debian/compat
    compat = dist_config.get(dist, 'compat')
    cmds.append('echo %s > debian/compat' % compat)

    # set Standards-Version field
    standards = dist_config.get(dist, 'standards')
    sed_ex = 's/^Standards-Version:.*/Standards-Version: %s/' % standards
    cmds.append('sed -i "%s" debian/control' % sed_ex)

    # set distribution in topmost entry in changes-file:
    if dist_config.has_option(dist, 'name'):
        dist = dist_config.get(dist, 'name')
    sed_ex = '1s/) [^;]*;/) %s;/' % dist
    cmds.append('sed -i "%s" debian/changelog' % sed_ex)

    update, version = get_version(dist)
    if update:
        regex = '1s/(.*)/(%s)/' % version
        cmds.append('sed -i "%s" debian/changelog' % regex)

    return cmds


def get_changes_file(dist, arch):
    changelog_fields = env.get_changelog_fields()
    version = changelog_fields['version']
    changes = '%s_%s_%s.changes' % (changelog_fields['package'], version, arch)
    path = os.path.join(os.path.expanduser('~/build'), '%s-%s' % (dist, arch))
    return os.path.join(path, changes)
