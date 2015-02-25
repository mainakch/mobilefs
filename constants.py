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
