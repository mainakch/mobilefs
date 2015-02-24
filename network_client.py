'''
network_client.py - Sends remote requests, receives response and returns response
'''
#TODO: add error checking
import socket
import json
import sys
import select
import time
from random import randint

log = logging.getLogger('network_client')
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(ch)

#socket address
network_server_address = ('corn29.stanford.edu', 60002)
client_address = '/tmp/socket_c_and_nc'

#list of sockets
unix_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
network_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#initialize the sockets
unix_server.bind(client_address)
unix_server.listen(1)

inputs = [unix_server, network_server]

outputs = [network_server]

#queues

#key = taskid, value = request
transmit_queue = {}
#key = original_taskid, value = response
receive_queue = {}
#key = (priority, taskid, original_taskid, chunknum, chunktotalnum, timestamp when added to queue), value = chunkof request
chunk_queue = {}
#key = (taskid, original_taskid, chunknum, chunktotalnum, timestamp when received), value=chunkofresponse
receive_chunk_queue = {}
#(received taskid, timestamp)
completed_tasks = {}
#timestamp of last transmission
timestamp_transmission = 0

#mapping from socket object to taskid
sock_to_taskid = {}
taskid_to_sock = {}
order_of_keys_in_chunk_queue = []
taskid = randint(0, 1002039) #not randomizing can lead to same taskid in case of client failure
packets_in_flight = 0

def split_task(taskid, taskstring):
    #this splits up the taskstring into a list of chunks
    startpt = range(0, len(taskstring), 100)
    chunks = [taskstring[pt:pt + 100] for pt in startpt[:-1]]
    chunks.append(taskstring[startpt[-1]:len(taskstring)])
    #smaller the task higher the priority
    ids = [(len(taskstring), taskid, -1, ctr, len(chunks), time.time()) for ctr in range(len(chunks))]
    return (ids, chunks)

def remove_priority_timestamp_info_from_key(key):
    return (key[1], key[2], key[3], key[4])

def augment_timestamp_info_key(key):
    return (key[0], key[1], key[2], key[3], time.time())

def add_filesystem_request_to_transmit_queue(message, s):
    taskid += 1
    #add message to the chunk_queue
    (keys, chunks) = split_task(taskid, message)
    #add keys to order_of_keys_in_chunk_queue
    order_of_keys_in_chunk_queue.extend(keys)
    #sort by priority
    order_of_keys_in_chunk_queue.sort(key = lambda x: x[0])
    #add entries to chunk_queue
    for (key, val) in zip(keys, chunks):
        chunk_queue[key] = val
    #add association between sock and taskid
    sock_to_taskid[s] = taskid
    taskid_to_sock[taskid] = s
    #remove from readables
    inputs.remove(s)
    #add to writables
    outputs.append(s)

    return s

def receive_filesystem_request(s):
    data = s.recv(10)
    if data:
        return s.recv(int(data)) #change this to handle large requests

def handle_remote_filesystem_response(obj):
    data, network_server_address = s.recvfrom(512)
    obj = json.loads(data)
    if obj[2] == 'ack':
        #find out key info
        candidate_list = [ctr for ctr in order_of_keys_in_chunk_queue if ctr[1] == obj[1][0] and ctr[3] == obj[1][2]]
        #remove from chunk_queue
        key = candidate_list[0]
        order_of_keys_in_chunk_queue.remove(key)
        del chunk_queue[key]
        packets_in_flight -= 1
    if obj[2] == 'pac' and obj[0][1] not in completed_tasks:
        #add to receive chunk queue queue
        key = augment_timestamp_info_key(obj[0])
        val = obj[1]
        #add packet to receive chunk
        receive_chunk_queue[key] = val
        #send ack
        s.sendto(json.dumps([0, obj[0], 'ack']), network_server_address)
        #check if all packets have been received for the same original_task_id
        #there's a more efficient way to do this
        list_of_recv_chunks = [ctr for ctr in receive_chunk_queue.keys() if ctr[1] == key[1]]
        if len(list_of_recv_chunks) == key[3]:
            list_of_recv_chunks.sort(key = lambda x: x[2])
            #all chunks have been received
            #transfer to receive_queue
            receive_queue[key[1]] = ''.join([receive_chunk_queue.pop(ctr) for ctr in list_of_recv_chunks])
            #mark timestamp in completed queue
            completed_tasks[key[1]] = time.time()

def send_packets_to_remote_filesystem(s):
    #if possible send packets
    #TODO: add a retransmission timeout
    if packets_in_flight < 1 and len(order_of_keys_in_chunk_queue)>0:
        key = order_of_keys_in_chunk_queue[0]
        s.sendto(json.dumps([remove_priority_timestamp_info_from_key(key), chunk_queue[key], 'pac']), network_server_address)
        packets_in_flight += 1

def send_response_to_local_filesystem(s):
    #TODO: add code to handle network error
    if sock_to_taskid[s] in receive_queue:
        log.debug('Sending response to filesystem')
        s.sendall(str(len(receive_queue[sock_to_taskid[s]])).zfill(10))
        s.sendall(receive_queue[sock_to_taskid[s]])

        #cleanup
        del taskid_to_sock[sock_to_taskid[s]]
        del receive_queue[sock_to_taskid[s]]
        del sock_to_taskid[s]
        outputs.remove(s)

    
while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    for s in readable:
        if s is unix_server:
            log.debug('Accept filesystem connection')
            connection, client_address = unix_server.accept()
            connection.setblocking(0)
            inputs.append(connection)
        if s is not unix_server and s.family == socket.AF_UNIX:
            log.debug('Listen to filesystem connection')
            #s is a client connection from a local process
            #read length of tcp message
            message = receive_filesystem_request(s)
            add_filesystem_request_to_transmit_queue(message, s)
        if s.family == socket.AF_INET:
            log.debug('Receiving information from remote filesystem')
            #s is a network client

            handle_remote_filesystem_response(s)
            
    for s in writable:
        if s is network_server:
            send_packets_to_remote_filesystem(s)
            
        if s is not unix_server and s.family == socket.AF_UNIX:
            send_response_to_local_filesystem(s)
            
    for s in exceptional:
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
