#!/bin/bash

set -e

control_dir="DEBIAN"

if [[ "$1" == "" ]]; then
	echo "Please supply the directory of the package to be build."
	exit 1
fi

if [[ "$2" != "" ]]; then
	target="$2"
else
	# note: if you don't specify a target, don't build this directly from
	# the package directory
	target="."
fi

# some sanity checks:
if [[ ! -d "$1" ]]; then
	echo "Error: $1 doesn't exist"
	exit
fi
if [[ ! -d "$2" ]]; then
	echo "Error: $2 doesn't exist"
	exit
fi

# cut out the optional last slash (prettyfication):
dir=$(echo "$1" | sed 's/\(.*\)\/$/\1/')
if [[ ! -f "$dir/$control_dir/control" ]]; then
	echo "Error: no control-file"
	exit
fi

# If the control-file is windows formatted, this fucks everything up. Badly.
sed -i 's/\r//' "$dir/$control_dir/control"

# we parse the package name, version and arch directly from the control file.
# the final name of the .deb file is: $package_$version_$arch.deb
package=$(grep "Package: " "$dir/$control_dir/control" | sed 's/^Package: *\(.*\)/\1/')
version=$(grep "Version: " "$dir/$control_dir/control" | sed 's/^Version: *\(.*\)/\1/')
arch=$(grep "Architecture: " "$dir/$control_dir/control" | sed 's/^Architecture: *\(.*\)/\1/')

doc_dir="$dir/usr/share/doc/$package/"
if [[ -d "$doc_dir" ]]; then
	sed -i "s/__DATE/$(822-date)/" $doc_dir/changelog
	sed -i "s/__DATE/$(822-date)/" $doc_dir/changelog.Debian
else
	echo "ERROR: no doc dir $doc_dir found."
	exit
fi

# since all of this is now in an svn-repository, we have to create
# a temporary directory that does not include all the .svn directories.
# note that we can delete it afterwards.
if [[ -d $target/tmp ]]; then
	echo "Error: $target/tmp already exists. Exiting."
	exit 1
fi
rsync -ra --delete $dir/ $target/tmp --exclude ".svn" --exclude "DEBIAN/exec"
dir=$target/tmp/
doc_dir="$dir/usr/share/doc/$package"

# existense of these files is already asserted by the above __DATE replacement.
gzip --best $doc_dir/changelog
gzip --best $doc_dir/changelog.Debian

# create md5sums:
old_dir=$(pwd)
cd $dir
if [[ $(ls | wc -l) != "1" ]]; then
	rm -f $control_dir/md5sums
	find * -type f | grep --invert-match "^$control_dir[$/]" | xargs md5sum > $control_dir/md5sums
else
	echo "This package contains no files!"
	rm $control_dir/md5sums
fi
cd $old_dir

# this just ensures correct permissions for everything.
echo -e "Fixing permissions and ownership..."
chmod -R go-rwx $dir
chmod -R a+rX $dir
chmod -R u+w $dir
if [[ -f "$dir/$control_dir/postinst" || -f "$dir/$control_dir/postrm" ]]; then
	chmod 755 $dir/$control_dir/post*
fi
if [[ -f "$dir/$control_dir/preinst" || -f "$dir/$control_dir/prerm" ]]; then
	chmod 755 $dir/$control_dir/pre*
fi

# implement the feature that we can mark executables in $control_dir/exec
if [[ -f "$dir/$control_dir/exec" ]]; then
	for i in $(cat "$dir/$control_dir/exec"); do
		if [[ -f "$dir/$i" ]]; then
			chmod 755 $dir/$i
		else
			echo "Warning: $i is marked executable, but doesn't exist!"
		fi
	done
fi

echo -e "Sudo "
sudo chown -R root:root $dir
echo " Done."

# final step
echo "dpkg-deb --build $dir $target/"$package"_"$version"_"$arch".deb"
dpkg-deb --build $dir $target/"$package"_"$version"_"$arch".deb

sudo rm -r $dir
