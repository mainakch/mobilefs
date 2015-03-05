"""
constants.py - Set up common parameters
"""


import socket
import os
import json
import sys
import select
import time
import logging
import pickle
import errno

from random import randint

SOCK_CHUNK_SIZE = 1024
CHUNK_SIZE = 300
WINDOW = 10
LOCAL_UNIX_SOCKET = '/tmp/socket_c_and_nc'
LOCAL_UNIX_SOCKET_FOR_QUERY = '/tmp/socket_mobilefs'
DATAGRAM_SIZE = 512
RETRANSMISSION_TIMEOUT = 1 #seconds
FILESYSTEM_TIMEOUT = 10
LISTDIR_TIMEOUT = 2

class Entryattributes():
    def __init__(self, stat):
        self.st_ino = stat.st_ino
        self.st_mode = stat.st_mode
        self.st_nlink = stat.st_nlink
        self.st_uid = stat.st_uid
        self.st_gid = stat.st_gid
        try:
            self.st_rdev = stat.st_dev
        except:
            self.st_rdev = stat.st_rdev
        self.st_size = stat.st_size
        self.st_atime = stat.st_atime
        self.st_mtime = stat.st_mtime
        self.st_ctime = stat.st_ctime
        try:
            self.st_atime_ns = int(self.st_atime*10**9)
            self.st_ctime_ns = int(self.st_ctime*10**9)
            self.st_mtime_ns = int(self.st_mtime*10**9)
        except:
            self.st_atime_ns = None
            self.st_ctime_ns = None
            self.st_mtime_ns = None
            
        self.generation = 0
        self.entry_timeout = 1
        self.attr_timeout = 1
        self.st_blksize = stat.st_blksize
        self.st_blocks = stat.st_blocks

"""
Miscellaneous functions
"""
def recvall(sock, count):
    """This receives count bytes from the sock stream"""
    #print 'Inside recvall'
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def sendmsg(sock, msg):
    """This sends a potentially large msg"""
    current_ptr = 0
    while current_ptr + SOCK_CHUNK_SIZE < len(msg):
        sock.sendall(msg[current_ptr: current_ptr + SOCK_CHUNK_SIZE])
        current_ptr += SOCK_CHUNK_SIZE

    if current_ptr >= len(msg):
        sock.send(msg[current_ptr:-1])
