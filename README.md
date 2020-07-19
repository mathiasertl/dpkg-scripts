## Local installation

Install dependencies:

```
apt-get install python3 dput git-buildpackage pbuilder
```

Edit `~/.dput.cf` and add:

```
[DEFAULT]
fqdn = enceladus.local
method = scp
login = mati
incoming = incoming/%(dist)s-%(arch)s
```

## Add a new distribution

A script will add everything locally for you:

```
./create-dist.py --release 10 buster
./create-dist.py --vendor ubuntu --release 20.04 focal
```

If you do not have the `fsinf-keyring` package installed, you need to pass it
locally using the `--fsinf-keyring` parameter.

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
