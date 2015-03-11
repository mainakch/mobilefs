import curses
import time
import sys
import subprocess
import pickle
import socket
import constants
from Tkinter import *
from itertools import groupby
import tkMessageBox
import pdb

def send_command_and_receive_response(command):

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


def display_frame(wnd,) : 
	y0 = 50
	x0 = 10

	Label(wnd, text = local_mt+" is mounted to: "+server_name+":"+str(server_port)+remote_root).place(x=10,y=10)
	Button(wnd, text="Unmount", fg="red", command = lambda wnd=wnd : umount(wnd)).place(x=500,y=30)		
	
	Label(wnd, text = "Pending incoming:", bg='blue', fg = 'black').place(x = x0, y = y0)
	labels = ['Priority', 'TaskID','Description','Progress']	
	for i,st in enumerate(labels) :
		Label(wnd, text = st, bg='black', fg='white').place(x = x0+130*i,y = y0+30, width=100, height = 35)
	y0=y0+200
	
	Label(wnd, text = "Pending outgoing:", bg='red', fg = 'black').place(x = x0, y = y0)
	labels = ['Priority', 'TaskID','Description','Progress']	
	for i,st in enumerate(labels) :
		Label(wnd, text = st, bg='black', fg='white').place(x = x0+130*i,y = y0+30, width=100, height = 35)
	y0 = y0 +200

	Label(wnd, text = "Completed:", bg='green', fg = 'black').place(x = x0, y = y0)
	labels = ['TaskID','Description','Timestamp']	
	for i,st in enumerate(labels) :
		Label(wnd, text = st, bg='black', fg='white').place(x = x0+130*i,y = y0+30, width=100, height = 35)


def display_receive(wnd,the_list):
	y0 = 60
	x0 = 10
	for j,row in enumerate(the_list) :
		for i in range(len(row)-2) :
			Label(wnd, text = row[i]).place(x = x0+130*i,y = y0+70+j*30, width=120, height = 35) 
		if (row[4]>0) :
			precentage = float(row[3])/float(row[4])*100
		else : 
			precentage = 100
		Label(wnd, text = str(row[3])+"/"+str(row[4]), bg = 'red').place(x=x0+130*(i+1), y = y0+75+j*30, width=120/100*precentage, height = 20)	


def display_transmit(wnd,the_list) : 
	y0 = 250
	x0 = 10

	for j,row in enumerate(the_list) :
		for i in range(len(row)-2) :
			Label(wnd, text = row[i]).place(x = x0+130*i,y = y0+70+j*30, width=120, height = 35) 
		if (row[4]>0) : 
			precentage = float(row[3])/float(row[4])*100
		else : 
			precentage = 100
		pr = Label(wnd, text = str(row[3])+"/"+str(row[4]), bg = 'red').place(x=x0+130*(i+1), y = y0+75+j*30, width=120/100*precentage, height = 20)	
		Button(wnd, text="Kill", fg="red", command = lambda j=row[1]: kill(j)).place(x=x0+130*(i+2), y =y0+75+j*30)
		

def display_complete(wnd,the_list):
	y0 = 400
	x0 = 10
	for j,row in enumerate(the_list[0: min(len(the_list), 6)]) :
		for i in range(len(row)) :
			Label(wnd, text = row[i]).place(x = x0+130*i,y = y0+120+j*30, width=120, height = 35) 


def kill(process_num) :
	print "You requested to kill process #"+str(process_num)
        status = send_command_and_receive_response(
            'kill ' + str(process_num))

def umount(wnd) :
	err = subprocess.call(["fusermount", "-u", local_mt])
 	if err == 0:
		p_net_client.kill()
		wnd.quit()
	else :
		tkMessageBox.showerror("Error","Error in unmounting "+local_mt)


def update_display(wnd,list_transmitting, list_receive, list_complete):
	widget_list = wnd.winfo_children()
	for widget in widget_list[16:]:
		widget.destroy()
    	display_complete(wnd,list_complete)
    	display_receive(wnd,list_receive)
    	display_transmit(wnd,list_transmitting)


def update_state(wnd) :
	current_state = send_command_and_receive_response('state')
    	list_tr, list_res, list_complete = pickle.loads(current_state)
	update_display(wnd, list_tr, list_res, list_complete)	
	wnd.after(500,lambda wnd=wnd : update_state(wnd))
	return
	
stdscr = curses.initscr()
curses.cbreak()
#curses.noecho()
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
    stdscr.addstr(2, 0, "Remote mountpoint: ", curses.A_BOLD)
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

    stdscr.addstr(2, 0, "Remote mountpoint: ", curses.A_BOLD)
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


#starting GUI:
wnd = Tk()
wnd.title("MOBILEFS")
wnd.geometry("600x800")
display_frame(wnd)
update_state(wnd)
wnd.mainloop()  

devnull.close()
curses.nocbreak()
stdscr.keypad(0)
curses.echo()
curses.endwin()

