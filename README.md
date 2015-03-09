# MobileFS

Userspace filesystem over UDP

## Usage:

* At server run ./network_server.py *servername* *serverport*; e.g. ./network_server.py corn.stanford.edu 60002
* At client run ./curses_ui.py *servername* *serverport* *remote_directory* *local_mountpoint*; e.g. ./curses_ui.py corn.stanford.edu 60002 /userfolder/remotedir /localmountpoint

## Known issues:
* In progress system calls will block a suspend-to-RAM unless killed explicitly via the curses_ui.py interface
