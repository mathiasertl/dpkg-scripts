#!/usr/bin/python3

import configparser
import os
import re
import subprocess
import sys

from github import Github

def get_field(field):
    data = subprocess.check_output(['dpkg-parsechangelog', '--show-field', field])
    return data.strip().decode('utf-8')

config = configparser.ConfigParser()
config_path = '~/.dpkg-release.conf'
config.read(os.path.expanduser(config_path))
pkg_name = get_field('Source')
if not config.has_section(pkg_name):
    config.add_section(pkg_name)

try:
    token = config.get(pkg_name, 'github-token')
except configparser.NoOptionError:
    print('''No GitHub token could be read from config file.

Please create a token here (needs 'repo' scope):

    https://github.com/settings/tokens

Then set that token in %s like this:

    [DEFAULT]
    github-token = ...

''' % config_path)

    sys.exit(1)

# get the repo-name for github api
url = subprocess.check_output(['git', 'remote', 'get-url', 'origin']).strip().decode('utf-8')
match = re.match('(?P<username>.*)@(?P<host>.*):(?P<repo>.*?)(.git)?$', url)
if match is None:
    print('''Cannot get GitHub repo name.''')
    sys.exit(1)
github_repo_name = match.groupdict()['repo']

#GPG_TTY=$(tty) gbp buildpackage --git-tag-only
tty = subprocess.check_output(['tty']).strip().decode('utf-8')
print('GPG_TTY=%s gbp buildpackage --git-tag-only' % tty)
subprocess.check_call(['gbp', 'buildpackage', '--git-tag-only'])

print('+ git push origin --all')
subprocess.check_call(['git', 'push', 'origin', '--all'])
print('+ git push origin --tags')
subprocess.check_call(['git', 'push', 'origin', '--tags'])

# get version and changelog for GitHub release
version = subprocess.check_output(['dpkg-parsechangelog', '--show-field', 'Version'])
version = version.strip().decode('utf-8')

# parse the changelog (use only lines starting with two spaces, and skip those spaces)
changelog = subprocess.check_output(['dpkg-parsechangelog', '--show-field', 'Changes'])
changelog = changelog.strip().decode('utf-8')
changelog = '\n'.join([line.strip() for line in changelog.splitlines() if line.startswith('  ')])

# Actually create release on GitHub
github = Github(token)
repo = github.get_repo(github_repo_name)
release = repo.create_git_release(
    # TODO: get from gbp.conf config-format?
    tag='debian/%s' % version.replace(':', '%'),
    name=version,
    message=changelog)
#print('Pushed release to %s' % release.url)
print('Pushed release to %s' % release.raw_data['html_url'])
