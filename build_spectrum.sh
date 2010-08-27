#!/bin/bash

if [[ $(whoami) != "root" ]]; then
	echo "Error: require root privileges."
	exit 1 
fi

find /home/mati/build | grep spectrum-dev | xargs rm -f 2> /dev/null
rm -f /home/mati/repositories/all/spectrum-dev_*
cd /chroot
su mati -c "mchroot schroot -p -c DIR -d /home/mati/repositories/all/spectrum-dev ../../scripts/build.py"
cd /srv/www/apt.fsinf.at/dists
rsync -av /home/mati/build/ ./
repo-maint
find /home/mati/build | grep spectrum-dev | xargs rm 
