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

CHUNK_SIZE = 100
DATAGRAM_SIZE = 512
RETRANSMISSION_TIMEOUT = 4 #seconds
FILESYSTEM_TIMEOUT = 8

class Entryattributes():
    def __init__(self, stat):
        self.st_ino = stat.st_ino
        self.st_mode = stat.st_mode
        self.st_nlink = stat.st_nlink
        self.st_uid = stat.st_uid
        self.st_gid = stat.st_gid
        self.st_rdev = stat.st_dev
        self.st_size = stat.st_size
        self.st_atime = stat.st_atime
        self.st_mtime = stat.st_mtime
        self.st_ctime = stat.st_ctime
        self.st_atime_ns = int(self.st_atime*10**9)
        self.st_ctime_ns = int(self.st_ctime*10**9)
        self.st_mtime_ns = int(self.st_mtime*10**9)
        self.generation = 0
        self.entry_timeout = 1
        self.attr_timeout = 1
        self.st_blksize = stat.st_blksize
        self.st_blocks = stat.st_blocks
