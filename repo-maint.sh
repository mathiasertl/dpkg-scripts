#!/bin/bash


# some settings:
HOME=/var/www/apt
repository="$HOME"
# were the gnupg keyrings are located. This should be outside of the apt-repo!
GNUPGHOME="/var/www/gpg/"
export GNUPGHOME=$GNUPGHOME

# ensure good permissions:
chown -R root:www-data $repository
chmod -R u+rwX $repository
chmod -R g+rX $repository
chmod -R o-rwx $repository
chmod -R g-w $repository

dists="$(ls $repository/dists)"

signer="Mathias Ertl <mati@pluto.htu.tuwien.ac.at>"
pubring="pubring-mati.gpg"
secring="secring-mati.gpg"

packagers_keyring="$pubring"

# only user apt has write permissions, web-server has read-only access
umask 0027

# cd to home-dir (the dir of the repo)
cd $HOME

# to sign the Release files, we need the gpg-passphrase. 
echo -e "Please supply your GnuPG passphrase (will not be echoed)..."
read -p "GnuPG passphrase: " -s -a gpgpass
echo -e "\n"

# first we create Packages and Packages.gz files (horrific loop!):
for dist in $dists; do
	# first we get the common description:
	date=$(date -R)
	if [[ ! -f dists/$dist/Release.head ]]; then
		echo "Warning: no dists/$dist/Release.head found!"
	fi

	all_comp=$(find dists/$dist/ -maxdepth 1 -mindepth 1 -type d -printf "%f " | sed 's/ $//')

	# see what components we have:
	for comp in $all_comp; do

		# first we see if there are even any packages.
		if [[ -d dists/$dist/$comp/all/ && ( "$(ls dists/$dist/$comp/all/*.deb dists/$dist/$comp/all/*.dsc 2> /dev/null | wc -l)" -gt "0" ) ]]; then
			chmod 640 dists/$dist/$comp/all/*
		else
			echo "Warning: No packages AT ALL found for $dist/$comp"
			continue
		fi

		# define an override-file
		if [[ -r "dists/$dist/$comp/override.$dist.$comp" ]]; then
			override_file="dists/$dist/$comp/override.$dist.$comp"
		else
			echo "Warning: no override file (dists/$dist/$comp/override.$dist.$comp) found, using /dev/null instead."
			override_file="/dev/null"
		fi

		# this is for the binary packages:
		for a in $(find dists/$dist/$comp/binary* -maxdepth 0 -mindepth 0 -type d); do 
			arch=$(basename $a | sed 's/.*binary-//')

			if [[ $(find dists/$dist/$comp/all/*_$arch.deb 2> /dev/null | wc -l) -gt "0" || $(find dists/$dist/$comp/all/*_all.deb 2> /dev/null | wc -l) -gt "0" ]]; then
				dpkg-scanpackages -a$arch dists/$dist/$comp/all/ $override_file > dists/$dist/$comp/binary-$arch/Packages
				cat dists/$dist/$comp/binary-$arch/Packages | gzip -9c > dists/$dist/$comp/binary-$arch/Packages.gz
				cat dists/$dist/$comp/binary-$arch/Packages | bzip2 -z9 > dists/$dist/$comp/binary-$arch/Packages.bz2
			
				release_file="dists/$dist/$comp/binary-$arch/Release"
				cat dists/$dist/Release.head > $release_file
				echo "Architecture: $arch" >> $release_file
				echo "Component: $comp" >> $release_file
				# The grep expression filters out the Release file itself.
				apt-ftparchive release dists/$dist/$comp/binary-$arch/ | grep --invert-match "^ [0-9a-z]* *[0-9]* Release$" >> $release_file

				rm -f dists/$dist/$comp/binary-$arch/Release.gpg # less annoying questions!
				output="$(echo "$gpgpass" | gpg --logger-fd 1 --keyring $pubring --secret-keyring $secring --passphrase-fd 0 -a -b -s -q -u "$signer" --batch -o dists/$dist/$comp/binary-$arch/Release.gpg dists/$dist/$comp/binary-$arch/Release)"
				if [[ "$?" != "0" ]]; then
					echo "!!! Error: signing of dists/$dist/$comp/binary-$arch/Release.gpg failed."
					echo -e "gpg-output was:\n$output"
					exit
				fi
			else
				echo "Warning: No $arch-packages for $dist/$comp found."
			fi
		done

		# this is for source-packages:
		if [[ -d dists/$dist/$comp/source ]]; then
			# this checks if there are any source-packages in all/
			if [[ "$(ls dists/$dist/$comp/all/*.dsc 2> /dev/null | wc -l)" -gt "0" ]]; then
				# This makes some very good error-checking:
				for src_pkg in $(ls dists/$dist/$comp/all/*.dsc); do
					output=$(gpg --logger-fd 1 --keyring $packagers_keyring --verify $src_pkg)
					if [[ "$?" != "0" ]]; then
						echo "!!! Error: Signature of $src_pkg could not be verified!!!"
						echo -e "Output was:\n$output"
						exit
					fi
					
					# this will grep the checksum lines from the .dsc file,
					# sed them into md5sum compatible format and send that
					# to md5sum. Note that stdout is surpressed for less
					# bogus-output.
					grep "^ [0-9a-z]\{32\} [0-9]* " $src_pkg |\
						 sed "s/^ \([0-9a-z]\{32\}\) [0-9]* /\1  dists\/$dist\/$comp\/all\//" |\
						 md5sum -c - > /dev/null
					if [[ "$?" != "0" ]]; then
						echo "!!! Error: Checksum found in $src_pkg does not match, see above!"
						exit
					fi
				done

				dpkg-scansources dists/$dist/$comp/all/ $override_file > dists/$dist/$comp/source/Sources
				cat dists/$dist/$comp/source/Sources | gzip -9c > dists/$dist/$comp/source/Sources.gz
				cat dists/$dist/$comp/source/Sources | bzip2 -z9 > dists/$dist/$comp/source/Sources.bz2
				
				release_file="dists/$dist/$comp/source/Release"
				cat dists/$dist/Release.head > $release_file
				echo "Architecture: source" >> $release_file
				echo "Component: $comp" >> $release_file
				# The grep expression filters out the Release file itself.
				apt-ftparchive release dists/$dist/$comp/binary-$arch/ | grep --invert-match "^ [0-9a-z]* *[0-9]* Release$" >> $release_file

				rm -f dists/$dist/$comp/source/Release.gpg # less annoying questions!
				output=$(echo "$gpgpass" | gpg --logger-fd 1 --keyring $pubring --secret-keyring $secring --passphrase-fd 0 -a -b -s -q -u "$signer" --batch -o dists/$dist/$comp/source/Release.gpg dists/$dist/$comp/source/Release)
				if [[ "$?" != "0" ]]; then
					echo "!!! Error: signing of dists/$dist/$comp/source/Release.gpg failed."
					echo -e "gpg-output was:\n$output"
					exit
				fi
			else
				echo "Warning: No source packages in dist/$dist/$comp/all/ found."
			fi
		else
			echo " No source directory found for $dist/$comp"
		fi

		release_file="dists/$dist/Release"
		cat dists/$dist/Release.head > $release_file
		echo Architectures: $(find dists/$dist/$comp/binary* -maxdepth 0 -mindepth 0 -type d -printf "%f " | sed "s/dists\/$dist\/$comp\/binary-//g" | sed 's/ $//') >> $release_file
		echo "Components: $all_comp" >> $release_file
		# The grep expression filters out the Release file itself.
		apt-ftparchive release dists/$dist/ | grep --invert-match "^ [0-9a-z]* *[0-9]* Release$" >> $release_file

		rm -f dists/$dist/Release.gpg # less annoying questions!
		output=$(echo "$gpgpass" | gpg --logger-fd 1 --keyring $pubring --secret-keyring $secring --passphrase-fd 0 -a -b -s -q -u "$signer" --batch -o dists/$dist/Release.gpg dists/$dist/Release)
		if [[ "$?" != "0" ]]; then
			echo "!!! Error: signing of dists/$dist/Release failed."
			echo -e "gpg-output was:\n$output"
			exit
		fi
	common_desc=""
	done
done

gpgpass=""
echo "Finished."
