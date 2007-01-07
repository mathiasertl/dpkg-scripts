#!/bin/bash
# Location of the apt-repo:
HOME=/var/www/apt
# were the gnupg keyrings are located. This should be outside of the apt-repo!
GNUPGHOME="/var/www/gpg/"
export GNUPGHOME=$GNUPGHOME

dists="tunix dapper edgy"
arch="i386 powerpc amd64"

for d in $d; do
	chmod g+r /var/www/apt/dists/$d/main/all/*
done

signer="Mathias Ertl <mati@pluto.htu.tuwien.ac.at>"
pubring="pubring-mati.gpg"
secring="secring-mati.gpg"

# first check we run as good user
if [[ "$(id -u -n)" != "apt" ]]; then
	echo "Please execute script as user \"apt\" (sudo -u apt $0)"
	exit
fi
if [[ "$(id -g $(id -u -n))" != "$(id -g www-data)" ]]; then
	echo "Please execute script with gid \"www-data\""
	exit
fi

# only user apt has write permissions, web-server has read-only access
umask 0027

# cd to home-dir (the dir of the repo)
cd $HOME

# first we create Packages and Packages.gz files:
for d in $dists; do
   for a in $arch; do 
      if [[ $(find dists/$d/main/all/*_$a.deb 2> /dev/null | wc -l) -gt "0" || $(find dists/$d/main/all/*_all.deb 2> /dev/null | wc -l) -gt "0" ]]; then
         if [[ -d "dists/$d/main/binary-$a/" ]]; then
            if [[ -r "dists/$d/main/all/override.$d.main" ]]; then
		override_file="dists/$d/main/all/override.$d.main"
            else
                echo "Warning: no override file (dists/$d/main/all/override.$d.main) found, using /dev/null instead."
                override_file="/dev/null"
            fi
            dpkg-scanpackages -a$a dists/$d/main/all/ $override_file > dists/$d/main/binary-$a/Packages
            cat dists/$d/main/binary-$a/Packages | gzip -9c > dists/$d/main/binary-$a/Packages.gz
            cat dists/$d/main/binary-$a/Packages | bzip2 -z9 > dists/$d/main/binary-$a/Packages.bz2
         else
            echo "Error: no directory dists/$d/main/binary-$a/ found!"
         fi
      else
         echo "No $a-packages for $d found."
      fi
   done
done

# to sign the Release files, we need the gpg-passphrase. 
echo -e "\nPlease supply your GnuPG passphrase (will not be echoed)..."
read -p "GnuPG passphrase: " -s -a gpgpass
echo -e "\n"

# This loop creates the Release-files and signes them:
for d in $dists; do
	# Note that the description file is not part of the debian repository
	# specification, it just makes a lot of things easier!
	if [[ ! -r $HOME/dists/$d/main/all/description ]]; then
		echo "ERROR: No description for $d file!!"
		continue
	fi
	
	# First we create the Release files in in the binary-* directories
	for a in $arch; do
		if [[ ! -r $HOME/dists/$d/main/binary-$a/Packages ]]; then
			break
		fi
		cd $HOME/dists/$d/main/binary-$a/
		cat "$HOME/dists/$d/main/all/description" > Release
		echo "Architecture: $a" >> Release
		# The grep expression filters out the Release file itself.
		apt-ftparchive release . | grep --invert-match "^ [0-9a-z]* *[0-9]* Release$" >> Release

		rm -f Release.gpg # less annoying questions!
		echo "$gpgpass" | gpg --keyring $pubring --secret-keyring $secring --passphrase-fd 0 -a -b -s -q -u "$signer" -o Release.gpg Release
	done
	
	# now we dynamically create the arches for this repo that go into the toplevel
	# releases file. Note that an arch is only mentioned if there is a Packages
	# file for it.
	repo_arches=""
	for i in $HOME/dists/$d/main/binary-*/Packages; do
		# this if is for the case where there are no Packages files. In that case
		# bash still gets into the for-loop with the right-hand expression.
		if [[ "$i" == "$HOME/dists/$d/main/binary-*/Packages" ]]; then
			break
		fi
		repo_arches="$repo_arches $(echo "$i" | sed "s/\/var\/www\/apt\/dists\/$d\/main\/binary-\(.*\)\/Packages/\1/")"
	done

	cd $HOME/dists/$d/
	cat "$HOME/dists/$d/main/all/description" > Release
	echo "Architecture:$repo_arches" >> Release
	apt-ftparchive release . | grep --invert-match "^ [0-9a-z]* *[0-9]* Release$" >> Release

	rm -f Release.gpg # less annoying questions!
	echo "$gpgpass" | gpg --keyring $pubring --secret-keyring $secring --passphrase-fd 0 -a -b -s -q -u "$signer" -o Release.gpg Release
done
