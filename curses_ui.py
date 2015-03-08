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

maxval = stdscr.getmaxyx()
stdscr.addstr(maxval[0]-1, 0, 'u: Unmount fs; k: Kill task; r: Refresh tasklist')
stdscr.refresh()

NUM_LINES = min((maxval[0]-10)/3, 5)
#add transport, receive and completed tasks queue
stdscr.addstr(6, 0, 'Transmit queue', curses.A_BOLD)
stdscr.addstr(6+NUM_LINES, 0, 'Receive queue', curses.A_BOLD)
stdscr.addstr(6+2*NUM_LINES, 0, 'Completed tasks', curses.A_BOLD)

stdscr.refresh()


def display_transmit(list_of_transmitting_tasks):
    #each element in the task is a tuple (priority, taskid, taskdesc, chunks, totalchunks)
    if len(list_of_transmitting_tasks)>NUM_LINES-1: list_of_transmitting_tasks = list_of_transmitting_tasks[:NUM_LINES-1]
    ctr=0
    while ctr<min(len(list_of_transmitting_tasks), NUM_LINES-1):
        task = list_of_transmitting_tasks[ctr]
        stdscr.move(6+ctr+1, 0)
        stdscr.clrtoeol()
        stdscr.addstr(6+ctr+1, 0, str(task[0]) + '\t' + str(task[1]) + '\t' + str(task[2]) + '\t' + str(task[3]) + '\t' + str(task[4]))
        ctr = ctr + 1
    #clear remaining lines
    while ctr<NUM_LINES-1:
        stdscr.move(6+ctr+1, 0)
        stdscr.clrtoeol()
        ctr = ctr + 1
        
def display_receive(list_of_responses):
    #each element is a tuple (priority, originaltaskid, taskdesc, chunks, totalchunks)
    if len(list_of_responses)>NUM_LINES-1: list_of_responses = list_of_responses[:NUM_LINES-1]
    ctr=0
    while ctr<min(len(list_of_responses), NUM_LINES-1):
        task = list_of_responses[ctr]
        stdscr.move(6+ctr+1+NUM_LINES, 0)
        stdscr.clrtoeol()
        stdscr.addstr(6+ctr+1+NUM_LINES, 0, str(task[0]) + '\t' + str(task[1]) + '\t' + str(task[2]) + '\t' + str(task[3]) + '\t' + str(task[4]))
        ctr = ctr + 1
    #clear remaining lines
    while ctr<NUM_LINES-1:
        stdscr.move(6+ctr+1+NUM_LINES, 0)
        stdscr.clrtoeol()
        ctr = ctr + 1
    

def display_complete(list_of_complete):
    #each element is a tuple (taskid, taskdesc, timestamp)
    if len(list_of_complete)>NUM_LINES-1: list_of_complete = list_of_complete[:NUM_LINES-1]
    ctr=0
    while ctr<min(len(list_of_complete), NUM_LINES-1):
        task = list_of_complete[ctr]
        stdscr.move(6+ctr+1+2*NUM_LINES, 0)
        stdscr.clrtoeol()
        stdscr.addstr(6+ctr+1+2*NUM_LINES, 0, str(task[0]) + '\t' + str(task[1]) + '\t' + str(task[2]))
        ctr = ctr + 1
    #clear remaining lines
    while ctr<NUM_LINES-1:
        stdscr.move(6+ctr+1+2*NUM_LINES, 0)
        stdscr.clrtoeol()
        ctr = ctr + 1

def update_display(list_transmitting, list_receive, list_complete):
    display_complete(list_complete)
    display_receive(list_receive)
    display_transmit(list_transmitting)
    stdscr.refresh()

sample_list_tr = [(0,1,2,3,4)]
sample_list_res = [(0,1,2,3,4)]
sample_list_complete = [(0,1,2)]
update_display(sample_list_tr, sample_list_res, sample_list_complete)

update_display([], [], [])

while True:
    time.sleep(0.3)
    c = stdscr.getch()
    if c == ord('u'):
        err = subprocess.call(["fusermount", "-u", local_mt])
        if err==0:
            p_net_client.kill()
            break
        else:
            stdscr.addstr(maxval[0], 0, 'Error in unmounting', curses.A_BOLD)
            stdscr.refresh()

devnull.close()
curses.nocbreak(); stdscr.keypad(0); curses.echo()
curses.endwin()

