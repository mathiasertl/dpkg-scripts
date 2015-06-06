import os
import re
import sys

from subprocess import Popen, PIPE

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
    'unstable',
]
ARCHITECTURES = ['amd64', 'i386', ]


def would_build(config, dist):
    if config.has_section('distros'):
        raise Exception("gbp-config: Found old 'distros' section, use 'DEFAULT' instead")

    build_distros = DISTROS
    if config.has_option('DEFAULT', 'until'):
        until = config.get('DEFAULT', 'until')
        build_distros = build_distros[:build_distros.index(until) + 1]
    if config.has_option('DEFAULT', 'from'):
        until = config.get('DEFAULT', 'from')
        build_distros = build_distros[build_distros.index(until):]
    if config.has_option('DEFAULT', 'exclude'):
        exclude = config.get('DEFAULT', 'exclude').split()
        build_distros = [d for d in build_distros if d not in exclude]

    if dist in build_distros:
        return True
    else:
        return False


def get_release(dist, dist_config):
    if dist_config.has_section('defaults'):
        raise Exception('dist-config: Using old section name "defaults", use DEFAULTS instead!')

    if dist_config.has_option('DEFAULT', 'release'):
        return dist_config.get('DEFAULT', 'release')
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


def get_architecture():
    return get_command_output(['dpkg-architecture', '-qDEB_BUILD_ARCH'])


def get_lsb_value(var):
    f = open('/etc/lsb-release')
    line = [l for l in f.readlines() if l.startswith(var)]
    if len(line) != 1:
        raise RuntimeError("Variable could not be read from /etc/lsb-release")

    return line[0].strip().split('=', 1)[1]


def get_distribution():
    return get_command_output(['lsb_release', '-sc']).lower()


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


def get_version(package=None):
    test_dir()
    changelog = 'debian/changelog'
    if package and os.path.exists('debian/%s.changelog' % package):
        changelog = 'debian/%s.changelog' % package

    p1 = Popen(["dpkg-parsechangelog", '-l' + changelog], stdout=PIPE)
    p2 = Popen(['grep', '^Version:'], stdin=p1.stdout, stdout=PIPE)
    p3 = Popen(['sed', 's/Version: //'], stdin=p2.stdout, stdout=PIPE)
    p4 = Popen(['sed', 's/.*://'], stdin=p3.stdout, stdout=PIPE)
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
