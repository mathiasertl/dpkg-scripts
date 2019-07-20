import re
import sys

from subprocess import Popen, PIPE

from dpkg import gbp
from dpkg import dist_config

# available distros, in order of release
# NOTE: do not remove old distros, as this list is used
#    to determine increasing debian revision numbers.
DISTROS = [
    'hardy',
    'lenny',
    'jaunty',
    'karmic',
    'lucid',
    'maverick',
    'natty',
    'squeeze',
    'oneiric',
    'precise',
    'quantal',
    'wheezy',
    'raring',
    'saucy',
    'trusty',
    'utopic',
    'jessie',
    'vivid',
    'wily',
    'xenial',
    'yakkety',
    'zesty',
    'stretch',
    'artful',
    'bionic',
    'cosmic',
    'disco',
    'buster',
    'eoan',
    'bullseye',
    'unstable',
]
ARCHITECTURES = ['amd64', 'i386', ]


def would_build(dist):
    build_distros = DISTROS
    if gbp.has_option('until'):
        until = gbp.get('until')
        build_distros = build_distros[:build_distros.index(until) + 1]
    if gbp.has_option('from'):
        until = gbp.get('from')
        build_distros = build_distros[build_distros.index(until):]
    if gbp.has_option('exclude'):
        exclude = gbp.get('exclude').split()
        build_distros = [d for d in build_distros if d not in exclude]

    if dist in build_distros:
        return True
    else:
        return False


def get_release(dist):
    if dist_config.has_option(dist, 'release'):
        return dist_config.get(dist, 'release')
    return dist


def get_command_output(cmd):
    p = Popen(cmd, stdout=PIPE)
    stdout = p.communicate()[0].strip()
    return stdout


def test_dir():
    p = Popen(['dh_testdir'], stderr=PIPE)
    stderr = p.communicate()[1].strip()
    if p.returncode:
        print(stderr.decode('utf_8'))
        sys.exit(1)


def get_binary_packages():
    test_dir()
    f = open('debian/control', 'r')
    lines = [l for l in f.readlines() if l.startswith('Package: ')]
    return [l.split(': ', 1)[1].strip() for l in lines]


def get_packages():
    return get_source_package(), get_binary_packages()


def get_package_details():
    test_dir()
    f = open('debian/control', 'r')
    lines = [l for l in f.readlines()]
    packages = {}
    field, value, pkg, pkg_name = None, None, None, None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if line.startswith("Source: "):
            pkg_name = 'source'
            pkg = {'Source': line.split(": ", 1)[1].strip()}
            continue

        if line.startswith("Package: "):
            packages[pkg_name] = pkg

            pkg_name = line.split(": ", 1)[1].strip()
            pkg = {'Package': line.split(": ", 1)[1].strip()}
            continue

        if line.startswith(' ') or line.startswith('\t'):  # continuation field
            pkg[field] += " %s" % line.strip()
        elif ':' in line:
            try:
                field, value = line.split(": ", 1)
                field.strip()
                value.strip()
            except ValueError:
                field = line.strip(': ')
                value = ''

            pkg[field] = value.strip()
        else:
            print("Unable to parse line in debian/control:\n\t%s" % line)

    packages[pkg_name] = pkg

    return packages


def get_changelog_fields(changelog='debian/changelog'):
    # cgabackup (1:2.2-1) quantal; urgency=low
    line = open(changelog).readline().strip()
    match = re.match(r'^(?P<package>[^ ]*)\s+\((?P<version>[^\)]*)\)\s+'
                     '(?P<dist>[^;]*);\s+(?P<urgency>.*)', line)
    return match.groupdict()


def get_source_package(changelog='debian/changelog'):
    return get_changelog_fields(changelog)['package']

def get_source_version(changelog='debian/changelog'):
    version = get_changelog_fields(changelog)['version']
    version = version.rsplit('-', 1)[0]
    if ':' in version:
        version = version.split(':', 1)[1]

    return version
