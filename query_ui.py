#!/usr/bin/env python2
'''
clientfs.py - Example file system for python-llfuse
'''

import llfuse
from argparse import ArgumentParser
import stat
from llfuse import FUSEError
from constants import *

log = logging.getLogger('query_ui')
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(ch)

fse = sys.getfilesystemencoding()

def bytes2str(s):
    return s.decode(fse, 'surrogateescape')

def str2bytes(s):
    return s.encode(fse, 'surrogateescape')

class Query():
    
    def __init__(self):      
        self.server_address = LOCAL_UNIX_SOCKET

    def send_command_and_receive_response(self, command):
        """This function sends command to the network and returns response. If response
        is an error it raises an error. command is a tuple the first element of which
        is a string description of the command and the second to last elements are
         arguments to the command."""

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.server_address)

        data = 'No response'
        try:
            msg = command
            log.debug(msg)
            log.debug('Sending data')
            sock.sendall(str(len(msg)).zfill(10))
            sock.sendall(msg)
            #sendmsg(sock, str(len(msg)).zfill(10))
            #sendmsg(sock, msg)

            length = recvall(sock, 10)
            #length = sock.recv(10)
            #log.debug(str(length))
            data = recvall(sock, int(length))
           
        finally:
            sock.close()
           
        return data

    def run_loop(self):
        while True:
            commandstring = raw_input('Enter command: ')
            print self.send_command_and_receive_response(commandstring)
            
def main():
    query = Query()
    query.run_loop()
    

if __name__ == '__main__':
    main()
