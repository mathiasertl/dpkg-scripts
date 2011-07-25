#!/bin/bash

if [[ $(whoami) != "root" ]]; then
	echo "Error: require root privileges."
	exit 1 
fi

set -x 
find /home/mati/build | grep spectrum-dev | xargs rm -f 2> /dev/null
rm -f /home/mati/repositories/all/spectrum-dev_*
cd /chroot
su mati -c "mchroot schroot -p -c DIR -d /home/mati/repositories/spectrum-dev ../scripts/build.py spectrum-dev"
cd /srv/www/apt.fsinf.at/dists
rsync -av /home/mati/build/ ./
repo-maint
find /home/mati/build | grep spectrum-dev | xargs rm 
