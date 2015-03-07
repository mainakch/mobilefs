import curses
import time
import sys
import subprocess
import os

stdscr = curses.initscr()
curses.cbreak()
stdscr.keypad(1)

devnull = open('/dev/null', 'w')
#set up screen
if len(sys.argv)>4:
    server_name = sys.argv[1]
    server_port = int(sys.argv[2])
    remote_root = sys.argv[3]
    local_mt = sys.argv[4]
    stdscr.addstr(0,0, "Server name: ", curses.A_BOLD)
    stdscr.addstr(1,0, "Server port: ", curses.A_BOLD)
    stdscr.addstr(2,0, "Remote mountpoint: ", curses.A_BOLD)
    stdscr.addstr(3,0, "Local mountpoint: ", curses.A_BOLD)
    stdscr.addstr(0,30, server_name, curses.A_UNDERLINE)
    stdscr.addstr(1,30, str(server_port), curses.A_UNDERLINE)
    stdscr.addstr(2,30, remote_root, curses.A_UNDERLINE)
    stdscr.addstr(3,30, local_mt, curses.A_UNDERLINE)
    stdscr.refresh()
else:
    
    stdscr.addstr(0,0, "Server name: ", curses.A_BOLD)
    stdscr.refresh()
    server_name = stdscr.getstr(0, 30)
    stdscr.addstr(0,30, server_name, curses.A_UNDERLINE)
    
    stdscr.addstr(1,0, "Server port: ", curses.A_BOLD)
    stdscr.refresh()
    server_port = int(stdscr.getstr(1, 30))
    stdscr.addstr(1,30, str(server_port), curses.A_UNDERLINE)

    stdscr.addstr(2,0, "Remote mountpoint: ", curses.A_BOLD)
    stdscr.refresh()
    remote_root = stdscr.getstr(2, 30)
    stdscr.addstr(2,30, remote_root, curses.A_UNDERLINE)

    stdscr.addstr(3,0, "Local mountpoint: ", curses.A_BOLD)
    stdscr.refresh()
    local_mt = stdscr.getstr(3, 30)
    stdscr.addstr(3,30, local_mt, curses.A_UNDERLINE)
    

#starting network client
stdscr.addstr(4, 0, 'Starting network client...')
stdscr.refresh()
p_net_client = subprocess.Popen(["python2", "network_client.py", server_name, str(server_port)], stderr=devnull, stdout=devnull)
time.sleep(1)
stdscr.addstr(5, 0, 'Starting local fs...')
stdscr.refresh()
p_fs = subprocess.Popen(["python2", "clientfs.py", remote_root, local_mt], stderr=devnull, stdout=devnull)


while True:
    time.sleep(0.3)
    c = stdscr.getch()
    if c == ord('u'):
        err = subprocess.call(["fusermount", "-u", local_mt])
        if err==0:
            p_net_client.kill()
            break
        else:
            stdscr.addstr(-1, 0, 'Error in unmounting', curses.A_BOLD)
            stdscr.refresh()

devnull.close()
curses.nocbreak(); stdscr.keypad(0); curses.echo()
curses.endwin()

