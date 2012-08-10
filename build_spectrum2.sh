#!/bin/bash

if [[ $(whoami) != "root" ]]; then
	echo "Error: require root privileges."
	exit 1 
fi

APT_REPO="/srv/www/apt.fsinf.at/dists/"
DPKG_REPO='/home/mati/repositories/spectrum2'

set -x

cd $DPKG_REPO
su mati -c 'git checkout upstream'
su mati -c 'git pull'

yesterday=$(date --date=yesterday)
no_commits=$(su mati -c 'git log --oneline --since="`date --date=yesterday`"' | wc -l)

version=$(git describe --tags --match '[0-9].*' | sed 's/\(^[0-9\.]*\)-/\1~/')

su mati -c 'git checkout master'

if [[ $no_commits -eq 0 && -z $FORCE_BUILD ]]; then
	exit
fi

su mati -c 'git merge upstream'

sed -i "1s/\((.*)\)/(1:$version-1)/" debian/changelog

# remove old packages:
find /home/mati/build | grep ^spectrum2 | xargs rm -f 2> /dev/null
find /home/mati/build | grep ^libtransport | xargs rm -f 2> /dev/null

# build packages
su mati -c "mchroot --fd=lucid git-build.py"

# update repositories
rsync --include='libtransport*' --include='spectrum2*' --exclude='*.*' -av /home/mati/build/ $APT_REPO
repo-maint

# remove packages again:
find /home/mati/build | grep ^spectrum2 | xargs rm -f 2> /dev/null
find /home/mati/build | grep ^libtransport | xargs rm -f 2> /dev/null
