import socket
import sys
import os
import multiprocessing

def add(a, b):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_address = '/tmp/socket_c_and_nc'
    sock.connect(server_address)
    
    try:
        msg = 'add ' + str(a) + ' ' + str(b)
        length = len(msg)
        #send message length first
        sock.sendall(str(length).zfill(10))
        #now send message
        sock.sendall(msg)
    
        length = sock.recv(10)
        data = sock.recv(int(length))
        print data
    finally:
        sock.close()

def concat(a, b):

        msg = 'concat ' + a*40 + ' ' + b*29
        print msg
        length = len(msg)
        #send message length first
        sock.sendall(str(length).zfill(10))
        #now send message
        sock.sendall(msg)
    
        length = sock.recv(10)
        print length
        data = sock.recv(int(length))
        print data
        print sock.family
    
    finally:
        sock.close()

if __name__ == '__main__':
    p = multiprocessing.Process(target=concat, args=('absbsbbsshhshs', 'dhdhdhhdhssjishhs',))
    p.start()
    p = multiprocessing.Process(target=add, args=(2334, 171717,))
    p.start()
