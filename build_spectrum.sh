#!/bin/bash

find | grep spectrum-dev | xargs rm 
cd /chroot
su mati -c "mchroot schroot -c DIR -d /home/mati/repositories/all/spectrum-dev ../../scripts/build.py"
cd /srv/www/apt.fsinf.at/dists
rsync -av /home/mati/build/ ./
repo-maint
find /home/mati/build | grep spectrum-dev | xargs rm 
