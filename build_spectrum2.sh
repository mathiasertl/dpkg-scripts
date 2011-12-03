#!/bin/bash

if [[ $(whoami) != "root" ]]; then
	echo "Error: require root privileges."
	exit 1 
fi

APT_REPO="/srv/www/apt.fsinf.at/dists/"

set -x

# remove old packages:
find /home/mati/build | grep spectrum2.*git | xargs rm -f 2> /dev/null
find /home/mati/build | grep libtransport.*git | xargs rm -f 2> /dev/null
# remove empty directories
find -depth -empty -type d -exec rmdir {} \;

# build packages
cd /chroot
su mati -c "mchroot schroot -p -c DIR -d /home/mati/repositories/spectrum2 build.py spectrum2-git"

# update repositories
rsync --include='libtransport*git*' --include='spectrum2*git*' --exclude='*.*' -av /home/mati/build/ $APT_REPO
repo-maint

# remove packages again:
find /home/mati/build | grep spectrum2.*git | xargs rm -f 2> /dev/null
find /home/mati/build | grep libtransport.*git | xargs rm -f 2> /dev/null
# remove empty directories
find /home/mati/build -depth -empty -type d -exec rmdir {} \;
