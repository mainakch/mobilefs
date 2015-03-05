#!/usr/bin/env python2

import llfuse
from argparse import ArgumentParser
import stat
from llfuse import FUSEError
import pickle
from constants import *
from Tkinter import *
from itertools import groupby

def display_graphics(wnd) : 
	
	#data = (Priority, ID, $, packet#, out of, time)	
	labels = ['Priority', 'ID', 'Progress']	
	for i,st in enumerate(labels) :
		l = Label(wnd, text = st, bg='black', fg='white')
		l.place(x = 10+100*i,y = 10, width=120, height = 35)

def display_data(wnd,data):
		
	#data = (Priority, ID, $, packet#, out of, time)	

	#for task_id, group in groupby(data, lambda x: x[1]): #group by tasks, for each task..,
		#least_packet = min(group, key = lambda x : x[3]) # take the earliest packet
		#progress = float(least_packet[2])/float(least_packet[3])
		
		 	


	info = [(row[0], row[1], row[3], row[4]) for row in data]	
 
	btn_lst= []
	for j,row in enumerate(info) :
		for i in range(len(row)-2) :
			l = Label(wnd, text = row[i], )
			l.place(x = 10+100*i,y = 50+j*30, width=120, height = 35) 
		precentage = float(row[2])/float(row[3])*100
		pr = Label(wnd, text = str(precentage)[0:4]+'%', bg = 'red')		
		pr.place(x=10+100*(i+1), y = 60+j*30, width=120/100*precentage, height = 20)	
		kill_btn = Button(wnd, text="kill", fg="red", command = lambda j=j: kill(j))
		kill_btn.place(x=130+100*(i+2), y = 55+j*30)
		suspend_btn = Button(wnd, text="suspend", fg="green", command = lambda j=j: suspend(j))
		suspend_btn.place(x=40+100*(i+2), y = 55+j*30)
		
def suspend(process_num) :
	print "You requested to suspend process #"+str(process_num)
	send_command("suspend",process_num)

def kill(process_num) :
	print "You requested to kill process #"+str(process_num)
	send_command("suspend",process_num)

def query_f():
	file_name = "state_file"
	
	try:
		fin = open(file_name,'rb')
		data = pickle.load(fin)
	finally:
		fin.close()

	return data

def query():
       	server_address = LOCAL_UNIX_SOCKET
       	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
       	sock.connect(self.server_address)

       	try:
            msg = chunks
            log.debug(msg)
            log.debug('Sending data')
            sock.sendall(str(len(msg)).zfill(10))
            sock.sendall(msg)

            length = recvall(sock, 10)
            data = recvall(sock, int(length))
           
	finally:
            sock.close()
           
        return data

def send_command(command, pss_id):
	#send a command to clientfs
       	server_address = LOCAL_UNIX_SOCKET
       	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
       	sock.connect(self.server_address)

       	try:
            msg = (command, pss_id)
            sock.sendall(str(len(msg)).zfill(10))
            sock.sendall(msg)

            length = recvall(sock, 10)
            data = recvall(sock, int(length))
           
	finally:
            sock.close()
           
        return data




def handler(wnd) :
	data = query_f()
	#data = query()
	
	display_data(wnd,data)
	print "itr"
	wnd.after(2000,lambda wnd=wnd : handler(wnd))
	return
	
            
def main():
	wnd = Tk()
	wnd.title("MOBILEFS QUEUE STATUS")
	wnd.geometry("700x500")
	display_graphics(wnd)
	handler(wnd)	
	wnd.mainloop()

if __name__ == '__main__':
    main()
