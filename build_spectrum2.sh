#!/bin/bash

if [[ $(whoami) != "root" ]]; then
	echo "Error: require root privileges."
	exit 1 
fi

DPKG_REPO=/home/mati/repositories/spectrum2
BUILD_DIR=/home/mati/build/

function cleanup {
	findargs='-type f -or -type l'
	if [[ $(find $BUILD_DIR -name 'spectrum*' $findargs | wc -l) -gt 0 ]]; then
		find $BUILD_DIR -name 'spectrum*' $findargs | xargs rm -r
	fi
	if [[ $(find $BUILD_DIR -name 'libtransport*' $findargs | wc -l) -gt 0 ]]; then
		find $BUILD_DIR -name 'libtransport*' $findargs | xargs rm -r
	fi
}

set -x

cd $DPKG_REPO
su mati -c 'git checkout master'

rm -rf debian

su mati -c 'git checkout upstream'
su mati -c 'git pull upstream master'

# BEGIN ADDED BY HANZZ
#if [[ $(su mati -c 'git status --porcelain' | wc -l) -gt 0 ]]; then
#	git commit debian/changelog -m "build for $(date)"
#fi
# END

yesterday=$(date --date=yesterday)
no_commits=$(su mati -c 'git log --oneline --since="`date --date=yesterday`"' | wc -l)

version=$(su mati -c "git describe --tags --match '[0-9].*'" | sed 's/\(^[0-9\.]*\)-/\1~/')

su mati -c 'git checkout master'

if [[ $no_commits -eq 0 && -z $FORCE_BUILD ]]; then
	exit
fi

su mati -c 'git merge upstream'

sed -i "1s/\((.*)\)/(1:$version-1)/" debian/changelog

if [[ $(git status --porcelain | wc -l) -gt 0 ]]; then
	su mati -c "git commit debian/changelog -m \"build for $(date)\""
fi

# remove old packages:
cleanup

# build packages
su mati -c "mchroot --fd=lucid git-build.py --no-pristine --upload"

# remove packages again:
cleanup
