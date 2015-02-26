# MobileFS

Userspace filesystem over UDP

## Usage:

* At server run ./network_server.py *servername* *serverport*; e.g. ./network_server.py corn.stanford.edu 60002
* At client run ./network_client.py *servername* *serverport*; e.g. ./network_client.py corn.stanford.edu 60002
* At client run ./clientfs.py *remotedir* *localmountpoint*; e.g. ./clientfs.py /remote/users/example /mnt/remote

