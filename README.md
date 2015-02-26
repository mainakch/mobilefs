# MobileFS

Userspace filesystem over UDP

## Usage:

1. At server run ./network_server.py <servername> <serverport>; e.g. ./network_server.py corn.stanford.edu 60002
2. At client run ./network_client.py <servername> <serverport>; e.g. ./network_client.py corn.stanford.edu 60002
3. At client run ./clientfs.py <remotedir> <localmountpoint>; e.g. ./clientfs.py /remote/users/example /mnt/remote

