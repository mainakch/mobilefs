import curses
import time
import sys
import subprocess
import pickle
import socket
import constants

stdscr = curses.initscr()
curses.cbreak()
curses.noecho()
stdscr.keypad(1)
devnull = open('/dev/null', 'w')

#set up screen
if len(sys.argv) > 4:
    server_name = sys.argv[1]
    server_port = int(sys.argv[2])
    remote_root = sys.argv[3]
    local_mt = sys.argv[4]
    stdscr.addstr(0, 0, "Server name: ", curses.A_BOLD)
    stdscr.addstr(1, 0, "Server port: ", curses.A_BOLD)
    stdscr.addstr(2, 0, "Remote directory: ", curses.A_BOLD)
    stdscr.addstr(3, 0, "Local mountpoint: ", curses.A_BOLD)
    stdscr.addstr(0, 30, server_name, curses.A_UNDERLINE)
    stdscr.addstr(1, 30, str(server_port), curses.A_UNDERLINE)
    stdscr.addstr(2, 30, remote_root, curses.A_UNDERLINE)
    stdscr.addstr(3, 30, local_mt, curses.A_UNDERLINE)
    stdscr.refresh()
else:
    stdscr.addstr(0, 0, "Server name: ", curses.A_BOLD)
    stdscr.refresh()
    server_name = stdscr.getstr(0, 30)
    stdscr.addstr(0, 30, server_name, curses.A_UNDERLINE)
    
    stdscr.addstr(1, 0, "Server port: ", curses.A_BOLD)
    stdscr.refresh()
    server_port = int(stdscr.getstr(1, 30))
    stdscr.addstr(1, 30, str(server_port), curses.A_UNDERLINE)

    stdscr.addstr(2, 0, "Remote directory: ", curses.A_BOLD)
    stdscr.refresh()
    remote_root = stdscr.getstr(2, 30)
    stdscr.addstr(2, 30, remote_root, curses.A_UNDERLINE)

    stdscr.addstr(3, 0, "Local mountpoint: ", curses.A_BOLD)
    stdscr.refresh()
    local_mt = stdscr.getstr(3, 30)
    stdscr.addstr(3, 30, local_mt, curses.A_UNDERLINE)

#starting network client
stdscr.addstr(4, 0, 'Starting network client...')
stdscr.refresh()
p_net_client = subprocess.Popen(["python2", "network_client.py",
								 server_name, str(server_port)],
								 stderr=devnull, stdout=devnull)
#starting filesystem
stdscr.addstr(5, 0, 'Starting local fs...')
stdscr.refresh()
p_fs = subprocess.Popen(["python2", "clientfs.py", remote_root,
						 local_mt], stderr=devnull, stdout=devnull)

maxval = stdscr.getmaxyx()
stdscr.addstr(maxval[0]-1, 0, 'u: Unmount fs; k: Kill task; d: Kill all tasks; ' +
			  'r: Refresh tasklist')
stdscr.refresh()

NUM_LINES = min((maxval[0]-10)/3, 5)
#add transport, receive and completed tasks queue
stdscr.addstr(6, 0, 'Transmit queue', curses.A_BOLD)
stdscr.addstr(6+NUM_LINES, 0, 'Receive queue', curses.A_BOLD)
stdscr.addstr(6+2*NUM_LINES, 0, 'Completed tasks', curses.A_BOLD)

stdscr.refresh()

def send_command_and_receive_response(command):
    """This function sends command to the network and returns
	 response. If response is an error it raises an error. command is
	 a tuple the first element of which is a string description of the
	 command and the second to last elements are arguments to the
	 command.
	 """

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect('/tmp/socket_c_and_nc')
    data = 'No response'
    try:
        msg = command
        sock.sendall(str(len(msg)).zfill(10))
        sock.sendall(msg)
        #sendmsg(sock, str(len(msg)).zfill(10))
        #sendmsg(sock, msg)

        length = constants.recvall(sock, 10)
        #length = sock.recv(10)
        #log.debug(str(length))
        data = constants.recvall(sock, int(length))
       
    finally:
        sock.close()
       
    return data


def display_transmit(list_of_tasks):
    # element is a tuple (priority, taskid,
    # taskdesc, chunks, totalchunks)
    if len(list_of_tasks) > NUM_LINES-1:
        list_of_tasks = list_of_tasks[:NUM_LINES-1]
    ctr = 0
    while ctr < min(len(list_of_tasks), NUM_LINES-1):
        task = list_of_tasks[ctr]
        stdscr.move(6+ctr+1, 0)
        stdscr.clrtoeol()
        stdscr.addstr(6+ctr+1, 0, str(task[0]) + '\t' +
					  str(task[1]) + '\t' +  str(task[2]) +
					  '\t' + str(task[3]) + '\t' + str(task[4]))
        ctr = ctr + 1
    #clear remaining lines
    while ctr < NUM_LINES-1:
        stdscr.move(6+ctr+1, 0)
        stdscr.clrtoeol()
        ctr = ctr + 1
        
def display_receive(list_of_responses):
    # each element is a tuple (priority, originaltaskid,
    # taskdesc, chunks, totalchunks)
    if len(list_of_responses) > NUM_LINES-1:
        list_of_responses = list_of_responses[:NUM_LINES-1]
    ctr = 0
    while ctr < min(len(list_of_responses), NUM_LINES-1):
        task = list_of_responses[ctr]
        stdscr.move(6+ctr+1+NUM_LINES, 0)
        stdscr.clrtoeol()
        stdscr.addstr(6+ctr+1+NUM_LINES, 0, str(task[0]) + '\t' + 
					   str(task[1]) + '\t' + str(task[2]) + '\t' + 
					   str(task[3]) + '\t' + str(task[4]))
        ctr = ctr + 1
    #clear remaining lines
    while ctr < NUM_LINES-1:
        stdscr.move(6+ctr+1+NUM_LINES, 0)
        stdscr.clrtoeol()
        ctr = ctr + 1
    

def display_complete(list_of_complete):
    #each element is a tuple (taskid, taskdesc, timestamp)
    if len(list_of_complete) > NUM_LINES-1:
        list_of_complete = list_of_complete[:NUM_LINES-1]
    ctr = 0
    while ctr < min(len(list_of_complete), NUM_LINES-1):
        task = list_of_complete[ctr]
        stdscr.move(6+ctr+1+2*NUM_LINES, 0)
        stdscr.clrtoeol()
        stdscr.addstr(6+ctr+1+2*NUM_LINES, 0, str(task[0]) + '\t' +
					  str(task[1]) + '\t' + str(task[2]))
        ctr = ctr + 1
    #clear remaining lines
    while ctr < NUM_LINES-1:
        stdscr.move(6+ctr+1+2*NUM_LINES, 0)
        stdscr.clrtoeol()
        ctr = ctr + 1

def update_display(list_transmitting, list_receive, list_complete):
    display_complete(list_complete)
    display_receive(list_receive)
    display_transmit(list_transmitting)
    stdscr.refresh()

def update_state():
    current_state = send_command_and_receive_response('state')
    list_tr, list_res, list_complete = pickle.loads(current_state)
    update_display(list_tr, list_res, list_complete)

while True:
    time.sleep(0.3)
    c = stdscr.getch()
    if c == ord('u'):
        err = subprocess.call(["fusermount", "-u", local_mt])
        if err == 0:
            p_net_client.kill()
            break
        else:
            stdscr.addstr(maxval[0]-1, 0, 'Error in unmounting', curses.A_BOLD)
            stdscr.refresh()
    if c == ord('r'):
        update_state()
    if c == ord('k'):
        curses.echo()
        stdscr.addstr(maxval[0]-2, 0, 'Enter taskid: ')
        stdscr.refresh()
        status = send_command_and_receive_response(
            'kill ' + stdscr.getstr(maxval[0]-2, 15)
            )
        stdscr.move(maxval[0]-2, 0)  #clear user input
        stdscr.clrtoeol()
        curses.noecho()
        stdscr.refresh()
    # if c == ord('d'):
    #     curses.echo()
    #     status = send_command_and_receive_response('killall')
    #     stdscr.move(maxval[0]-2, 0)  #clear user input
    #     stdscr.clrtoeol()
    #     curses.noecho()
    #     stdscr.refresh()
        

#close curses screen        
devnull.close()
curses.nocbreak()
stdscr.keypad(0)
curses.echo()
curses.endwin()

