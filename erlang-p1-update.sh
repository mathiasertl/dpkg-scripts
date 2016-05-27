#!/bin/bash

VERSION=$1
set -e
set -x
export DEBFULLNAME="Mathias Ertl"
export DEBEMAIL="mati@jabber.at"


# update master branch
git checkout master
git fetch upstream
git reset --hard ${VERSION}

git checkout debian
git merge master -m "Merge branch 'master' into debian"

if [[ $(head -n 1 debian/changelog | grep -c "1") -eq "1" ]]; then
    dch -v 1:${VERSION}-0.1 -D unstable "New upstream release."
else
    dch -v ${VERSION}-0.1 -D unstable "New upstream release."
fi
git commit debian/changelog -m "update changelog with new version ${VERSION}"
git-export-orig
