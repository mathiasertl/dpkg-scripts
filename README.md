## Add a new distribution


### Add debootstrap script

First, you might have to symlink debootstrap scripts for the new distro
(especially any Ubuntu version) (note that all Ubuntu versions are just a
symlink to gutsy):

```
cd /usr/share/debootstrap/scripts
sudo ln -s gutsy cosmic
```

### Build pbuilder chroot

For Ubuntu:

```
DIST=gutsy ARCH=amd64 git-pbuilder create --distribution gutsy --architecture=amd64 \
  --mirror=http://at.archive.ubuntu.com/ubuntu/ --components="main universe" \
  --debootstrapopts "--keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg"
```

For Debian:

```
DIST=wheezy ARCH=amd64 git-pbuilder create --distribution wheezy --architecture amd64 \
  --mirror http://gd.tuwien.ac.at/opsys/linux/debian/ \
  --debootstrapopts "--keyring=/usr/share/keyrings/debian-archive-keyring.gpg"
```

### Configure dput upload locations

Edit `~/.dput.cf` and add:

```
[cosmic-amd64]
dist = cosmic
arch = amd64

[cosmic-i386]
dist = cosmic
arch = i386

[cosmic-amd64-stage]
incoming = /var/cache/pbuilder/repo/cosmic-amd64
method = local

[cosmic-i386-stage]
incoming = /var/cache/pbuilder/repo/cosmic-i386
method = local
```

If not already present, add the default config as well:

```
[DEFAULT]
fqdn = enceladus.local
method = scp
login = mati
incoming = incoming/%(dist)s-%(arch)s
```

### Add dist config

In this repo, add `dist-config/<dist>.cfg` (copy from the last version of the
same vendor). You will have to update some data later.

### Prepare repository server

On the repository server side, you have to do:

* Add distro to `/var/www/apt.fsinf.at/conf/distributions` (copy from previous
  distro),
* Add distro in the admin web interface.
* Create incoming directories 
  (`mkdir -p incoming/cosmic-amd64 incoming-cosmic-i386`)
* Copy `fsinf-keyring` packages:
  
  ```
  cd /var/www/apt.fsinf.at
  reprepro copy cosmic bionic fsinf-keyring
  ```

### Add base packages

Add some base packages so that builds are faster. Use mchroot to log into the
new distro:

```
mchroot -d cosmic login --save
```

And install packages in each:

```
apt-get install -y gnupg2 lintian fakeroot eatmydata
echo deb http://apt.local <dist> all > /etc/apt/sources.list.d/fsinf.list
apt-get update -o Acquire::AllowInsecureRepositories=true
apt-get install -y --allow-unauthenticated fsinf-keyring
apt-get update
```
